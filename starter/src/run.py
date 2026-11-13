"""Prepare locally, then ingest and evaluate explicitly selected splits."""
import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf, section_parts
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(out):
    manifest = json.loads((ROOT / 'data/manifest.json').read_text(encoding='utf-8'))
    source = manifest['sources'][0]
    path = ROOT / source['source_path_or_url']
    if hashlib.sha256(path.read_bytes()).hexdigest() != source['snapshot']['sha256']:
        raise ValueError('PDF differs from manifest snapshot; revalidate corpus and benchmark.')
    selected = set(source['content_page_counting']['counted_pdf_pages'])
    pages = load_pdf(path, source['document_id'], source['source_path_or_url'])
    pages = [p for p in pages if p.page in selected]
    if len(pages) < 30 or any(not p.text for p in pages):
        raise ValueError('Need at least 30 readable content pages.')
    parts = []
    for page in pages:
        page.metadata.update(language=source['language'], year=source['publication_year'])
        parts.extend(section_parts(page))
    chunks_a = [c for p in parts for c in fixed_size(p, 500, 50)]
    chunks_b = [c for p in parts for c in by_paragraph(p, 1000)]
    chunks = {'A': chunks_a, 'B': chunks_b, 'C': chunks_b}
    questions = json.loads((ROOT / 'benchmark/questions.json').read_text(encoding='utf-8'))
    if (len({q['id'] for q in questions}) != len(questions) or
            sum(q['split'] == 'dev' for q in questions) < 15 or
            sum(q['split'] == 'test' for q in questions) < 5):
        raise ValueError('Invalid benchmark split or duplicate IDs.')
    lookup = {(p.document_id, p.page): ' '.join(p.text.split()) for p in pages}
    for q in questions:
        if ' '.join(q['evidence_quote'].split()) not in lookup[q['gold_source_id'], q['gold_page']]:
            raise ValueError(f'Evidence validation failed: {q["id"]}')
    stats = {}
    for strategy, items in chunks.items():
        lengths = [len(c.text) for c in items]
        stats[strategy] = dict(chunk_count=len(items), characters=sum(lengths),
                               min=min(lengths), max=max(lengths), mean=statistics.mean(lengths))
        write(out / f'chunks_{strategy}.json', [asdict(c) for c in items])
    write(out / 'preparation.json', {'content_pages': len(pages), 'statistics': stats,
                                   'A': {'size': 500, 'overlap': 50},
                                   'B': {'max_size': 1000}, 'C': 'B plus supplied filter only',
                                   'section_mapping': 'corpus-specific headings; mixed pages split',
                                   'paragraph_rule': 'PDF blank lines and sentence-ending line breaks; oversized blocks split at spaces'})
    # Same ten locations across strategies, chosen before viewing retrieval scores.
    sample_pages = sorted(selected)[:10]
    samples = []
    for strategy, items in chunks.items():
        for page in sample_pages:
            chunk = next(c for c in items if c.page == page)
            samples.append({'strategy': strategy, 'page': page, 'location': 'first content character',
                            'chunk': asdict(chunk), 'coherence_0_2': None, 'reason': None})
    write(out / 'coherence_to_label.json', samples)
    return chunks, questions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true', help='No database/API calls')
    parser.add_argument('--split', choices=['dev', 'test'], default='dev')
    args = parser.parse_args()
    # A fresh folder preserves previous runs and error evidence.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'starter/results' / stamp
    out.mkdir(parents=True)
    handler = logging.FileHandler(out / 'errors.log', encoding='utf-8')
    logging.getLogger().addHandler(handler)
    started = time.perf_counter()
    embedder = None
    try:
        chunks, questions = prepare(out)
        if args.prepare_only:
            print(f'Preparation OK (no API/database): {out}')
            return
        embedder = MyEmbedder()
        url = os.getenv('DATABASE_URL')
        if not url:
            raise ValueError('DATABASE_URL missing in starter/.env')
        store = PgVectorStore(url, embedder.dimensions)
        store.create_schema()  # Fail before spending on embeddings if DB is unavailable.
        write(out / 'run_config.json', {
            'started_at_utc': stamp, 'split': args.split, 'model': embedder.model_name,
            'dimensions': embedder.dimensions, 'metric': 'cosine', 'search': 'exact',
            'benchmark_sha256': hashlib.sha256((ROOT / 'benchmark/questions.json').read_bytes()).hexdigest(),
            'versions': {p: importlib.metadata.version(p) for p in ['pypdf','openai','psycopg','python-dotenv']},
            'selection_rule': 'dev Evidence Hit@3, then dev Hit@1, then resources',
            'cost_usd': None, 'cost_note': 'Obtain actual charge from OpenRouter usage; not assumed zero.',
            'test_note': 'Run test only after freezing configuration; no automatic tuning.'})
        vectors = {}
        measurements = []
        for strategy in ('A', 'B', 'C'):
            tick = time.perf_counter()
            if strategy == 'C':
                vectors[strategy] = vectors['B']
            else:
                vectors[strategy] = embedder.embed_documents([c.text for c in chunks[strategy]])
            store.upsert(strategy, chunks[strategy], vectors[strategy])
            before = store.count(strategy)
            store.upsert(strategy, chunks[strategy], vectors[strategy])
            after = store.count(strategy)
            if before != after or after != len(chunks[strategy]):
                raise RuntimeError('Reingestion duplicated or lost chunks')
            measurements.append({'strategy': strategy, 'ingest_and_reload_seconds': time.perf_counter()-tick,
                                 'count_before_reload': before, 'count_after_reload': after,
                                 'embeddings_reused_from_B': strategy == 'C'})
        write(out / 'ingestion.json', measurements)
        traces = []
        audit = []
        # Embed each query once; use the exact same query vector across A/B/C.
        for q in [q for q in questions if q['split'] == args.split]:
            vector = embedder.embed_query(q['question'])
            for strategy in ('A','B','C'):
                filters = q.get('filter') if strategy == 'C' else None
                tick = time.perf_counter()
                hits = store.search(strategy, vector, filters=filters)
                trace = evaluate_query(q, hits)
                trace.update(strategy=strategy, applied_filter=filters,
                             retrieval_seconds=time.perf_counter()-tick)
                traces.append(trace)
                write(out / 'traces.json', traces)
                if args.split == 'test':
                    audit.append({'id': q['id'], 'strategy': strategy,
                                  'grounding_0_2': None, 'reason': None,
                                  'metadata_audit': [{'chunk_id': h['chunk_id'], 'correct_and_complete': None,
                                                     'reason': None} for h in hits],
                                  'filter_compliance': (bool(hits) and all(
                                      all(h['metadata'].get(k) == v for k,v in q['filter'].items())
                                      for h in hits)) if q.get('filter') else None})
        write(out / 'metrics.json', summarize(traces))
        write(out / 'test_audit_to_label.json', audit)
        write(out / 'completion.json', {'status': 'retrieval_complete_manual_audit_pending',
                                      'elapsed_seconds': time.perf_counter()-started})
        print(f'Retrieval complete; manual audit pending: {out}')
    except Exception as error:
        # Avoid persisting credentials or provider error bodies.
        write(out / 'failure.json', {'status': 'failed', 'error_type': type(error).__name__,
                                    'detail': str(error) if isinstance(error, (RuntimeError, ValueError)) else 'Backend error; credentials and provider bodies omitted.',
                                    'elapsed_seconds': time.perf_counter()-started,
                                    'note': 'No fallback. Check database, configuration, provider and corpus.'})
        raise RuntimeError(f'Pipeline failed ({type(error).__name__}); see {out}') from None
    finally:
        if embedder is not None:
            embedder.close()
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == '__main__':
    main()

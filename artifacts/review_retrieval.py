"""Apply documented equivalent evidence to saved test traces, without API calls.

Original benchmark gold and literal run artifacts are never changed. Overrides
are keyed by question and chunk, so the same decision applies to A/B/C.
"""
import hashlib
import csv
import json
import unicodedata
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'starter/results/20261113T114712057039Z'
OUT = ROOT / 'artifacts/audit'


def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    traces = read(RUN / 'traces.json')
    reviews = read(OUT / 'test_review.json')
    assert all(r['label_provenance']['human_confirmation'] == 'confirmed' for r in reviews)
    pdf = PdfReader(ROOT / 'starter/data/Foundations_of_Information_Systems.pdf')
    # Existing confirmed audit explains that these single chunks contain the
    # complete answer despite omitting incidental introductory gold text.
    decisions = [
        {'question_id': 'q19', 'chunk_id': '6715a16b384bdac36658390a7a71a77910c8b258490f9c359eb85495655a4175',
         'source_id': 'foundations-of-information-systems', 'page': 71,
         'evidence_start': 'Workers with higher reputation scores',
         'evidence_end': 'workers with lower scores and less experience.',
         'reason': 'Một chunk có điều kiện điểm uy tín cao/kinh nghiệm, được nhận thêm việc và hệ quả phân phối cơ hội bất lợi cho nhóm điểm thấp/ít kinh nghiệm. Không cần câu dẫn của gold để trả lời đầy đủ.'},
        {'question_id': 'q20', 'chunk_id': 'bb0470f7b1da6d8bc76b553afba1553aef251b3e287034465374c53ead89abe3',
         'source_id': 'foundations-of-information-systems', 'page': 72,
         'evidence_start': 'Inputs: These encompass',
         'evidence_end': 'delivered to the intended recipient.',
         'reason': 'Một chunk có đủ tên và định nghĩa inputs/resources/outputs, bao gồm điều kiện đầu ra sẵn sàng giao cho người nhận. Câu dẫn của gold ở chunk trước không cần thiết cho đáp án; không ghép chunk để tính hit.'},
    ]
    for decision in decisions:
        hits = [h for t in traces if t['id'] == decision['question_id']
                for h in t['hits'] if h['chunk_id'] == decision['chunk_id']]
        assert hits, 'Reviewed chunk no longer present in saved traces'
        text = norm(hits[0]['text'])
        a = text.index(decision.pop('evidence_start'))
        end = decision.pop('evidence_end')
        quote = text[a:text.index(end, a) + len(end)]
        assert quote in norm(pdf.pages[decision['page'] - 1].extract_text())
        assert all(h['page'] == decision['page'] and h['document_id'] == decision['source_id']
                   and quote in norm(h['text']) for h in hits)
        decision['equivalent_evidence_quote'] = quote
        decision['basis'] = 'Derived from confirmed test grounding audit; explicit single-chunk retrieval adjudication.'
    lookup = {(d['question_id'], d['chunk_id']): d for d in decisions}
    reviewed = []
    for trace in traces:
        flags = []
        hit_reviews = []
        for rank, (hit, literal) in enumerate(zip(trace['hits'], trace['evidence_matches']), 1):
            decision = lookup.get((trace['id'], hit['chunk_id']))
            accepted = bool(literal or decision)
            flags.append(accepted)
            hit_reviews.append({'rank': rank, 'chunk_id': hit['chunk_id'], 'literal_hit': literal,
                                'reviewed_hit': accepted,
                                'reason': decision['reason'] if decision else
                                'Đủ literal gold trong một chunk.' if literal else
                                'Không có bằng chứng tương đương đầy đủ được chấp nhận trong một chunk ở audit này.'})
        reviewed.append({'id': trace['id'], 'strategy': trace['strategy'], 'split': 'test',
                         'hit_at_1': flags[0], 'hit_at_3': any(flags), 'hit_reviews': hit_reviews})
    metrics = []
    for strategy in ['A', 'B', 'C']:
        items = [r for r in reviewed if r['strategy'] == strategy]
        metrics.append({'strategy': strategy, 'split': 'test', 'total': len(items),
                        'hit_at_1_n': sum(r['hit_at_1'] for r in items),
                        'hit_at_3_n': sum(r['hit_at_3'] for r in items),
                        'hit_at_1': sum(r['hit_at_1'] for r in items) / len(items),
                        'hit_at_3': sum(r['hit_at_3'] for r in items) / len(items)})
    output = {'scope': 'Saved test set only; dev metrics remain literal and are not presented as reviewed.',
              'method': 'Literal evidence OR documented equivalent evidence within one source-traceable chunk; never union of chunks.',
              'reviewer': 'Codex (AI assistant), deriving retrieval decisions from student-confirmed audit',
              'label_provenance': read(OUT / 'summary.json')['provenance'],
              'original_trace_sha256': hashlib.sha256((RUN / 'traces.json').read_bytes()).hexdigest(),
              'decisions': decisions, 'traces': reviewed, 'metrics': metrics}
    (OUT / 'retrieval_review.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log = ROOT / 'artifacts/experiment_log.csv'
    with log.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = list(reader.fieldnames), list(reader)
    for field in ['test_reviewed_hit1', 'test_reviewed_hit3']:
        if field not in fields:
            fields.append(field)
    for row in rows:
        metric = next(m for m in metrics if m['strategy'] == row['strategy'])
        row['test_reviewed_hit1'] = f'{metric["hit_at_1_n"]}/{metric["total"]}'
        row['test_reviewed_hit3'] = f'{metric["hit_at_3_n"]}/{metric["total"]}'
    with log.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()

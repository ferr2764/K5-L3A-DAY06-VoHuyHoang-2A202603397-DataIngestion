"""Export the authored report questions and verify evidence; no retrieval calls."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'report/individual/2A202603397_VoHuyHoang.md'
PDF = ROOT / 'starter/data/Foundations_of_Information_Systems.pdf'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def main():
    text = REPORT.read_text(encoding='utf-8')
    reader = PdfReader(PDF)
    pages = {n: normalize(reader.pages[n - 1].extract_text() or '') for n in range(30, 73)}
    questions = []
    checks = []
    for match in re.finditer(r'^\*\*(q\d{2})\*\*\s*\n(.*?)(?=^\*\*q\d{2}\*\*|^####|\Z)', text, re.M | re.S):
        qid, block = match.groups()
        def field(label):
            return re.search(r'^- ' + re.escape(label) + r': (.+)$', block, re.M).group(1)
        source = re.search(r'`([^`]+)`; trang PDF \*\*(\d+)\*\*, trang in \*\*(\d+)\*\*; mục \*\*([^*]+)\*\*', field('Nguồn'))
        source_id, page, printed_page, section = source.groups()
        page = int(page)
        quote = re.search(r'^> (.+)$', block, re.M).group(1)
        if normalize(quote) not in pages[page]:
            raise ValueError(f'{qid}: evidence missing on PDF page {page}')
        number = int(qid[1:])
        split = 'dev' if number <= 15 else 'test' if number <= 20 else 'reserve'
        filtered = 'section =' in field('Filter')
        alternatives = [{'gold_source_id': source_id, 'gold_page': n, 'evidence_quote': quote}
                        for n, content in pages.items() if n != page and normalize(quote) in content]
        questions.append({
            'id': qid, 'split': split, 'question': field('Câu hỏi'),
            'expected_answer': field('Đáp án kỳ vọng'), 'gold_source_id': source_id,
            'gold_page': page, 'printed_page': int(printed_page), 'section': section,
            'evidence_quote': quote, 'alternative_gold': alternatives,
            'filter': {'section': section} if filtered else None,
            'filter_origin': f'Phạm vi mục {section} được nêu trong câu hỏi trước truy xuất.' if filtered else None,
        })
        checks.append({'id': qid, 'gold_page': page, 'normalized_evidence_found': True,
                       'literal_alternative_pages': [a['gold_page'] for a in alternatives]})
    assert len(questions) == 22 and len({q['id'] for q in questions}) == 22
    assert sum(q['split'] == 'dev' for q in questions) == 15
    assert sum(q['split'] == 'test' for q in questions) == 5
    assert sum(q['filter'] is not None for q in questions) == 4
    assert sum(q['filter'] is not None and q['split'] == 'test' for q in questions) == 2
    output = Path(__file__).resolve().parent
    files = {
        'questions.json': [q for q in questions if q['split'] != 'reserve'],
        'reserve_questions.json': [q for q in questions if q['split'] == 'reserve'],
        'evidence_validation.json': {
            'source_path': PDF.relative_to(ROOT).as_posix(),
            'source_sha256': hashlib.sha256(PDF.read_bytes()).hexdigest(),
            'report_sha256': hashlib.sha256(REPORT.read_bytes()).hexdigest(),
            'normalization': 'Unicode NFC, collapse whitespace; preserve case and punctuation.',
            'page_convention': 'Physical PDF pages, 1-based; selected range 30-72 inclusive.',
            'checks': checks,
            'scope': 'Evidence existence only; no retrieval experiment or grounding labels.',
        },
    }
    for name, data in files.items():
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Exported 15 dev / 5 test / 2 reserve; verified 22 evidence quotes; 4 filters (2 test).')


if __name__ == '__main__':
    main()

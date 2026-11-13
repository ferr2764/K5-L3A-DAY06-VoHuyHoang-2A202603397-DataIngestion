"""Record Codex-assisted review of observed outputs; never invent human labels."""
import csv
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / 'starter/results/20261113T110230648138Z'
TEST = ROOT / 'starter/results/20261113T114712057039Z'
OUT = ROOT / 'artifacts/audit'
OUT.mkdir(exist_ok=True)


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def write(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


provenance = {'reviewer': 'Codex (AI assistant)',
              'method': 'Read displayed chunks and top-3 traces; compare with PDF text, gold and rubric; explicit reasons below. Not a human or independent blinded review.',
              'human_confirmation': 'confirmed',
              'confirmed_by': 'Võ Huy Hoàng',
              'confirmation_date': '2026-11-13',
              'bias_risk': 'Same assistant supported benchmark/code/report and reviewed outputs after seeing retrieval scores.'}

coherence = read(DEV / 'coherence_to_label.json')
scores_b = [2, 1, 1, 1, 1, 2, 2, 1, 1, 2]
reasons_a = [
    'Có chủ đề và các câu giải thích nhưng kết thúc giữa từ “thi”, thiếu phần còn lại của ý.',
    'Mở đầu nối từ trang trước; câu McKinsey bị cắt trước danh sách bảy yếu tố.',
    'Caption SFIA hiểu được nhưng câu về phát triển nghề nghiệp bị cắt giữa từ.',
    'Đoạn Waterfall hiểu một phần; phần giới thiệu Zachman bị cắt giữa từ.',
    'Mở đầu là phần credit nối trang trước; mô tả ASIS kết thúc giữa từ.',
    'Đoạn ứng dụng framework đủ hiểu nhưng danh sách tổ chức nghề nghiệp bị cắt giữa tên.',
    'Hai vai trò IS hiểu được; câu triển vọng nghề nghiệp bị cắt giữa từ.',
    'Mở đầu nối danh sách từ trang trước, phần competency tiếp theo bị cắt giữa từ.',
    'Hai nhóm competency có ví dụ nhưng hàng occupation-specific kết thúc ở “IS”, thiếu nội dung.',
    'Có link học tập rõ nghĩa nhưng câu phân biệt IS/IT kết thúc giữa từ.',
]
reasons_b = [
    'Heading và các câu giải thích vai trò framework đầy đủ, kết thúc trọn câu.',
    'Mở đầu nối trang trước; McKinsey dẫn vào bảy yếu tố nhưng danh sách ở chunk sau.',
    'Có mô tả SFIA và Level 1 trọn câu; phần dẫn bảy cấp thiếu sáu cấp còn lại.',
    'Có mô tả Waterfall/Zachman nhưng chỉ ba trong sáu câu hỏi của ma trận.',
    'ASIS được mô tả trọn ý nhưng chunk bắt đầu bằng credit nối từ trang trước.',
    'Heading và đoạn ứng dụng framework/standard trọn ý, tự hiểu được.',
    'Hai vai trò IS và kết luận triển vọng nghề nghiệp đều trọn câu.',
    'Mở đầu nối danh sách từ trang trước; câu năng lực công nghệ cuối chunk chưa hoàn chỉnh.',
    'Hiểu nhóm workplace/technical nhưng chunk kết thúc ở nhãn IS specific thiếu ví dụ occupation-specific.',
    'Phân biệt mục tiêu IS, hạ tầng và hỗ trợ IT đủ ngữ cảnh, kết thúc trọn câu.',
]
for item in coherence:
    i = item['page'] - 30
    item['coherence_0_2'] = 1 if item['strategy'] == 'A' else scores_b[i]
    item['reason'] = reasons_a[i] if item['strategy'] == 'A' else reasons_b[i]
    item['label_provenance'] = provenance
write(OUT / 'coherence_review.json', coherence)

traces = read(TEST / 'traces.json')
pdf = PdfReader(ROOT / 'starter/data/Foundations_of_Information_Systems.pdf')
pages = {n: ' '.join(pdf.pages[n - 1].extract_text().split()) for n in range(30, 73)}
ground_a = {'q16': (2, 'Top-1 có định nghĩa freemium đầy đủ, đúng trường hợp miễn phí rồi nâng cấp.'),
            'q17': (2, 'Top-3 ghép lại có cách kiếm hoa hồng ở rank 3 và tracking sales ở rank 1; grounding đủ dù không có một chunk chứa toàn bộ gold.'),
            'q18': (1, 'Đúng case Cohealo nhưng thiếu tên Cohealo + Clinical và đoạn đầu chức năng tương ứng; không đủ xác định sản phẩm.'),
            'q19': (2, 'Top-1 có điều kiện uy tín/kinh nghiệm và hệ quả bất lợi cho nhóm điểm thấp, dù thiếu câu dẫn của gold.'),
            'q20': (1, 'Có inputs/resources nhưng định nghĩa outputs bị cắt, thiếu sản phẩm/dịch vụ sẵn sàng giao cho người nhận.')}
ground_b = {'q16': 'Top-1 giữ trọn định nghĩa freemium và điều kiện nâng cấp.',
            'q17': 'Top-1 có cả hoa hồng và tracking/reporting quy doanh số cho affiliate.',
            'q18': 'Top-1 nêu rõ Cohealo + Clinical và khả năng huy động thiết bị nhàn rỗi.',
            'q19': 'Top-1 có cả điều kiện và hệ quả phân phối cơ hội không đều.',
            'q20': 'Rank 2 có đủ định nghĩa inputs/resources/outputs; rank 1 cung cấp tên quy trình và câu dẫn. Grounding xét top-3 nên đủ.'}
reviews = []
for t in traces:
    s, qid = t['strategy'], t['id']
    score, reason = ground_a[qid] if s == 'A' else (2, ground_b[qid])
    metadata = []
    for rank, hit in enumerate(t['hits'], 1):
        correct = (hit['document_id'] == 'foundations-of-information-systems'
                   and hit['source'] == 'starter/data/Foundations_of_Information_Systems.pdf'
                   and ' '.join(hit['text'].split()) in pages[hit['page']]
                   and hit['metadata']['section'] == ('2.2' if hit['page'] == 65 else '2.4' if hit['page'] == 72 else '2.3'))
        assert correct
        metadata.append({'rank': rank, 'chunk_id': hit['chunk_id'], 'source': hit['source'],
                         'page': hit['page'], 'section': hit['metadata']['section'],
                         'correct_and_complete': correct,
                         'reason': 'Đối chiếu text trên trang PDF vật lý và heading mục 2.2/2.3/2.4; source/path/document ID khớp manifest.'})
    compliance = (len(t['hits']) == 3 and all(all(h['metadata'].get(k) == v for k, v in t['filter'].items()) for h in t['hits'])) if t.get('filter') else None
    reviews.append({'id': qid, 'strategy': s, 'grounding_0_2': score, 'reason': reason,
                    'metadata_audit': metadata, 'filter_compliance': compliance,
                    'label_provenance': provenance})
write(OUT / 'test_review.json', reviews)

summary = []
for s in ['A', 'B', 'C']:
    c = [x for x in coherence if x['strategy'] == s]
    ts = [x for x in reviews if x['strategy'] == s]
    filters = [x for x in ts if x['filter_compliance'] is not None]
    summary.append({'strategy': s, 'coherence_mean': sum(x['coherence_0_2'] for x in c)/len(c),
                    'coherence_n': len(c), 'metadata_correct_n': sum(h['correct_and_complete'] for x in ts for h in x['metadata_audit']),
                    'metadata_total': sum(len(x['metadata_audit']) for x in ts),
                    'filter_compliance_n': sum(x['filter_compliance'] for x in filters), 'filter_total': len(filters),
                    'grounding_counts': {str(v): sum(x['grounding_0_2'] == v for x in ts) for v in [0,1,2]},
                    'grounding_mean': sum(x['grounding_0_2'] for x in ts)/len(ts)})
write(OUT / 'summary.json', {'provenance': provenance, 'strategies': summary})

# Prove the test used the same chunk contents and benchmark snapshot as dev.
assert read(DEV / 'run_config.json')['benchmark_sha256'] == read(TEST / 'run_config.json')['benchmark_sha256']
assert read(DEV / 'run_config.json')['model'] == read(TEST / 'run_config.json')['model']
for s in ['A', 'B', 'C']:
    assert (DEV / f'chunks_{s}.json').read_bytes() == (TEST / f'chunks_{s}.json').read_bytes()
write(OUT / 'frozen_inputs_check.json', {
    'dev_run': DEV.name, 'test_run': TEST.name, 'benchmark_sha256_equal': True,
    'model_equal': True, 'chunks_A_B_C_byte_identical': True,
    'note': 'Checked after test against saved dev inputs; no claim that this verification file existed before test.'})

metrics = read(DEV / 'metrics.json') + read(TEST / 'metrics.json')
p = ROOT / 'artifacts/experiment_log.csv'
with p.open(encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    fields, rows = reader.fieldnames, list(reader)
for row in rows:
    for m in metrics:
        if row['strategy'] == m['strategy']:
            row[f'{m["split"]}_hit1'] = f'{m["hit_at_1_n"]}/{m["total"]}'
            row[f'{m["split"]}_hit3'] = f'{m["hit_at_3_n"]}/{m["total"]}'
    row['notes'] = f'Dev {DEV.name}; test {TEST.name}; literal evidence metrics; AI-assisted audit confirmed by Vo Huy Hoang on 2026-11-13; total OpenRouter cost USD 0.0018 reported by student; not allocated per strategy/split'
with p.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps(summary, ensure_ascii=False, indent=2))

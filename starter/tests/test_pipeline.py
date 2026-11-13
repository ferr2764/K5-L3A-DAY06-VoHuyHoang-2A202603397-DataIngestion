"""Offline invariants; synthetic fixtures are never used by the real pipeline."""
import unittest
from src.models import DocumentPage
from src.chunking import by_paragraph, fixed_size
from src.evaluation import evaluate_query


class PipelineTests(unittest.TestCase):
    def test_paragraph_coverage_and_stable_ids(self):
        for text in ['', 'x' * 2301, 'Sentence.\nNext.\n\n' + 'Long words ' * 500]:
            page = DocumentPage('doc', 'source', 1, text, {'section': '1.2'})
            chunks = by_paragraph(page, 1000)
            self.assertEqual(''.join(c.text for c in chunks), text)
            self.assertTrue(all(len(c.text) <= 1000 for c in chunks))
            self.assertEqual([c.chunk_id for c in chunks], [c.chunk_id for c in by_paragraph(page, 1000)])

    def test_fixed_overlap(self):
        page = DocumentPage('doc', 'source', 1, 'abcdefghij')
        self.assertEqual([c.text for c in fixed_size(page, 5, 2)], ['abcde', 'defgh', 'ghij'])
        with self.assertRaises(ValueError):
            fixed_size(page, 5, 5)

    def test_hit_needs_page_and_complete_evidence(self):
        question = dict(gold_source_id='doc', gold_page=1, evidence_quote='full evidence')
        hit = dict(document_id='doc', page=1, text='has full evidence here')
        self.assertTrue(evaluate_query(question, [hit])['hit_at_1'])
        self.assertFalse(evaluate_query(question, [dict(hit, page=2)])['hit_at_3'])
        self.assertFalse(evaluate_query(question, [dict(hit, text='full')])['hit_at_3'])

    def test_alternative_gold(self):
        question = dict(gold_source_id='doc', gold_page=1, evidence_quote='primary',
                        alternative_gold=[dict(gold_source_id='doc', gold_page=2, evidence_quote='alternative')])
        hit = dict(document_id='doc', page=2, text='alternative')
        self.assertTrue(evaluate_query(question, [hit])['hit_at_3'])


if __name__ == '__main__':
    unittest.main()

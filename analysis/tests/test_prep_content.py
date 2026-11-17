import collections
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class PrepContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files=[json.loads((ROOT/'site'/p).read_text(encoding='utf-8')) for p in ['content-foundations.json','content-breadth.json']]
        cls.learning=json.loads((ROOT/'site/learning-evidence.json').read_text(encoding='utf-8'))

    def test_complete_card_and_lesson_coverage(self):
        modules=[m for d in self.files for m in d['modules']]
        cards=[c for d in self.files for c in d['flashcards']]
        questions=[q for d in self.files for q in d['questions']]
        self.assertEqual(len(modules),16)
        self.assertEqual(len(cards),128)
        self.assertEqual(len(questions),64)
        self.assertEqual(set(collections.Counter(c['topicId'] for c in cards).values()),{8})
        self.assertEqual(set(collections.Counter(q['topicId'] for q in questions).values()),{4})
        for m in modules:
            self.assertGreaterEqual(len(m['sections']),3)
            self.assertGreaterEqual(len(m['distinctions']),2)
            self.assertGreaterEqual(len(m['pitfalls']),3)
            for section in m['sections']:
                self.assertGreaterEqual(len(section['body'].split()),55)

    def test_sources_ids_and_original_passages(self):
        sources=[s for d in self.files for s in d['sources']]+self.learning['sources']
        sourceids={s['id'] for s in sources}
        self.assertEqual(len(sources),len(sourceids))
        allids=[]
        for d in self.files:
            for kind in ['modules','flashcards','questions','passages']:
                for entry in d[kind]:
                    allids.append(entry['id'])
                    self.assertTrue(set(entry['sourceIds'])<=sourceids,entry['id'])
                    self.assertTrue(entry['sourceIds'])
            for p in d['passages']:
                self.assertEqual(p['provenance'],'original_fictional_learning_scenario')
                self.assertGreaterEqual(len(p['passage'].split()),170)
                self.assertLessEqual(len(p['passage'].split()),260)
                self.assertEqual(len(p['questions']),3)
                allids.extend(q['id'] for q in p['questions'])
        self.assertEqual(len(allids),len(set(allids)))
        self.assertEqual(sum(len(d['passages']) for d in self.files),8)
        for s in sources:
            self.assertTrue(s['url'].startswith('https://'))
            self.assertTrue(s['pinpoint'])

    def test_answer_integrity_and_encoding(self):
        for d in self.files:
            questions=d['questions']+[q for p in d['passages'] for q in p['questions']]
            for q in questions:
                self.assertEqual(len(q['options']),4)
                self.assertEqual(len(set(q['options'])),4,q['id'])
                self.assertIn(q['correctIndex'],range(4))
                self.assertGreater(len(q['explanation']),35)
                self.assertTrue(q['trap'])
            serialized=json.dumps(d,ensure_ascii=False)
            self.assertNotIn('\ufffd',serialized)
            self.assertNotIn('<script',serialized.lower())
            self.assertNotIn('file://',serialized)
            self.assertNotIn('\\u2019',serialized)
        self.assertEqual(self.learning['exam']['date'],'2026-12-06')


if __name__=='__main__':unittest.main()

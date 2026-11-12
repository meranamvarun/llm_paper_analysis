import copy
import unittest
from extraction.structural_repair import repair_records

class RepairTests(unittest.TestCase):
    def row(self):
        return {"question_id":"q", "year_label":2026, "pdf_pages":[1], "raw_text":"(A) one (B) two (C) Both (A) and (B) (D) Neither (A) nor (B)", "options":[{"label":l,"raw_label":"("+l+")","text":t} for l,t in [("A","one"),("B","two"),("C","Both"),("A","and"),("B",""),("D","Neither"),("A","nor"),("B","")]]}
    def test_nested_references_and_preservation(self):
        q=self.row(); before=copy.deepcopy(q)
        rows, logs=repair_records([q])
        self.assertEqual([o["label"] for o in rows[0]["options"]],list("ABCD"))
        self.assertEqual(rows[0]["options"][2]["text"],"Both (A) and (B)")
        self.assertEqual(q,before)
        self.assertEqual(len(logs),1)
    def test_mismatch_and_ambiguity_remain(self):
        for text in ["unrelated", "(A) one (B) two (C) Both (A) and (B) (D) Neither (A) nor (B)"]:
            q=self.row(); q["raw_text"]=text
            if text!="unrelated": q["options"][2]["text"]="Uncertain"
            rows,logs=repair_records([q]); self.assertEqual(rows,[q]); self.assertEqual(logs,[])
    def test_out_of_scope_and_accepted_unchanged(self):
        for key,value in [("year_label",2015),("review_status","accepted")]:
            q=self.row(); q[key]=value
            self.assertEqual(repair_records([q]),([q],[]))

    def test_idempotent(self):
        first, logs=repair_records([self.row()])
        self.assertEqual(repair_records(first),(first,[]))

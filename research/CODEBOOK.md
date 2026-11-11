# Draft coding manual

Version: 0.1; pilot required before freezing. Blank values mean unknown, not absent. Every label needs status (proposed/reviewed/adjudicated/unresolved), reviewer and codebook version.

| Record | Required fields |
|---|---|
| Paper | paper_id, exam, administration_date, year, set/version, source, access_date, sha256, PDF page span, completeness, duplicate_of, rights_status |
| Question | question_id, paper_id, PDF page (1-based), printed_page, printed_question_number, passage_id, parent_question_id, raw_text, corrected_text, options, marks, extraction_method, OCR/review status |
| Answer | question_id, proposed_answer, official_key_answer, key_source/page, verification_status, discrepancy_note |
| Coding | question_id, subject[], doctrine[], theme[], format, cognitive_demand, evidence_span, status, reviewer, rationale, codebook_version |
| Judgment | judgment_id, canonical_name, aliases[], court, citation, decision_date, authoritative_URL, pinpoint, verification_status |
| Judgment link | question_id, judgment_id (nullable), explicit/implicit/unresolved, question_evidence, legal_reasoning, reviewer, status |
| Repeat pair | question_id_a, question_id_b, exact/near/theme_only/judgment_only/unrelated/unresolved, method_version, score (nullable), rationale, reviewer, status, repeat_group_id |
| AI run | run_id, input_hash, model/provider/version, prompt_version, settings, run_date, output_path, review_status |

Initial subject candidates: constitutional law, jurisprudence, administrative law, criminal law, contract, tort, property, family law, public international law, procedure/evidence, commercial law, labour law, environmental law, intellectual property, other and unresolved. These are seed categories, not a claim about the paper's syllabus. Permit multiple subjects and retain the original labels when mappings change.

Cognitive-demand candidates: recall, doctrinal understanding, application, analysis, unresolved. Write operational examples from the pilot before full coding. Theme names should identify a legal concept, not merely a broad subject. Maintain alias mappings without discarding original wording.

Repeated questions need reviewed substantive equivalence; changed options or negation may change the legal task. Record judgment recurrence independently of question recurrence. One question may link to several judgments; multiple appearances within one question do not multiply its prevalence count.

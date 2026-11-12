"""Apply explicit image-grounded proposals; preserve review/acceptance metadata."""
import copy

ALLOWED={'stem','options','pdf_pages','evidence','printed_question_number','passage_id'}

def apply_proposals(rows,proposals):
    result=copy.deepcopy(rows);byid={q['question_id']:q for q in result};logs=[]
    if len(byid)!=len(rows):raise ValueError('Duplicate record IDs')
    seen=set()
    for p in proposals:
        key=p['question_id'];q=byid[key]
        if key in seen:raise ValueError('Duplicate proposal')
        seen.add(key)
        if not p.get('image_paths') or not p.get('after') or set(p['after'])!=set(p['before']) or not set(p['after'])<=ALLOWED:raise ValueError('Explicit source images and allowed before/after fields required')
        if any(q.get(k)!=v for k,v in p['before'].items()):raise ValueError('Stale before value')
        if 'options' in p['after']:
            opts=p['after']['options']
            if [o['label'] for o in opts]!=list('ABCD') or any(not o['text'].strip() for o in opts):raise ValueError('Complete literal options required')
        q.update(copy.deepcopy(p['after']));logs.append(copy.deepcopy(p))
    return result,logs

"""Apply explicitly accepted extraction proposals to a separate derived view."""

import argparse
import copy
import hashlib
import json
from pathlib import Path


def apply_accepted(baseline, items, decisions, packet_hash):
    """Return corrected copies and a complete before/after log; never mutate inputs."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    originals = {q['question_id']: q for q in baseline}
    accepted = {d['packet_item_id']: d for d in decisions}
    require(len(originals) == len(baseline), 'Duplicate baseline IDs')
    require(len(accepted) == len(decisions), 'Duplicate decisions')
    require(len({d['decision_id'] for d in decisions}) == len(decisions), 'Duplicate decision IDs')
    require(len({i['packet_item_id'] for i in items}) == len(items), 'Duplicate packet items')
    require(set(accepted) == {i['packet_item_id'] for i in items}, 'Decision coverage mismatch')
    replacements, log = {}, []
    for item in items:
        decision = accepted[item['packet_item_id']]
        require(decision['decision'] == 'accept', 'Proposal not accepted')
        require(decision['packet_items_sha256'] == packet_hash, 'Packet hash mismatch')
        packet_baseline = item['baseline']
        old_id = packet_baseline['question_id']
        before = originals.get(old_id)
        require(old_id not in replacements, 'Repeated correction target')
        require(before is not None, 'Missing baseline record')
        content = lambda q: {k: v for k, v in q.items() if k != 'parser_version'}
        require(content(before) == content(packet_baseline), 'Stale baseline record')
        require(decision['baseline_question_id'] == old_id, 'Decision target mismatch')
        if item['kind'] == 'id_alias':
            after = copy.deepcopy(item['reparse'])
            new_id = after['question_id']
            require(item['proposal']['old_id'] == old_id and
                    item['proposal']['new_id'] == new_id and
                    decision['proposed_question_id'] == new_id, 'Alias mismatch')
            require(all(e in after['evidence'] for e in before['evidence']), 'Lost source evidence')
            for key in ('source_hash', 'paper_id', 'year_label'):
                require(after.get(key) == before.get(key), 'Alias crosses source or paper')
            require(new_id == old_id or new_id not in originals, 'Alias ID collision')
        elif item['kind'] == 'transcription':
            require(decision['proposed_question_id'] is None, 'Unexpected transcription alias')
            after = copy.deepcopy(before)
            proposal = item['proposal']
            options = proposal['options']
            require([o['label'] for o in options] == list('ABCD'), 'Invalid option labels')
            stem = '\n'.join(s for s in (proposal['stem'], proposal.get('parenthetical_text')) if s)
            after.update(printed_question_number=proposal['printed_question_number'], stem=stem,
                         options=copy.deepcopy(options),
                         corrected_text=stem+'\n'+'\n'.join(f"({o['label']}) {o['text']}" for o in options))
            new_id = old_id
        else:
            raise ValueError('Unsupported proposal kind')
        # Record the limited acceptance without promoting the entire record to reviewed.
        after['accepted_correction'] = {
            'decision_id': decision['decision_id'], 'packet_item_id': item['packet_item_id'],
            'scope': 'displayed_proposal_only', 'independent_validation_pilot': False}
        after['review_status'] = before['review_status']
        replacements[old_id] = after
        log.append({'decision_id': decision['decision_id'], 'packet_item_id': item['packet_item_id'],
                    'kind': item['kind'], 'old_id': old_id, 'new_id': new_id,
                    'status': 'accepted_proposal_applied', 'before': copy.deepcopy(before),
                    'packet_baseline': copy.deepcopy(packet_baseline),
                    'after': copy.deepcopy(after)})
    result = [copy.deepcopy(replacements.get(q['question_id'], q)) for q in baseline]
    require(len({q['question_id'] for q in result}) == len(result), 'Result ID collision')
    return result, log


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Output directory already exists; choose a new path')
    inputs = [args.baseline, args.packet, args.decisions, Path(__file__)]
    hashes = {str(p.resolve()): sha256(p) for p in inputs}
    baseline, items, decisions = map(read_rows, (args.baseline, args.packet, args.decisions))
    result, log = apply_accepted(baseline, items, decisions, sha256(args.packet))
    if hashes != {str(p.resolve()): sha256(p) for p in inputs}:
        raise ValueError('Input changed during application')
    args.output.mkdir(parents=True, exist_ok=False)
    for name, rows in [('questions.jsonl', result), ('corrections.jsonl', log),
                       ('id_aliases.jsonl', [{'old_id': x['old_id'], 'new_id': x['new_id'],
                                             'decision_id': x['decision_id']} for x in log
                                            if x['old_id'] != x['new_id']])]:
        with (args.output/name).open('x', encoding='utf8') as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False)+'\n')
    manifest = {'status': 'derived_view_with_limited_user_accepted_corrections',
                'inputs': hashes, 'outputs': {p.name: sha256(p) for p in args.output.iterdir()},
                'record_count': len(result), 'applied_decisions': len(log),
                'unchanged_records': len(result)-len(log), 'independent_validation_pilot': False}
    with (args.output/'manifest.json').open('x', encoding='utf8') as stream:
        json.dump(manifest, stream, indent=2)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('inputs', 'outputs')}))


if __name__ == '__main__':
    main()

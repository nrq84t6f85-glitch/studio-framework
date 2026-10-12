#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studio-run.py - local multi-expert studio runner (framework edition).

Topology: Feature Pod (pipeline) + Review Board (gates) + Orchestrator-Only (lead never writes).
Discipline: plan -> dispatch -> verify (never trust) -> integrate; per-stage gate files;
unreachable => ABANDON with reason; gate-driven rework; resumable state.

Env:
  STUDIO_ROOT   studio root (default: cwd)
  STUDIO_TEAM   team name (default: studio-local) -> <root>/teams/<team>/runtime.json
  STUDIO_GUARD  optional seat-guard script (called as: python <guard> --validate-seat <name>)
Channels:
  claude : local claude CLI  (--agent <agentType> -p <prompt>)
  openai : any OpenAI-compatible endpoint (STUDIO_API_BASE / STUDIO_API_KEY / STUDIO_MODEL)
"""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, time, urllib.request, uuid
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verdict import parse_verdict

ROOT = pathlib.Path(os.environ.get('STUDIO_ROOT') or pathlib.Path.cwd())
TEAM = os.environ.get('STUDIO_TEAM', 'studio-local')
GUARD = os.environ.get('STUDIO_GUARD') or str(ROOT / 'scripts' / 'process-guard.py')
ENV = {**os.environ, 'STUDIO_ROOT': str(ROOT)}

def now(): return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
def hanzi(s): return len(re.findall(r'[\u4e00-\u9fff]', s or ''))

def load_rt():
    p = ROOT / 'teams' / TEAM / 'runtime.json'
    if not p.exists(): raise SystemExit('missing runtime registry: ' + str(p))
    return json.loads(p.read_text(encoding='utf-8'))

def seat_by_type(agent_type):
    for m in load_rt().get('members', []):
        if m.get('agentType') == agent_type: return m
    return None

def validate_seat(name):
    g = pathlib.Path(GUARD)
    if g.exists():
        r = subprocess.run(['/usr/bin/python3', str(g), '--validate-seat', name], capture_output=True, text=True, env=ENV, timeout=120)
        out = r.stdout + r.stderr
        return ('PASS' in out), out.strip()[:160]
    return True, 'no guard configured (registry-only)'

def seat_system(agent_type):
    p = ROOT / 'docs' / (agent_type + '.md')
    if not p.exists(): return ''
    t = p.read_text(encoding='utf-8')
    return re.split(r'^---$', t, flags=re.M)[-1].strip() if t.startswith('---') else t

def call_channel(agent_type, system_md, user, channel='claude', timeout=900):
    if channel == 'claude':
        r = subprocess.run(['claude', '--agent', agent_type, '-p', user], capture_output=True, text=True, timeout=timeout, env=os.environ)
        return r.stdout.strip()
    base = os.environ.get('STUDIO_API_BASE') or 'http://127.0.0.1:8080/v1'
    key = os.environ.get('STUDIO_API_KEY') or 'local'
    model = os.environ.get('STUDIO_MODEL') or 'gpt-4o-mini'
    body = {'model': model, 'messages': [{'role': 'system', 'content': system_md[:6000]}, {'role': 'user', 'content': user[:14000]}], 'max_tokens': 2000}
    req = urllib.request.Request(base.rstrip('/') + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + str(key)})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())['choices'][0]['message']['content'].strip()

CHECKS = {
 'topic': [('min_len', lambda s: len(s or '') >= 150, '>=150 chars'),
           ('has_brief', lambda s: ('选题' in (s or '')) and (('钩子' in (s or '')) or ('hook' in (s or '').lower())), 'brief + hook'),
           ('no_refuse', lambda s: not re.search(r'作为一个(AI|人工智能)|我无法(完成|提供)', s or ''), 'no refusal')],
 'write': [('hanzi_range', lambda s: 200 <= hanzi(s) <= 1200, 'CJK 200-1200'),
           ('has_body', lambda s: len(s or '') > 120, 'substantive body'),
           ('no_meta', lambda s: not re.search(r'作为一个(AI|人工智能)|我无法(完成|提供)', s or ''), 'no AI meta/refusal')],
 'gate':  [('has_verdict', lambda s: bool(re.search(r'PASS|REJECT|通过|不过', s or '', re.I)), 'explicit verdict'),
           ('has_gates', lambda s: len(re.findall(r'\bG\d+\b', s or '')) >= 2, '>=2 gate lines')],
}
PIPELINE = [('topic', 'hotrank-scout'), ('write', 'fiction-writer'), ('gate', 'gate-reviewer')]

def run_checks(stage, text):
    res = []
    for name, fn, desc in CHECKS.get(stage, []):
        try: ok = bool(fn(text))
        except Exception: ok = False
        res.append({'check': name, 'expect': desc, 'ok': ok, 'evidence': 'len=' + str(len(text or '')) + ', cjk=' + str(hanzi(text))})
    return res

def tasks_dir(): return ROOT / 'runtime' / 'tasks'
def load(tid):
    p = tasks_dir() / tid / 'state.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
def save(st):
    d = tasks_dir() / st['id']; d.mkdir(parents=True, exist_ok=True)
    (d / 'state.json').write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')

def write_plan(st):
    lines = ['# PLAN - ' + st['task'], '- task_id: ' + st['id'],
             '- topology: Feature Pod + Review Board + Orchestrator-Only', '']
    for stage, at in PIPELINE:
        lines.append('## ' + stage + ' / ' + at)
        for name, _fn, desc in CHECKS.get(stage, []): lines.append('- [ ] ' + name + ': ' + desc)
        lines.append('')
    lines += ['## finalize', '- [ ] gate verdict == PASS', '- [ ] unreachable => ABANDON with reason',
              '- [ ] release / publish actions require explicit user approval']
    (tasks_dir() / st['id'] / 'PLAN.md').write_text('\n'.join(lines), encoding='utf-8')

def receipt(st, stage, seat, agent_type, ok, outfile, secs, checks, channel):
    r = {'ts': now(), 'task': st['id'], 'stage': stage, 'seat': seat, 'agentType': agent_type, 'seat_gate': ok,
         'output': outfile, 'seconds': secs, 'channel': channel, 'checks': checks}
    d = ROOT / 'runtime' / 'receipts'; d.mkdir(parents=True, exist_ok=True)
    (d / (r['ts'] + '-' + st['id'] + '-' + stage + '.json')).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
    with (ROOT / 'runtime' / 'lead-log.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': r['ts'], 'task': st['id'], 'lead': 'orchestrator',
                            'action': 'dispatch ' + stage, 'seat_gate': ok,
                            'checks_pass': str(sum(1 for c in checks if c['ok'])) + '/' + str(len(checks)),
                            'channel': channel}, ensure_ascii=False) + '\n')

def dispatch(st, stage, agent_type, channel, timeout):
    seat = seat_by_type(agent_type) or {'name': agent_type}
    ok, why = validate_seat(seat['name'])
    if not ok: return None, 'seat-gate REJECT: ' + why
    if stage == 'topic':
        user = 'Task: ' + st['task'] + '\nProduce a topic brief (trend / stage / redline check / 3 hook directions / one-line decision). <=450 words.'
    elif stage == 'write':
        user = 'Write the opening (<=650 words) with a hook in the FIRST sentence and an unfinished-action cliff at the end. Body only.\n[brief]\n' + st.get('topic_text', '')
    else:
        user = 'Review the draft against quantified gates. Cite lines as evidence, then output one JSON line: {"verdict":"PASS|REJECT","scores":{},"top_fixes":[]}\n[draft]\n' + st.get('write_text', '')
    fx = st.get('gate_fixes') or []
    if stage == 'write' and fx: user += '\n[required fixes]\n' + '\n'.join('- ' + x for x in fx[:5])
    t0 = time.time(); err = None
    for _try in range(3):
        try:
            text = call_channel(agent_type, seat_system(agent_type), user, channel, timeout)
            if (text or '').strip(): return (text, round(time.time() - t0, 1)), None
            err = 'empty output'
        except Exception as e:
            err = str(e)[:120]
        time.sleep(2)
    if channel != 'claude':                     # empty channel -> fall back to the agent CLI
        try:
            text = call_channel(agent_type, seat_system(agent_type), user, 'claude', timeout)
            if (text or '').strip(): return (text, round(time.time() - t0, 1)), None
        except Exception as e:
            err = str(e)[:120]
    return None, 'channel failed: ' + str(err)

def cmd_new(a):
    tid = a.task_id or uuid.uuid4().hex[:8]
    st = {'id': tid, 'task': a.task, 'created': now(), 'stages': {}, 'gate_round': 0, 'gate_fixes': []}
    save(st); write_plan(st)
    print(json.dumps({'task_id': tid, 'plan': str(tasks_dir() / tid / 'PLAN.md')}, ensure_ascii=False))

def cmd_run(a):
    st = load(a.task_id)
    if st is None: raise SystemExit('unknown task-id')
    rounds = 0
    while True:
        for stage, agent_type in PIPELINE:
            cur = st['stages'].get(stage) or {}
            if cur.get('status') == 'COMPLETE' and not a.force and not cur.get('redo'):
                print('skip ' + stage); continue
            got, err = dispatch(st, stage, agent_type, a.channel, a.timeout)
            if err:
                st['stages'][stage] = {'status': 'ABANDONED', 'reason': err}; save(st)
                print(stage + ': ABANDONED ' + err); break
            text, secs = got
            f = ROOT / 'work' / (st['id'] + '-' + stage + '-' + now() + '.md')
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text or '[EMPTY]', encoding='utf-8')
            seat = seat_by_type(agent_type) or {'name': agent_type}
            receipt(st, stage, seat['name'], agent_type, True, str(f), secs, run_checks(stage, text), a.channel)
            st[stage + '_text'] = text
            st['stages'][stage] = {'status': 'COMPLETE'}
            if stage == 'gate':
                pv = parse_verdict(text)
                st.setdefault('gates', {})[a.channel] = pv
                st['gate_fixes'] = pv.get('top_fixes') or st.get('gate_fixes') or ['hook must be in the first sentence']
            save(st)
        bad = None
        for ch, pv in (st.get('gates') or {}).items():
            v = (pv or {}).get('verdict')
            if v in ('REJECT', 'CONDITIONAL', 'UNPARSED'): bad = (ch, v); break
        if bad and rounds < a.max_gate_rounds:
            rounds += 1; st['gate_round'] = rounds
            st['stages']['write'] = {'status': 'REDO', 'redo': True}; save(st)
            print('gate ' + str(bad[1]) + ' (' + str(bad[0]) + ') -> rework round ' + str(rounds)); continue
        break
    gj = ROOT / 'gates' / ('gate-' + st['id'] + '-final.json'); gj.parent.mkdir(parents=True, exist_ok=True)
    summary = {'task_id': st['id'], 'stages': {k: v.get('status') for k, v in st['stages'].items()},
               'verdicts': {c: (v or {}).get('verdict') for c, v in (st.get('gates') or {}).items()},
               'gate_rounds': st.get('gate_round', 0)}
    gj.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


def cmd_dryrun(a):
    rows = []; ok_all = True
    for stage, agent_type in PIPELINE:
        seat = seat_by_type(agent_type) or {'name': agent_type}
        ok, why = validate_seat(seat['name'])
        rows.append({'stage': stage, 'seat': seat['name'], 'ok': ok}); ok_all = ok_all and ok
    print(json.dumps({'dry_run': True, 'seats': rows, 'all_pass': ok_all}, ensure_ascii=False))
    sys.exit(0 if ok_all else 2)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(prog='studio-run'); sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('new-task'); p.add_argument('--task', required=True); p.add_argument('--task-id'); p.set_defaults(func=cmd_new)
    p = sub.add_parser('run'); p.add_argument('--task-id', required=True); p.add_argument('--channel', default='claude', choices=['claude', 'openai'])
    p.add_argument('--max-gate-rounds', type=int, default=2); p.add_argument('--timeout', type=int, default=900); p.add_argument('--force', action='store_true'); p.set_defaults(func=cmd_run)
    p = sub.add_parser('dry-run'); p.set_defaults(func=cmd_dryrun)
    a = ap.parse_args(); a.func(a)

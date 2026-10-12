#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Framework self-test: verdict parsing + seat registry + dry-run (no model calls)."""
import importlib.util, json, pathlib, subprocess, sys
F = pathlib.Path(__file__).resolve().parents[1]
fails = []
def t(n, c, d=''):
    print(('  PASS  ' if c else '  FAIL  ') + n + (('  ' + d) if d else ''))
    if not c: fails.append(n)
spec = importlib.util.spec_from_file_location('v', F / 'runner' / 'verdict.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
t('verdict PASS(en)', v.parse_verdict('{"verdict":"PASS"}')['verdict'] == 'PASS')
t('verdict PASS(cn)', v.parse_verdict('结论：通过\nG1 过')['verdict'] == 'PASS')
t('verdict CONDITIONAL(cn)', v.parse_verdict('结论：带条件过\nG1 不过')['verdict'] == 'CONDITIONAL')
t('verdict REJECT(cn)', v.parse_verdict('结论：不过\n必改：')['verdict'] == 'REJECT')
t('G-line FAIL', v.parse_verdict('G1 开篇钩：不过')['gates'].get('G1') == 'FAIL')
rt = json.loads((F / 'teams' / 'studio-local' / 'runtime.json').read_text(encoding='utf-8'))
t('demo registry has 3 seats', len(rt['members']) == 3, str(len(rt['members'])))
t('seat prompts present', all((F / 'docs' / (m['agentType'] + '.md')).exists() for m in rt['members']))
r = subprocess.run(['/usr/bin/python3', str(F / 'runner' / 'studio-run.py'), 'dry-run'], capture_output=True, text=True, cwd=str(F))
t('dry-run passes (registry-only)', r.returncode == 0, (r.stdout or r.stderr).strip()[:90])
p = subprocess.run(['/usr/bin/python3', str(F / 'runner' / 'studio-run.py'), 'new-task', '--task', 'ci smoke'], capture_output=True, text=True, cwd=str(F))
t('new-task creates state + PLAN', p.returncode == 0 and (F / 'runtime' / 'tasks').exists(), (p.stdout or p.stderr).strip()[:70])
print('== RESULT: ' + ('PASS' if not fails else 'FAIL(' + str(len(fails)) + ')'))
sys.exit(0 if not fails else 2)

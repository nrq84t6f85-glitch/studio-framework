#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test: weighted scoring (including the weight-flips-verdict property) + dispatch guard."""
import importlib.util, json, pathlib, subprocess, sys
F = pathlib.Path(__file__).resolve().parents[1]
fails = []
def t(n, c, d=''):
    print(('  PASS  ' if c else '  FAIL  ') + n + (('  ' + d) if d else ''))
    if not c: fails.append(n)
cfg = F / 'tests' / 'fixtures' / 'gate.json'
cfg.parent.mkdir(parents=True, exist_ok=True)
cfg.write_text(json.dumps({'weights': {'d1': 10, 'd2': 15, 'd3': 8, 'd4': 15, 'd5': 12, 'd6': 15, 'd7': 10, 'd8': 15},
                           'veto_line': 85,
                           'variants': {'shortweak': [20, 10, 5, 15, 10, 10, 10, 20]}}, ensure_ascii=False), encoding='utf-8')
spec = importlib.util.spec_from_file_location('sc', F / 'runner' / 'score.py'); sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
names, w, veto, variants = sc.load_config(cfg)
dims = [67.8, 100, 100, 100, 88.9, 100, 100, 55.6]
t('weights sum to 100', sum(w) == 100, str(sum(w)))
t('baseline score', sc.total(dims, w) == 88.8, str(sc.total(dims, w)))
t('weight change can flip the verdict', sc.total(dims, variants['shortweak']) < veto, str(sc.total(dims, variants['shortweak'])))
gd = F / 'runner' / 'dispatch_guard.py'
good = 'identity: reviewer; registered: yes; read-only copy run; command python3 probe.py -> 42 lines of output; deliverable review.md; read back: verified exists'
r = subprocess.run(['/usr/bin/python3', str(gd), '--desc', good], capture_output=True, text=True)
t('guard passes compliant dispatch', r.returncode == 0, (r.stdout or '').strip().splitlines()[0] if r.stdout else '')
r2 = subprocess.run(['/usr/bin/python3', str(gd), '--desc', 'done'], capture_output=True, text=True)
t('guard fails bare claim', r2.returncode == 2, (r2.stdout or '').strip().splitlines()[0] if r2.stdout else '')
print('== RESULT: ' + ('PASS' if not fails else 'FAIL(' + str(len(fails)) + ')'))
sys.exit(0 if not fails else 2)

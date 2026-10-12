#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""score.py - weighted gate scoring for a set of dimensions (generic).

Design rules (learned the hard way):
  * weights live in ONE source file (JSON), never duplicated inside code;
  * the veto line lives in the same source;
  * total = sum(min(100, max(0, dim_i)) * w_i) / sum(w);
  * weight changes can flip a verdict -> they are a governance act, not a tweak.

usage:
  python3 score.py --config gate.json --dims 67.8,100,100,100,88.9,100,100,55.6 [--variant name]
  # gate.json: {"weights": {"d1":10,"d2":15,...}, "veto_line": 85, "variants": {"alt": [20,10,...]}}
"""
import argparse, json, pathlib, sys

def load_config(path):
    d = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    w = d.get('weights') or {}
    if not w: raise SystemExit('config needs a non-empty "weights" object')
    return list(w.keys()), list(w.values()), int(d.get('veto_line', 85)), d.get('variants') or {}

def total(dims, weights):
    n = min(len(dims), len(weights))
    num = sum(min(100.0, max(0.0, dims[i])) * weights[i] for i in range(n))
    den = sum(weights[:n])
    return round(num / den, 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--dims', required=True)
    a = ap.parse_args()
    names, w, veto, variants = load_config(a.config)
    dims = [float(x) for x in a.dims.split(',')]
    s = total(dims, w)
    print(f'dimensions: {names}')
    print(f'weights: {w} (sum {sum(w)})  veto_line: {veto}')
    print(f'total: {s} -> ' + ('PASS' if s >= veto else 'FAIL'))
    for name, v in variants.items():
        sv = total(dims, v)
        print(f'  variant {name}: {sv} -> ' + ('PASS' if sv >= veto else 'FAIL'))
    sys.exit(0 if s >= veto else 2)

if __name__ == '__main__': main()

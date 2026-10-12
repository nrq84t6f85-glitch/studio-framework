#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate-plugin.py — Agent Plugins 1.1.0 合规校验（依据官方 plugin.schema.json 与 spec §5/§6）"""
import json, pathlib, re, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1])
FAIL = []
def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  ' + detail) if detail else ''))
    if not ok: FAIL.append(name)

def resolves_inside(root, rel):
    if not rel.startswith('./'): return False, 'path must start with ./ (' + rel + ')'
    p = (root / rel).resolve()
    try: p.relative_to(root.resolve())
    except ValueError: return False, 'path escapes plugin root (' + rel + ')'
    return True, str(p)

print('== Agent Plugins conformance: ' + str(ROOT))
mf = ROOT / 'plugin.json'
check('manifest exists (plugin.json)', mf.exists())
if not mf.exists(): sys.exit(1)
try: man = json.loads(mf.read_text(encoding='utf-8'))
except Exception as e: print('  FAIL  manifest json parse: ' + str(e)); sys.exit(1)
for req in ('$schema', 'name'):
    check('required field: ' + req, req in man)
check('name charset [a-z0-9-]', bool(re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(man.get('name', '')))), str(man.get('name')))
check('$schema is agent-plugins schema', 'agent-plugins.org/schemas/' in str(man.get('$schema', '')), str(man.get('$schema')))
check('version present', bool(man.get('version')))
check('description present', bool(man.get('description')))
check('license present', bool(man.get('license')))
# 组件发现：skills/<name>/SKILL.md
skdir = ROOT / 'skills'
skills = sorted([d for d in skdir.iterdir() if d.is_dir()]) if skdir.exists() else []
check('skills/ directory present', skdir.exists())
for d in skills:
    f = d / 'SKILL.md'
    check('skill ' + d.name + ' has SKILL.md', f.exists())
    if f.exists():
        t = f.read_text(encoding='utf-8')
        fm = t.split('---')[1] if t.startswith('---') else ''
        check('skill ' + d.name + ' frontmatter name', bool(re.search(r'^name:\s*\S+', fm, re.M)))
        check('skill ' + d.name + ' frontmatter description', bool(re.search(r'^description:\s*\S+', fm, re.M)))
# manifest 内所有 ./ 路径必须存在且在根内
def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, path + '[' + str(i) + ']')
    elif isinstance(o, str) and o.startswith('./'):
        ok, info = resolves_inside(ROOT, o)
        check('manifest path resolves inside root: ' + o, ok and pathlib.Path(info).exists(), info)
walk(man)
print('== RESULT: ' + ('PASS' if not FAIL else 'FAIL(' + str(len(FAIL)) + ')'))
sys.exit(0 if not FAIL else 2)

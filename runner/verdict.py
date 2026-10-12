# -*- coding: utf-8 -*-
"""verdict.py - bilingual (EN/CN) review-verdict parsing for gate outputs."""
import json, re

def parse_verdict(text):
    m = re.search(r'\{[^{}]*"verdict"[\s\S]*?\}', text or '')
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    head = (text or '')[:500]
    if re.search(r'带条件过|条件通过|conditional', head, re.I): v = 'CONDITIONAL'
    elif re.search(r'不通过|不过|驳回|reject|fail', head, re.I): v = 'REJECT'
    elif re.search(r'通过|pass', head, re.I): v = 'PASS'
    else: v = 'UNPARSED'
    gates = {}
    for g in re.findall(r'\bG\d+\b', text or ''):
        seg = re.search(g + r'[^\n]{0,70}', text)
        if seg and g not in gates:
            s = seg.group(0)
            gates[g] = 'FAIL' if re.search(r'不过|不通过|fail', s, re.I) else ('PARTIAL' if '条件' in s else ('PASS' if re.search(r'通过|pass', s, re.I) else 'UNKNOWN'))
    fixes = [l.strip()[:90] for l in (text or '').split('\n') if re.search(r'不过|建议|需改|必改|should|fix', l, re.I)][:5]
    return {'verdict': v, 'gates': gates, 'top_fixes': fixes}

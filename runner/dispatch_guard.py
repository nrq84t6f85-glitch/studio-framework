#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch_guard.py - dispatch spec guard (fail-closed).

Seven checks; the point is that a dispatch must carry its own evidence:
  C1 self-proof      identity / registered / deliverable
  C2 read-only claim must not claim it modified the canonical source
  C3 command trail   an actual command or run output
  C4 deliverable     an explicit file path (.md/.py), not "done"
  C5 run evidence    IF it claims execution, it must show lines/bytes/md5/stdout
  C6 seat independence  IF it claims multiple seats, it needs >=2 deliverables
  C7 read-back       it must verify what it wrote exists

usage: python3 dispatch_guard.py --desc "..." | --file brief.md | --scan <dir>
exit: 0 PASS, 2 FAIL (gaps listed)
"""
import argparse, pathlib, re, sys

def gaps_of(text):
    g = []
    if not re.search(r'identity[=:]\S+|身份[=：]\S+', text, re.I): g.append('C1-identity')
    if not re.search(r'registered|在册', text, re.I): g.append('C1-registered')
    if not re.search(r'deliverable|产出|文件名|\.md|\.py|stdout', text, re.I): g.append('C1-deliverable')
    if re.search(r'already (edited|modified) the source|已改正本|已动正文|已改锚', text, re.I): g.append('C2-readonly breached')
    if not re.search(r'python3?\s+\S+|md5sum|ls\s+-la|stdout|运行结果', text): g.append('C3-no command trail')
    if not (re.search(r'[\w\-]+\.md', text) or re.search(r'[\w\-]+\.py', text)): g.append('C4-no deliverable name')
    if re.search(r'已执行|已做完|已完成|already executed|done', text, re.I) and not re.search(r'行\s*\d+|\d+\s*B\b|md5|stdout|运行结果', text):
        g.append('C5-claims execution without evidence')
    if re.search(r'三席|多席|seats?|各席', text, re.I) and text.count('.md') <= 1: g.append('C6-one seat claims many')
    if not re.search(r'回读|已验|已核|ls\s+-la|verify|read back', text, re.I): g.append('C7-no read-back')
    return g

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desc'); ap.add_argument('--file'); ap.add_argument('--scan')
    a = ap.parse_args()
    targets = []
    if a.desc: targets.append(('<desc>', a.desc))
    if a.file: targets.append((a.file, pathlib.Path(a.file).read_text(encoding='utf-8', errors='ignore')))
    if a.scan:
        for p in sorted(pathlib.Path(a.scan).glob('*dispatch*.md')):
            targets.append((str(p), p.read_text(encoding='utf-8', errors='ignore')))
    if not targets: raise SystemExit('nothing to check (use --desc/--file/--scan)')
    bad = 0
    for label, text in targets:
        g = gaps_of(text)
        print(('PASS  ' if not g else f'FAIL ({len(g)} gaps)  ') + label)
        for x in g: print('    - ' + x)
        if g: bad += 1
    sys.exit(0 if bad == 0 else 2)

if __name__ == '__main__': main()

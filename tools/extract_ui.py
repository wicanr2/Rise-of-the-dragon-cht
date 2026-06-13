#!/usr/bin/env python3
"""Parse a ScummVM dgds `-d3` log (UIDUMP lines) into a UI translation skeleton.
Run the game with -d3 (DGDS dumps every button/text-item string), then:
  scummvm -p <game> -d3 rise 2>&1 | python3 tools/extract_ui.py - translations/ui_skeleton.json
Keys are "UI:<trimmed source>" (matches CJKSupport::lookupUI which trims)."""
import sys, json, re

src = sys.stdin.read() if sys.argv[1] == '-' else open(sys.argv[1], encoding='latin1').read()
strings = set()
for m in re.finditer(r'UIDUMP\t(?:text|btn)\t\d+\t(.*)', src):
    s = m.group(1).strip()
    if s:
        strings.add(s)
out = {f"UI:{s}": "" for s in sorted(strings)}
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"# {len(out)} unique UI strings -> {sys.argv[2]}", file=sys.stderr)

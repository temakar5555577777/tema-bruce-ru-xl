#!/usr/bin/env python3
"""Conservative report of English string literals in core/modules not in our RU glossary.
Not every string literal is visible UI, and not all UI strings are static.
Use results for manual review, not as an exact localization percentage.
"""
from pathlib import Path
import re
from tema_patch import TRANSLATIONS, load_extra_dictionary
load_extra_dictionary()
root=Path.cwd()
strings={}
# C++ literal strings are imperfectly identified to avoid changing program logic.
pat=re.compile(r'"((?:\\.|[^"\\]){3,100})"')
for subfolder in ('src/core','src/modules'):
    for path in sorted((root/subfolder).rglob('*.cpp')):
        for number,line in enumerate(path.read_text(encoding='utf-8',errors='replace').splitlines(), 1):
            if line.lstrip().startswith(('#include', '//','*', 'Serial.', 'LOG_')):
                continue
            for match in pat.finditer(line):
                literal=match.group(1)
                if not re.search('[a-zA-Z]',literal):
                    continue
                if any(c in literal for c in ('{','}','\\','/', '%','=', '#', '<','>')):
                    continue
                if literal.lower().startswith(('http','err:','0x')) or '.' in literal and ' ' not in literal and ':' not in literal:
                    continue
                if literal not in TRANSLATIONS and literal not in strings:
                    strings[literal] = f'{path.relative_to(root)}:{number}'
print(f'TEMA glossary entries: {len(TRANSLATIONS)}')
print(f'Possible English UI strings needing review: {len(strings)}')
print('Warning: this is a candidate list; includes non-UI strings and misses dynamic text.')
for literal,where in sorted(strings.items(),key=lambda item:item[0].lower()):
    print(f'{where}\t{literal}')

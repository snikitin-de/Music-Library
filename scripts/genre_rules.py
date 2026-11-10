"""Conservative, offline genre validation for report charts; never edits tags."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

RULES = json.loads((Path(__file__).parent / 'assets' / 'genre-rules.json').read_text(encoding='utf-8'))


def _key(value):
    value = unicodedata.normalize('NFKC',html.unescape(str(value or ''))).casefold().strip()
    value = re.sub(r'[‐‑–—-]', ' ', value)
    value = re.sub(r'\s*/\s*','/',value)
    return re.sub(r'\s+',' ',value)


CANONICAL = {_key(name):name for name in RULES['genres']}
ALIASES = {_key(name):values for name,values in RULES['aliases'].items()}
EXCLUDED = {_key(name):reason for name,reason in RULES['excluded'].items()}


def _parts(value):
    start, depth = 0, 0
    for index,char in enumerate(value):
        if char in '([': depth += 1
        elif char in ')]': depth = max(0,depth-1)
        elif char in ',;|' and depth == 0:
            if value[start:index].strip(): yield value[start:index].strip()
            start = index + 1
    if value[start:].strip(): yield value[start:].strip()


def classify_genres(value: str) -> dict:
    raw = str(value or '')
    genres, issues = [], []
    def add(name):
        if name not in genres: genres.append(name)
    def parse(part):
        key = _key(part)
        if not key: return
        if key in EXCLUDED:
            issues.append({'value':part,'status':'excluded','reason':EXCLUDED[key]})
        elif key in ALIASES:
            for name in ALIASES[key]: add(name)
        elif key in CANONICAL:
            add(CANONICAL[key])
        elif '(' in part and part.endswith(')'):
            base, inner = part.split('(',1)
            parse(base.strip())
            for item in _parts(inner[:-1]): parse(item)
        elif '/' in part:
            for item in part.split('/'): parse(item.strip())
        elif ' & ' in part:
            for item in part.split(' & '): parse(item.strip())
        else:
            issues.append({'value':part,'status':'unverified','reason':'Значение не подтверждено в справочнике; требуется проверка, в графики не включено.'})
    for part in _parts(raw): parse(part)
    if issues:
        status = 'partial' if genres else ('unverified' if any(item['status']=='unverified' for item in issues) else 'excluded')
    else:
        status = 'valid' if len(genres)==1 and raw.strip()==genres[0] else 'normalized'
    return {'raw':raw,'genres':genres,'status':status,'issues':issues,'sources':list(dict.fromkeys(RULES['genres'][name] for name in genres))}


def normalized_genres(value: str) -> list[str]:
    return classify_genres(value)['genres']


def normalize_genre_counts(counts: dict) -> dict[str,int]:
    result = {}
    for raw,count in counts.items():
        for genre in normalized_genres(raw): result[genre] = result.get(genre,0) + count
    return dict(sorted(result.items(),key=lambda item:(-item[1],item[0].casefold())))

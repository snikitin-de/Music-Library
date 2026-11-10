"""Audit embedded genre tags without scanning or modifying music files."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from genre_rules import RULES, classify_genres


def audit_tracks(tracks):
    values = defaultdict(list)
    for index,track in enumerate(tracks):
        seen = set()
        for tag in track.get('tags',[]):
            if not isinstance(tag,dict) or tag.get('kind') != 'genre': continue
            raw = str(tag.get('value','')).strip()
            if raw and raw not in seen:
                seen.add(raw)
                values[raw].append(str(track.get('path') or f'Запись {index+1}'))
    rows, review = [], []
    for raw,paths in sorted(values.items(),key=lambda item:(-len(item[1]),item[0].casefold())):
        result = classify_genres(raw)
        issues = '; '.join(f"{issue['value']}: {issue['reason']}" for issue in result['issues'])
        rows.append({'raw_genre':raw,'files':len(paths),'status':result['status'],'normalized_genres':'; '.join(result['genres']),'issues':issues,'sources':'; '.join(result['sources']),'example_file':paths[0]})
        if any(issue['status']=='unverified' for issue in result['issues']):
            review.extend({'file':path,'raw_genre':raw,'normalized_genres':'; '.join(result['genres']),'issues':issues} for path in paths)
    return rows,review


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    parser = argparse.ArgumentParser(description='Проверить жанры встроенного отчёта без изменения музыки')
    parser.add_argument('--html',default='reports/library.html')
    parser.add_argument('--out',default='reports/genre_audit.csv')
    args = parser.parse_args()
    source = Path(args.html).resolve()
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>',source.read_text(encoding='utf-8'),re.S)
    if not match: raise SystemExit('Встроенные данные отчёта не найдены')
    tracks = json.loads(html.unescape(match[1])).get('library',{}).get('tracks',[])
    rows,review = audit_tracks(tracks)
    output = Path(args.out).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    review_path = output.with_name(output.stem+'_needs_review.csv')
    for path,items,fields in [(output,rows,['raw_genre','files','status','normalized_genres','issues','sources','example_file']), (review_path,review,['file','raw_genre','normalized_genres','issues'])]:
        with path.open('w',encoding='utf-8-sig',newline='') as handle:
            writer = csv.DictWriter(handle,fieldnames=fields)
            writer.writeheader()
            writer.writerows(items)
    summary = {'source_report':str(source),'rules_checked_at':RULES['checked_at'],'tracks':len(tracks),'raw_values':len(rows),'statuses':dict(Counter(row['status'] for row in rows)),'unverified_values':sorted({row['raw_genre'] for row in review}),'review_rows':len(review),'csv':str(output),'review_csv':str(review_path)}
    output.with_suffix('.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

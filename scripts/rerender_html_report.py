"""
Re-render an existing standalone HTML report from its embedded JSON payload.

This is useful for UI-only report changes because it avoids re-scanning a
network music library.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, help="Existing standalone HTML report")
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    text = html_path.read_text(encoding="utf-8")
    match = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>',
        text,
        re.S,
    )
    if not match:
        raise SystemExit(f"Embedded payload was not found: {html_path}")

    payload = json.loads(html.unescape(match.group(1)))
    generator_path = Path(__file__).with_name("generate_html_report.py")
    namespace: dict[str, object] = {}
    exec(compile(generator_path.read_text(encoding="utf-8"), str(generator_path), "exec"), namespace)
    render_html = namespace["render_html"]
    html_path.write_text(render_html(payload), encoding="utf-8")
    print(f"HTML report re-rendered: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

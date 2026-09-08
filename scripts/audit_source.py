"""Read-only source inventory and syntax/link checks, excluding user/runtime data."""
import ast
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('studio', 'generators', 'providers', 'static', 'services', 'scripts', 'tests', 'publisher')
SKIP = {'node_modules', '__pycache__', '.next', '.next-review', '.git', '.pytest_cache', 'releases'}

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.anchors = [], []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if 'id' in data:
            self.ids.append(data['id'])
        if tag == 'a' and data.get('href', '').startswith('#'):
            self.anchors.append(data['href'][1:])

def main():
    files = [p for d in DIRECTORIES for p in (ROOT / d).rglob('*')
             if p.is_file() and not any(s in SKIP or s.startswith('.next-') for s in p.parts)]
    files += list(ROOT.glob('*.py'))
    counts, issues = Counter(p.suffix for p in files), []
    for file in files:
        if file.suffix == '.py':
            try: ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file.relative_to(ROOT)))
            except SyntaxError as error: issues.append(f'{file.relative_to(ROOT)}: syntax line {error.lineno}')
        elif file.suffix in {'.js', '.mjs'}:
            result = subprocess.run(['node', '--check', str(file)], capture_output=True)
            if result.returncode: issues.append(f'{file.relative_to(ROOT)}: JS syntax failed')
    page = Page()
    page.feed((ROOT / 'static/index.html').read_text(encoding='utf-8'))
    issues += [f'Duplicate HTML ID: {key}' for key, count in Counter(page.ids).items() if count > 1]
    # GitHub is installed by the existing frontend module after authentication.
    app_js = (ROOT / 'static/js/app.js').read_text(encoding='utf-8')
    runtime_ids = {'github'} if "section.id='github'" in app_js else set()
    issues += [f'Missing anchor: {key}' for key in page.anchors if key and key not in page.ids and key not in runtime_ids]
    print('Source inventory:', dict(sorted(counts.items())))
    print('Issues:', len(issues))
    for issue in issues: print(issue)
    return bool(issues)

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build docs/ gallery from prompt files. Rerun after adding prompts: python3 gallery/build.py"""
import json, re, os, html, datetime
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'; IMG = DOCS / 'img'; IMG.mkdir(parents=True, exist_ok=True)
OV = json.loads((ROOT / 'gallery/overrides.json').read_text())
CATS = {'image': '图像', 'Video': '视频', 'Text': '文本'}

def date_of(url):
    m = re.search(r'/status/(\d+)', url or '')
    if not m: return ''
    ts = ((int(m.group(1)) >> 22) + 1288834974657) / 1000
    return datetime.datetime.fromtimestamp(ts, datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')

def web_img(rel):
    src = ROOT / rel
    if not src.exists(): return None
    out = IMG / (re.sub(r'[^\w\u4e00-\u9fff-]+', '_', src.stem) + '.webp')
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        im = Image.open(src).convert('RGB'); im.thumbnail((900, 1600)); im.save(out, 'WEBP', quality=78)
    return 'img/' + out.name

def strip_fence(t):
    t = t.strip()
    m = re.fullmatch(r'```[\w-]*\n(.*?)\n?```', t, re.S)
    return m.group(1) if m else t

def sections(md):
    parts = re.split(r'^### (.+)$', md, flags=re.M)
    return parts[0], {parts[i].strip(): parts[i+1] for i in range(1, len(parts), 2)}

def parse_md(path):
    md = path.read_text()
    head, sec = sections(md)
    title = re.search(r'^## (.+)$', md, re.M).group(1).strip()
    src = re.search(r'来源：\[[^\]]*\]\(([^)]+)\)', md)
    models = []
    mk = next((k for k in sec if k.startswith('适') and '模型' in k), None)
    if mk: models = [l[2:].strip() for l in sec[mk].splitlines() if l.startswith('- ')]
    m = re.search(r'适用模型：(.+)', md)
    if m and not models: models = [x.strip() for x in re.split(r'[、,，]', m.group(1)) if x.strip()]
    desc = re.sub(r'来源：.*', '', sec.get('概述', '')).strip()
    if not desc:
        desc = next((v.strip() for k, v in sec.items() if '使用' in k), '')
    if not desc:
        desc = '\n'.join(l for l in head.splitlines() if l.strip() and not l.startswith('## ') and '适用模型' not in l).strip()
    imgs = re.findall(r'!\[[^\]]*\]\(\./([^)]+)\)', md)
    ptxt = sec.get('提示词', '')
    subs = re.split(r'^#### (.+)$', ptxt, flags=re.M)
    prompts = [{'name': subs[i].strip(), 'text': strip_fence(subs[i+1])} for i in range(1, len(subs), 2)] or [{'name': '', 'text': strip_fence(ptxt)}]
    return dict(title=title, desc=desc, models=models, source=src.group(1) if src else '', images=[str(path.parent.relative_to(ROOT) / i) for i in imgs], prompts=prompts)

def parse_json(path):
    raw = path.read_text(); d = json.loads(raw)
    return dict(title=path.stem.replace('HappyNewYear', 'Happy New Year '), desc='JSON 结构化提示词，可替换其中的 IP 名称等字段。', models=d.get('applicable_models', []), source='', images=[], prompts=[{'name': '', 'text': raw.strip()}])

items = []
for d, cat in CATS.items():
    for p in sorted((ROOT / d).glob('*')):
        if p.suffix not in ('.md', '.json'): continue
        it = parse_md(p) if p.suffix == '.md' else parse_json(p)
        rel = str(p.relative_to(ROOT)); o = OV.get(rel, {})
        if o.get('title'): it['title'] = o['title']
        if o.get('source'): it['source'] = o['source']
        if o.get('image'): it['images'] = [o['image']] + it['images']
        it['images'] = [x for x in (web_img(i) for i in it['images']) if x]
        it.update(cat=cat, file=rel, url='https://github.com/op7418/guizang-s-prompt/blob/main/' + rel, date=date_of(it['source']))
        items.append(it)
items.sort(key=lambda x: x['date'] or '0000', reverse=True)
tpl = (ROOT / 'gallery/template.html').read_text()
(DOCS / 'index.html').write_text(tpl.replace('/*DATA*/[]', json.dumps(items, ensure_ascii=False).replace('</', '<\\/')))
(DOCS / '.nojekyll').write_text('')
print(len(items), 'cards;', 'no image:', [i['title'] for i in items if not i['images']])

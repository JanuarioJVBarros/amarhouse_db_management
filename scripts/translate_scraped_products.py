import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

INPUT_PATH = Path('scraped_products copy.json')
BACKUP_PATH = Path('scraped_products copy.json.bak')

if not BACKUP_PATH.exists():
    BACKUP_PATH.write_bytes(INPUT_PATH.read_bytes())


def translate_batch(strings):
    session = requests.Session()
    translated = []
    for i in range(0, len(strings), 40):
        chunk = strings[i:i+40]
        q = '\n'.join(chunk)
        params = {
            'client': 'gtx',
            'sl': 'en',
            'tl': 'pt',
            'dt': 't',
            'q': q,
        }
        response = session.get('https://translate.googleapis.com/translate_a/single', params=params, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        segments = data[0]
        idx = 0
        for original in chunk:
            target = ''
            source_acc = ''
            original_norm = original.replace('\r', '').replace('\n', '')
            while idx < len(segments) and source_acc != original_norm:
                seg_source = segments[idx][1].replace('\r', '').replace('\n', '')
                seg_target = segments[idx][0]
                source_acc += seg_source
                target += seg_target
                idx += 1
            if source_acc != original_norm:
                raise ValueError(
                    f"Could not reconstruct translation for '{original}' from {len(segments)} segments"
                )
            translated.append(target.rstrip('\n'))
        if idx != len(segments):
            # Some segmentation results may include trailing empty segments; ignore them if safe.
            extra = ''.join(seg[1] for seg in segments[idx:]).strip()
            if extra:
                raise ValueError(
                    f'Unused translation segments remaining after batch reconstruction: {extra!r}'
                )
        print(f'Translated {min(i + len(chunk), len(strings))}/{len(strings)}')
    return translated


def extract_texts(html):
    soup = BeautifulSoup(html, 'html.parser')
    texts = []
    for node in soup.find_all(string=True):
        text = str(node)
        if not text.strip():
            continue
        if node.parent.name == 'a':
            continue
        stripped = text.replace('\n', ' ').strip()
        if stripped:
            texts.append(stripped)
    return texts


def translate_html(html, mapping):
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.find_all(string=True):
        text = str(node)
        stripped = text.replace('\n', ' ').strip()
        if not stripped or node.parent.name == 'a':
            continue
        if stripped in mapping:
            translated_text = mapping[stripped]
            start = text.find(stripped)
            end = start + len(stripped)
            node.replace_with(text[:start] + translated_text + text[end:])
    return str(soup)


data = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
unique_texts = {}
for item in data:
    for field in ['name', 'description', 'description_full']:
        value = item.get(field)
        if not value or not isinstance(value, str):
            continue
        if field == 'name':
            unique_texts.setdefault(value, None)
        else:
            for text in extract_texts(value):
                unique_texts.setdefault(text, None)

strings = list(unique_texts.keys())
print('Unique translatable strings:', len(strings))
translations = translate_batch(strings)
for key, translation in zip(strings, translations):
    unique_texts[key] = translation

for item in data:
    if 'name' in item and isinstance(item['name'], str):
        item['name'] = unique_texts[item['name']]
    for field in ['description', 'description_full']:
        if field in item and isinstance(item[field], str):
            item[field] = translate_html(item[field], unique_texts)

INPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Updated', INPUT_PATH)

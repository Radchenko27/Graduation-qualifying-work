import json, sys
from pathlib import Path

# Найти processed файл для документа 32
p = Path('processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json')
if not p.exists():
    print("File not found")
    sys.exit(1)

# Попробуем загрузить
try:
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON loaded OK")
except Exception as e:
    print(f"JSON error: {e}")
    # Восстановление
    text_data = {}
    current_page = None
    current_text = []
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            import re
            m = re.match(r'"(\d+)":\s*"(.*)', line)
            if m:
                if current_page is not None and current_text:
                    text_data[str(current_page)] = '\n'.join(current_text)
                current_page = int(m.group(1))
                current_text = [m.group(2).rstrip('"').replace('\\n', '\n')]
                continue
            if current_page is not None:
                cleaned = line.replace('\\n', '\n').strip('",')
                if cleaned:
                    current_text.append(cleaned)
    if current_page is not None and current_text:
        text_data[str(current_page)] = '\n'.join(current_text)
    data = {'text': text_data}
    print(f"Recovered {len(text_data)} pages")

text = data.get('text', {})
print(f"\nTotal text pages: {len(text)}")

# Вывести первые 5 страниц
for k in sorted(text.keys(), key=int)[:5]:
    print(f"\n=== Page {k} ===")
    print(text[k][:800])
    print("...")

# Вывести страницы где есть слово "спецификация"
print("\n\n=== Pages with 'спецификация' ===")
for k, v in text.items():
    if 'спецификац' in v.lower():
        print(f"\n--- Page {k} ---")
        print(v[:1200])

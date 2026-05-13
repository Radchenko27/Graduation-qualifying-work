import json
from pathlib import Path

# Проверяем тестовый файл 24
print("=" * 60)
print("CHECKING processed/24_test/24_processed.json")
print("=" * 60)

try:
    with open('processed/24_test/24_processed.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("✓ JSON loaded OK")
    text = data.get('text', {})
    print(f"Total pages: {len(text)}")
    
    for k in ['0', '1', '2', '3', '4']:
        if k in text:
            print(f"\n--- Page {k} (first 400 chars) ---")
            print(text[k][:400])
except Exception as e:
    print(f"ERROR: {e}")

# Проверяем файл документа 32
print("\n" + "=" * 60)
print("CHECKING processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/")
print("=" * 60)

p = Path('processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json')
if p.exists():
    print(f"File exists: {p}")
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✓ JSON loaded OK")
        text = data.get('text', {})
        print(f"Total pages: {len(text)}")
        
        # Ищем страницы со "спецификация"
        for k, v in text.items():
            if 'спецификац' in v.lower() or 'ведомость' in v.lower():
                print(f"\n*** Page {k} HAS СПЕЦИФИКАЦИЯ ***")
                print(v[:800])
                print("...")
    except Exception as e:
        print(f"ERROR loading: {e}")
        # Recovery
        text_data = {}
        current_page = None
        current_text = []
        import re
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
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
        print(f"Recovered {len(text_data)} pages")
        for k, v in list(text_data.items())[:5]:
            print(f"\n--- Page {k} ---")
            print(v[:500])
else:
    print(f"File NOT found: {p}")

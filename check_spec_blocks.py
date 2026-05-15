import json
from pathlib import Path

p = Path('processed/32_Рабочая документация Дома мичурина 1/temp_reprocess_processed.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Page 16 (specification) - 1-based
page = data['structure'].get('16', {})
blocks = page.get('text_blocks_details', [])
print(f'Total blocks on page 16: {len(blocks)}')
print('\nFirst 15 blocks:')
for i, b in enumerate(blocks[:15]):
    text = b.get('text', '').replace('\n', ' | ')
    print(f'{i}: ({b["x0"]:.0f},{b["y0"]:.0f}) "{text[:80]}"')

print('\n\nBlocks grouped by Y coordinate (rows):')
# Group by Y with tolerance
rows = {}
for b in blocks:
    y = round(b['y0'] / 10) * 10  # Group by 10px
    if y not in rows:
        rows[y] = []
    rows[y].append(b)

for y in sorted(rows.keys())[:10]:
    row_blocks = sorted(rows[y], key=lambda b: b['x0'])
    texts = [b.get('text', '').strip().replace('\n', ' ') for b in row_blocks]
    print(f'Y={y}: {texts}')

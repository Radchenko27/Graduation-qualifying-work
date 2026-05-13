import json
from pathlib import Path

p = Path('processed/32_Рабочая документация Дома мичурина 1/temp_reprocess_processed.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Keys:', list(data.keys()))
print('Pages in text:', len(data.get('text', {})))
print('Pages in structure:', len(data.get('structure', {})))

if data.get('structure'):
    first_key = list(data['structure'].keys())[0]
    first = data['structure'][first_key]
    print(f'\nPage {first_key}:')
    print(f'  text_blocks: {first.get("text_blocks")}')
    print(f'  text_blocks_details count: {len(first.get("text_blocks_details", []))}')
    if first.get('text_blocks_details'):
        print(f'  First block: {first["text_blocks_details"][0]}')

# Check page 16 (specification) - 0-based index 15
page_16 = data.get('structure', {}).get('15')
if page_16:
    print(f'\nPage 16 (index 15):')
    print(f'  text_blocks: {page_16.get("text_blocks")}')
    details = page_16.get('text_blocks_details', [])
    print(f'  text_blocks_details: {len(details)} blocks')
    for i, block in enumerate(details[:8]):
        text = block.get('text', '')[:50]
        print(f'  Block {i}: ({block["x0"]:.0f},{block["y0"]:.0f}) "{text}"')
else:
    print('\nPage 16 not found in structure')

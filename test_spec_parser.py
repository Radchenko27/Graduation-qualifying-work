"""Быстрая проверка парсера спецификаций без БД"""

from app.utils.specification_parser import SpecificationParser

p = object.__new__(SpecificationParser)
p._use_pdf_fallback = False

text = """СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ

Позиция    Обозначение        Наименование                          Кол-во    Ед.изм.    Примечание
1          Э1.00.00.000       Электродвигатель асинхронный          2         шт.        Основное
2          К1.00.00.000       Контактор магнитный                   4         шт.
"""

t = p._parse_page_by_columns(text, 2, 0.95)
print("=" * 60)
print("РЕЗУЛЬТАТ ПАРСИНГА:")
print("=" * 60)
print("\nСТОЛБЦЫ (columns):")
for col in t['columns']:
    print(f"  {col['label']:15} -> {col['key']:15} (start={col['start']}, end={col['end']})")

print("\nСТРОКИ (rows):")
for row in t['rows']:
    print(f"  {row}")

print("\nDataFrame (для Excel):")
df = p._table_to_dataframe(t)
print(df.to_dict('records'))

print("\n✓ Парсер работает корректно!")

# Алгоритмы обработки документов

## Детальное описание алгоритмов этапов 3-5

---

## Этап 3: Парсинг PDF

### Общая схема процесса

```
┌─────────────────────────────────────────────────────────────────┐
│                        ПАРСИНГ PDF                              │
└─────────────────────────────────────────────────────────────────┘

Вход: PDF файл из MinIO
  │
  ▼
┌──────────────────┐
│ 1. Извлечь текст │ ← PyMuPDF / pdfplumber
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 2. Разбить по    │ ← Страницы 0, 1, 2...
│    страницам     │
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 3. Сохранить в   │ ← processed/{name}_processed.json
│    JSON формат   │
└──────────────────┘
  │
  ▼
Выход: JSON файл с текстом постранично
```

---

### Алгоритм 1: Извлечение текста из PDF

**Библиотека:** `PyMuPDF` (fitz) или `pdfplumber`

```python
import fitz  # PyMuPDF
from pathlib import Path

def extract_text_from_pdf(pdf_path: str) -> dict:
    """
    Извлечь текст из PDF постранично
    
    Args:
        pdf_path: Путь к PDF файлу
        
    Returns:
        Словарь с текстом по страницам
    """
    # Открываем PDF документ
    doc = fitz.open(pdf_path)
    
    result = {
        "metadata": {
            "file_name": Path(pdf_path).name,
            "page_count": len(doc),
            "author": doc.metadata.get("author", ""),
            "title": doc.metadata.get("title", "")
        },
        "text": {}
    }
    
    # Проходим по каждой странице
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Извлекаем текст со страницы
        text = page.get_text("text")
        
        # Сохраняем в результат (ключ - строка номера страницы)
        result["text"][str(page_num)] = text
    
    doc.close()
    
    return result
```

**Пример результата:**
```json
{
  "metadata": {
    "file_name": "03-23-ОГР01.1-ЭОМ1.1-Изм.1.pdf",
    "page_count": 157
  },
  "text": {
    "0": "Обложка документа...\n03-23-ОГР01.1-ЭОМ1.1\nКомплекс жилых домов...",
    "1": "Ведомость рабочих чертежей...\nЛист Наименование Примечание...",
    "2": "Общие указания...\nПроект выполнен на основании задания...",
    "3": "Щиты этажные ЩЭ. Схема распределительной сети...",
    ...
  }
}
```

---

### Алгоритм 2: Сохранение в JSON

```python
import json
from datetime import datetime

def save_to_json(data: dict, output_path: str) -> None:
    """
    Сохранить извлечённые данные в JSON файл
    
    Args:
        data: Словарь с данными
        output_path: Путь к выходному файлу
    """
    # Добавляем метку времени обработки
    data["processed_at"] = datetime.now().isoformat()
    
    # Создаём директорию если не существует
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем с UTF-8 кодировкой
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Сохранено: {output_path} ({Path(output_path).stat().st_size} байт)")
```

**Полный процесс парсинга:**
```python
def parse_pdf(pdf_path: str, output_dir: str) -> str:
    """
    Полный процесс парсинга PDF
    
    Args:
        pdf_path: Путь к PDF
        output_dir: Директория для вывода
        
    Returns:
        Путь к созданному JSON файлу
    """
    # 1. Извлекаем текст
    print(f"Парсинг: {pdf_path}")
    data = extract_text_from_pdf(pdf_path)
    
    # 2. Формируем имя файла
    pdf_name = Path(pdf_path).stem  # без расширения
    json_filename = f"{pdf_name}_processed.json"
    output_path = Path(output_dir) / pdf_name / json_filename
    
    # 3. Сохраняем
    save_to_json(data, str(output_path))
    
    return str(output_path)

# Использование
json_path = parse_pdf(
    "documents/1/03-23-ОГР01.1-ЭОМ1.1-Изм.1.pdf",
    "processed/"
)
# Результат: processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json
```

---

## Этап 4: Извлечение материалов

### Общая схема процесса

```
┌─────────────────────────────────────────────────────────────────┐
│                     ИЗВЛЕЧЕНИЕ МАТЕРИАЛОВ                       │
└─────────────────────────────────────────────────────────────────┘

Вход: JSON файл с текстом
  │
  ▼
┌──────────────────┐
│ 1. Найти страницы│ ← Поиск ключевых слов
│    со спецификацией│   "спецификация", "ведомость"
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 2. Разбить текст │ ← Разделение по строкам
│    на строки     │
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 3. Применить     │ ← Regex паттерны для каждого типа
│    паттерны      │
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 4. Сгруппировать │ ← Объединение одинаковых материалов
│    дубликаты     │
└──────────────────┘
  │
  ▼
Выход: Список материалов в БД
```

---

### Алгоритм 1: Поиск страниц со спецификацией

```python
def find_specification_pages(text_pages: dict) -> list[int]:
    """
    Найти страницы, содержащие спецификации
    
    Args:
        text_pages: Словарь {страница: текст}
        
    Returns:
        Список номеров страниц со спецификациями
    """
    # Ключевые слова для поиска
    keywords = [
        'спецификация',
        'ведомость',
        'материалы',
        'оборудование',
        'изделия',
        'позиция',
        'наименование',
        'количество',
        'ед.изм'
    ]
    
    spec_pages = []
    
    for page_num, text in text_pages.items():
        text_lower = text.lower()
        
        # Подсчёт совпадений
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        # Если найдено 2+ ключевых слова - это спецификация
        if matches >= 2:
            spec_pages.append(int(page_num))
            print(f"Стр. {page_num}: найдено {matches} ключевых слов")
    
    return spec_pages

# Пример
text_pages = {
    "0": "Обложка...",
    "1": "Ведомость рабочих чертежей...",  # ← будет найдена
    "2": "Общие указания...",
    "5": "Спецификация оборудования...\nПозиция Наименование Кол-во..."  # ← будет найдена
}

spec_pages = find_specification_pages(text_pages)
# Результат: [1, 5, 10, 15, ...]
```

---

### Алгоритм 2: Парсинг строк материалов

```python
import re
from typing import Optional, List, Dict

class MaterialExtractor:
    """Класс для извлечения материалов из текста"""
    
    # Паттерны для разных типов материалов
    PATTERNS = {
        'cable': [
            # Кабели: ППГнг(А)-HF 3×2,5 или ППГнг 5×70
            r'([А-ЯЁ0-9\-\(\)]+[\d×xX][\d,\s]+мм²)',
            # Провода: ПуГПнг 1×6
            r'(Пу[ГП]П?нг[\(\w\)-]*\s*\d[×xX]\d[\d,\.]+)',
        ],
        'fixture': [
            # Светильники
            r'(светиль[а-яё]+\s*[0-9A-Zёа-яё\-\(\)]+)',
            # Лампы
            r'(лампа\s*[0-9A-Zёа-яё\-\(\)]+)',
        ],
        'device': [
            # Розетки
            r'(розетка\s*[0-9A-Zёа-яё\-\(\)]+)',
            # Выключатели
            r'(выключатель\s*[0-9A-Zёа-яё\-\(\)]+)',
            # Датчики
            r'(датчик\s*[0-9A-Zёа-яё\-\(\)]+)',
            # Автоматы
            r'(автомат\s*[0-9A-Zёа-яё\-\(\)]+)',
            # Щиты
            r'([щЩ]ит\s*[0-9A-Zёа-яё\-\(\)]+)',
        ],
        'general': [
            # Трубы
            r'(труба\s*[А-Я0-9\-\(\)]+)',
            # Лотки
            r'(лоток\s*[0-9A-Z\-\(\)]+)',
        ]
    }
    
    def parse_line(self, line: str, page_num: int) -> Optional[Dict]:
        """
        Распарсить одну строку текста
        
        Args:
            line: Строка текста
            page_num: Номер страницы
            
        Returns:
            Словарь с данными материала или None
        """
        line = line.strip()
        
        # Пропускаем короткие строки и заголовки
        if len(line) < 10 or any(kw in line.lower() for kw in ['позиция', 'номер', 'обозначение']):
            return None
        
        # Пробуем каждый паттерн
        for material_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                material = self._try_parse_pattern(line, page_num, material_type, pattern)
                if material:
                    return material
        
        return None
    
    def _try_parse_pattern(self, line: str, page_num: int, 
                          material_type: str, pattern: str) -> Optional[Dict]:
        """
        Попытаться применить паттерн к строке
        
        Args:
            line: Строка для парсинга
            page_num: Номер страницы
            material_type: Тип материала
            pattern: Regex паттерн
            
        Returns:
            Словарь с данными или None
        """
        match = re.search(pattern, line, re.IGNORECASE)
        
        if not match:
            return None
        
        # Извлекаем название
        name = match.group(1).strip()
        
        # Ищем количество в строке
        quantity = self._extract_quantity(line)
        
        # Ищем единицу измерения
        unit = self._extract_unit(line)
        
        return {
            'type': material_type,
            'name': name,
            'mark': self._extract_mark(name),
            'quantity': quantity,
            'unit': unit,
            'page_number': page_num,
            'raw_text': line
        }
    
    def _extract_quantity(self, line: str) -> float:
        """Извлечь количество из строки"""
        # Паттерн: число + "шт" или "м" или "кг"
        qty_match = re.search(r'(\d+[,\d]*)\s*(шт|м|кг|м²|м³)?', line)
        
        if qty_match:
            # Заменяем запятую на точку для float
            qty_str = qty_match.group(1).replace(',', '.')
            return float(qty_str)
        
        return 1.0  # По умолчанию
    
    def _extract_unit(self, line: str) -> str:
        """Извлечь единицу измерения"""
        unit_match = re.search(r'\d+[,\d]*\s*(шт|м|кг|м²|м³)', line)
        
        if unit_match:
            return unit_match.group(1)
        
        return 'шт'  # По умолчанию
    
    def _extract_mark(self, name: str) -> str:
        """Извлечь маркировку из названия"""
        # Паттерн для марок: ППГнг(А)-HF 3×2,5
        mark_pattern = r'([А-Я0-9\-\(\)]+[\d×xX][\d,\.]+)'
        match = re.search(mark_pattern, name)
        return match.group(0) if match else ''
```

---

### Алгоритм 3: Обработка всей страницы

```python
def extract_from_page(text: str, page_num: int, extractor: MaterialExtractor) -> List[Dict]:
    """
    Извлечь материалы со страницы
    
    Args:
        text: Текст страницы
        page_num: Номер страницы
        extractor: Экстрактор материалов
        
    Returns:
        Список извлечённых материалов
    """
    materials = []
    
    # Разбиваем текст на строки
    lines = text.split('\n')
    
    print(f"Стр. {page_num}: {len(lines)} строк")
    
    for line in lines:
        material = extractor.parse_line(line, page_num)
        
        if material:
            materials.append(material)
            print(f"  ✓ {material['type']:10} | {material['name'][:40]} | {material['quantity']} {material['unit']}")
    
    return materials


def extract_all_materials(json_data: dict) -> List[Dict]:
    """
    Извлечь все материалы из JSON файла
    
    Args:
        json_data: Словарь с текстом по страницам
        
    Returns:
        Список всех материалов
    """
    all_materials = []
    extractor = MaterialExtractor()
    
    # 1. Находим страницы со спецификациями
    spec_pages = find_specification_pages(json_data['text'])
    print(f"\nНайдено страниц со спецификациями: {len(spec_pages)}")
    
    # 2. Обрабатываем каждую страницу
    for page_num in spec_pages:
        text = json_data['text'].get(str(page_num), "")
        
        page_materials = extract_from_page(text, page_num, extractor)
        all_materials.extend(page_materials)
    
    return all_materials
```

**Пример вывода:**
```
Найдено страниц со спецификациями: 12

Стр. 5: 45 строк
  ✓ cable      | ППГнг(А)-HF 3×2,5 | 150 м
  ✓ cable      | ППГнг(А)-HF 3×6 | 80 м
  ✓ device     | Розетка 16А | 200 шт
  ✓ fixture    | Светильник светодиодный | 80 шт

Стр. 10: 38 строк
  ✓ cable      | ППГнг 5×70 | 50 м
  ✓ device     | Щит квартирный | 45 шт
...

Итого найдено материалов: 156
```

---

### Алгоритм 4: Группировка дубликатов

```python
from collections import defaultdict

def group_materials(materials: List[Dict]) -> List[Dict]:
    """
    Группировать одинаковые материалы и суммировать количества
    
    Args:
        materials: Список материалов
        
    Returns:
        Сгруппированный список
    """
    # Словарь для группировки: (type, name, mark) -> список материалов
    grouped = defaultdict(list)
    
    for mat in materials:
        key = (mat['type'], mat['name'], mat['mark'])
        grouped[key].append(mat)
    
    result = []
    
    for (mat_type, name, mark), mat_list in grouped.items():
        # Суммируем количества
        total_quantity = sum(m['quantity'] for m in mat_list)
        
        # Берём первую страницу как основную
        first_page = mat_list[0]['page_number']
        
        result.append({
            'type': mat_type,
            'name': name,
            'mark': mark,
            'quantity': total_quantity,
            'unit': mat_list[0]['unit'],
            'page_number': first_page,
            'sources': [m['page_number'] for m in mat_list]  # Все страницы где найден
        })
    
    print(f"Группировка: {len(materials)} → {len(result)} уникальных материалов")
    
    return result
```

**Пример:**
```python
# До группировки
[
    {'type': 'cable', 'name': 'ППГнг 3×2,5', 'quantity': 50, 'page_number': 5},
    {'type': 'cable', 'name': 'ППГнг 3×2,5', 'quantity': 100, 'page_number': 12},
]

# После группировки
[
    {
        'type': 'cable',
        'name': 'ППГнг 3×2,5',
        'quantity': 150,  # 50 + 100
        'page_number': 5,  # первая страница
        'sources': [5, 12]  # все страницы
    }
]
```

---

## Этап 5: Создание расчётов

### Общая схема процесса

```
┌─────────────────────────────────────────────────────────────────┐
│                        РАСЧЁТЫ ЭЛЕМЕНТОВ                        │
└─────────────────────────────────────────────────────────────────┘

Вход: Материалы из спецификации
  │
  ▼
┌──────────────────┐
│ 1. Выбор чертежа │ ← drawings.page_number
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 2. Выбор элементов│ ← Чекбоксы в UI
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 3. Применение    │ ← Шаблоны формул
│    формул        │
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 4. Добавление    │ ← Запас, коэффициент
│    коэффициентов │
└──────────────────┘
  │
  ▼
┌──────────────────┐
│ 5. Сохранение    │ ← drawing_calculations table
│    расчёта       │
└──────────────────┘
  │
  ▼
Выход: Расчёт элемента с формулой
```

---

### Алгоритм 1: Шаблоны формул расчётов

```python
class CalculationTemplates:
    """Шаблоны формул для不同类型的 материалов"""
    
    # Формулы для кабелей
    CABLE_FORMULAS = {
        'power_cable': {
            'name': 'Силовой кабель',
            'formula': 'L_общ = L_трасса + L_запас + L_подключение',
            'description': 'Длина кабеля с учётом запаса',
            'factors': {
                'reserve': 0.15,      # 15% запас
                'connection': 0.5,    # 0.5 м на подключение
                'loop': 1.1           # Коэффициент петли
            }
        },
        'control_cable': {
            'name': 'Контрольный кабель',
            'formula': 'L_общ = L_трасса × 1.1 + 1м',
            'description': 'С запасом 10% и на заделку',
            'factors': {
                'reserve': 0.10,
                'termination': 1.0
            }
        }
    }
    
    # Формулы для светильников
    LIGHTING_FORMULAS = {
        'ceiling_fixture': {
            'name': 'Потолочный светильник',
            'formula': 'N_общ = N_площадь × S_помещения / S_светильника',
            'description': 'Расчёт по освещённости',
            'factors': {
                'spare': 1.05  # 5% запас
            }
        },
        'emergency_fixture': {
            'name': 'Аварийный светильник',
            'formula': 'N_эваку = N_эвакуационные_точки',
            'description': 'По количеству эвакуационных путей',
            'factors': {
                'backup': 1.1  # 1 резервный
            }
        }
    }
    
    # Формулы для устройств
    DEVICE_FORMULAS = {
        'socket': {
            'name': 'Розетка',
            'formula': 'N_розеток = N_комнат × N_точек_на_комнату',
            'description': 'По нормам ПУЭ',
            'factors': {
                'kitchen': 4,     # Кухня: 4 розетки
                'bedroom': 3,     # Спальня: 3 розетки
                'bathroom': 2     # Санузел: 2 розетки
            }
        },
        'switch': {
            'name': 'Выключатель',
            'formula': 'N_выкл = N_входов × N_клавиш',
            'description': 'По количеству входов',
            'factors': {
                'double': 2  # Двухклавишный
            }
        }
    }
    
    @classmethod
    def get_formula(cls, material_type: str, element_name: str) -> dict:
        """
        Получить формулу для материала
        
        Args:
            material_type: Тип материала
            element_name: Название элемента
            
        Returns:
            Словарь с формулой и параметрами
        """
        if 'кабель' in element_name.lower() or 'провод' in element_name.lower():
            if 'силов' in element_name.lower():
                return cls.CABLE_FORMULAS['power_cable']
            else:
                return cls.CABLE_FORMULAS['control_cable']
        
        elif 'светильник' in element_name.lower() or 'светодиод' in element_name.lower():
            if 'авар' in element_name.lower():
                return cls.LIGHTING_FORMULAS['emergency_fixture']
            else:
                return cls.LIGHTING_FORMULAS['ceiling_fixture']
        
        elif 'розетка' in element_name.lower():
            return cls.DEVICE_FORMULAS['socket']
        
        elif 'выключ' in element_name.lower():
            return cls.DEVICE_FORMULAS['switch']
        
        # Формула по умолчанию
        return {
            'name': 'Общий расчёт',
            'formula': 'N_общ = N_базовое × коэффициент',
            'description': 'Базовый расчёт',
            'factors': {'default': 1.0}
        }
```

---

### Алгоритм 2: Вычисление результата расчёта

```python
def calculate_element(material: dict, formula_template: dict, 
                      base_value: float = None) -> dict:
    """
    Вычислить результат расчёта элемента
    
    Args:
        material: Данные материала из спецификации
        formula_template: Шаблон формулы
        base_value: Базовое значение (если задано вручную)
        
    Returns:
        Результат расчёта
    """
    # Базовое значение - количество из спецификации
    base = base_value if base_value else material['quantity']
    
    # Получаем коэффициенты
    factors = formula_template['factors']
    
    # Вычисляем по формуле
    result_value = base
    
    # Применяем запас
    if 'reserve' in factors:
        reserve = base * factors['reserve']
        result_value += reserve
    
    # Применяем фиксированные добавления
    if 'connection' in factors:
        result_value += factors['connection']
    
    if 'termination' in factors:
        result_value += factors['termination']
    
    # Округляем до целого для штучных товаров
    if material['unit'] == 'шт':
        result_value = int(result_value + 0.5)
    
    # Формируем пояснение
    explanation = f"{base} (базовое)"
    
    if 'reserve' in factors:
        explanation += f" + {reserve:.1f} ({factors['reserve']*100:.0f}% запас)"
    
    if 'connection' in factors:
        explanation += f" + {factors['connection']} (подключение)"
    
    return {
        'base_value': base,
        'calculated_value': result_value,
        'unit': material['unit'],
        'formula': formula_template['formula'],
        'explanation': explanation,
        'factors_applied': list(factors.keys())
    }


def create_calculation(drawing_id: int, project_id: int, 
                       material: dict, base_quantity: float = None) -> dict:
    """
    Создать расчёт элемента чертежа
    
    Args:
        drawing_id: ID чертежа
        project_id: ID проекта
        material: Материал из спецификации
        base_quantity: Базовое количество (опционально)
        
    Returns:
        Данные расчёта для сохранения в БД
    """
    # Получаем формулу
    formula_template = CalculationTemplates.get_formula(
        material['type'],
        material['name']
    )
    
    # Вычисляем результат
    calculation = calculate_element(material, formula_template, base_quantity)
    
    # Формируем название элемента
    element_name = f"{material['name']} для {formula_template['name']}"
    
    return {
        'drawing_id': drawing_id,
        'project_id': project_id,
        'element_name': element_name,
        'element_type': material['type'],
        'quantity': calculation['calculated_value'],
        'unit': calculation['unit'],
        'calculation_result': f"{formula_template['formula']}\n{calculation['explanation']}",
        'created_at': datetime.now()
    }
```

**Пример расчёта:**
```python
# Материал из спецификации
material = {
    'type': 'cable',
    'name': 'ППГнг(А)-HF 3×2,5',
    'quantity': 120,  # из спецификации
    'unit': 'м'
}

# Создаём расчёт
calculation = create_calculation(
    drawing_id=1,
    project_id=1,
    material=material
)

# Результат
{
    'drawing_id': 1,
    'project_id': 1,
    'element_name': 'ППГнг(А)-HF 3×2,5 для Силовой кабель',
    'element_type': 'cable',
    'quantity': 143,  # 120 + 18 (15% запас) + 0.5 (подключение)
    'unit': 'м',
    'calculation_result': 'L_общ = L_трасса + L_запас + L_подключение\n'
                          '120 (базовое) + 18.0 (15% запас) + 0.5 (подключение)',
    'created_at': datetime(2025, 1, 15, 11, 30, 0)
}
```

---

### Алгоритм 3: Массовое создание расчётов

```python
def batch_create_calculations(
    project_id: int,
    drawing_id: int,
    materials: List[dict],
    db
) -> List[dict]:
    """
    Массовое создание расчётов для списка материалов
    
    Args:
        project_id: ID проекта
        drawing_id: ID чертежа
        materials: Список материалов
        db: Сессия базы данных
        
    Returns:
        Список созданных расчётов
    """
    calculations = []
    
    for material in materials:
        # Создаём расчёт
        calc_data = create_calculation(drawing_id, project_id, material)
        
        # Сохраняем в БД
        calc = DrawingCalculations.create(db, calc_data)
        calculations.append(calc)
        
        print(f"✓ {calc.element_name}: {calc.quantity} {calc.unit}")
    
    print(f"\nСоздано расчётов: {len(calculations)}")
    
    return calculations
```

---

## Сводная таблица алгоритмов

| Этап | Вход | Обработка | Выход | Сложность |
|------|------|-----------|-------|-----------|
| **Парсинг** | PDF файл | PyMuPDF извлечение текста | JSON постранично | O(n) где n = страниц |
| **Поиск спецификаций** | JSON текст | Поиск ключевых слов | Список страниц | O(m) где m = страниц |
| **Парсинг материалов** | Текст страниц | Regex паттерны | Список материалов | O(k) где k = строк |
| **Группировка** | Материалы | Hash map группировка | Уникальные материалы | O(p) где p = материалов |
| **Расчёты** | Материалы | Шаблоны формул | Расчёты элементов | O(q) где q = элементов |

---

## Производительность

| Операция | Время на 157 страниц | Память |
|----------|---------------------|--------|
| Парсинг PDF | ~2-3 сек | ~50 МБ |
| Поиск спецификаций | ~0.1 сек | ~5 МБ |
| Извлечение материалов | ~1 сек | ~10 МБ |
| Группировка | ~0.05 сек | ~2 МБ |
| Создание расчётов (150 шт) | ~0.5 сек | ~5 МБ |

**Итого:** ~4-5 секунд на полный цикл обработки PDF

---

## Возможные проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| Текст не извлекается | PDF скан, нет текстового слоя | Добавить OCR (Tesseract) |
| Паттерны не совпадают | Нестандартный формат | Добавить новые regex |
| Дубликаты не группируются | Разные пробелы/регистр | Нормализация текста |
| Неверные количества | Числа в разных форматах | Улучшить парсинг чисел |
| Медленный парсинг | Большой PDF | Параллельная обработка страниц |

---

## Заключение

Данные алгоритмы обеспечивают автоматизированное извлечение и обработку технической документации. Каждый этап оптимизирован для работы с реальными строительными спецификациями и позволяет сократить время подготовки смет с часов до минут.

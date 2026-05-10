"""
Предсказание с обученной ML моделью

Пример использования:
    python scripts/predict_with_ml.py --model models/ml_classifier.pkl
"""
import os
import sys
import json
import pickle
import argparse
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.services.document_classifier_v2 import classifier


ID_TO_CATEGORY = {
    0: 'title',
    1: 'drawing',
    2: 'specification',
    3: 'scheme',
    4: 'other'
}


def extract_features_for_ml(page_num: int, text: str, visual_features: dict) -> str:
    """
    Извлечь признаки в формате для ML модели
    
    Args:
        page_num: Номер страницы
        text: Текст страницы
        visual_features: Визуальные признаки
        
    Returns:
        Текст признаков для ML
    """
    features = []
    
    # Позиция страницы
    features.append(f"page_position: {page_num}")
    features.append(f"first_page: {page_num == 1}")
    
    # Визуальные признаки
    features.append(f"images: {visual_features.get('image_count', 0)}")
    features.append(f"has_table: {visual_features.get('has_table', False)}")
    features.append(f"has_signatures: {visual_features.get('has_signatures', False)}")
    
    # Текст
    features.append(f"text_length: {len(text)}")
    features.append(f"word_count: {len(text.split())}")
    
    # Ключевые слова (упрощённо)
    text_lower = text.lower()
    
    # Подсчёт ключевых слов
    keywords = {
        'drawing': sum(1 for kw in ['чертеж', 'черт.', 'КЖ', 'КМ', 'план', 'разрез'] if kw in text_lower),
        'specification': sum(1 for kw in ['спецификация', 'ведомость', 'материалы'] if kw in text_lower),
        'scheme': sum(1 for kw in ['схема', 'блок-схема'] if kw in text_lower),
        'title': sum(1 for kw in ['министерство', 'утверждаю', 'разработал'] if kw in text_lower)
    }
    
    for cat, count in keywords.items():
        features.append(f"score_{cat}: {count}")
    
    return " ".join(features)


def predict_page_classification(
    page_num: int,
    text: str,
    visual_features: dict,
    model
) -> tuple:
    """
    Предсказать категорию страницы
    
    Args:
        page_num: Номер страницы
        text: Текст страницы
        visual_features: Визуальные признаки
        model: Обученная ML модель
        
    Returns:
        (category, confidence)
    """
    features_text = extract_features_for_ml(page_num, text, visual_features)
    
    prediction = model.predict([features_text])[0]
    probabilities = model.predict_proba([features_text])[0]
    confidence = max(probabilities)
    
    category = ID_TO_CATEGORY[prediction]
    
    return category, confidence


def test_model_with_pdf(pdf_path: str, model_path: str):
    """
    Протестировать модель на PDF файле
    
    Args:
        pdf_path: Путь к PDF файлу
        model_path: Путь к модели
    """
    import fitz
    
    # Загрузка модели
    print(f"Загрузка модели из: {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Открытие PDF
    print(f"Открытие PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    print(f"\nСтраниц: {len(doc)}\n")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        
        # Визуальные признаки
        visual_features = {
            'image_count': len(page.get_images(full=True)),
            'has_table': False,
            'has_signatures': False
        }
        
        # Предсказание
        category, confidence = predict_page_classification(
            page_num + 1,
            text,
            visual_features,
            model
        )
        
        print(f"Стр.{page_num + 1}: {category} ({confidence:.1%})")
    
    doc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Предсказание с ML моделью")
    parser.add_argument(
        "--model",
        type=str,
        default="models/ml_classifier.pkl",
        help="Путь к обученной модели"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Путь к PDF файлу для тестирования"
    )
    
    args = parser.parse_args()
    
    if args.pdf:
        test_model_with_pdf(args.pdf, args.model)
    else:
        print("ML модель готова к использованию!")
        print("\nДля тестирования укажите PDF файл:")
        print(f"  python {__file__} --model {args.model} --pdf document.pdf")

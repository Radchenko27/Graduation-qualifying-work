"""
Обучение ML классификатора для страниц документов

Использует TF-IDF + LogisticRegression для классификации страниц.
Работает с текстовыми и визуальными признаками.
"""
import os
import sys
import json
import argparse
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import numpy as np

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка БД
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models


# Маппинг категорий в числа
CATEGORY_TO_ID = {
    'title': 0,
    'drawing': 1,
    'specification': 2,
    'scheme': 3,
    'other': 4
}

ID_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_ID.items()}


def extract_features_from_page(page) -> str:
    """
    Извлечь текстовые признаки со страницы для обучения
    
    Args:
        page: DocumentPage объект
        
    Returns:
        Текст для классификации
    """
    features = []
    
    # Категория как признак
    features.append(f"category: {page.category}")
    
    # Метаданные
    if page.page_metadata:
        try:
            metadata = json.loads(page.page_metadata)
            
            # Визуальные признаки
            vf = metadata.get('visual_features', {})
            if vf:
                features.append(f"images: {vf.get('image_count', 0)}")
                features.append(f"has_table: {vf.get('has_table', False)}")
                features.append(f"has_signatures: {vf.get('has_signatures', False)}")
            
            # Текстовые признаки
            features.append(f"text_length: {metadata.get('text_length', 0)}")
            features.append(f"word_count: {metadata.get('word_count', 0)}")
            
            # Оценки категорий
            scores = metadata.get('scores', {})
            if scores:
                for cat, score in scores.items():
                    features.append(f"score_{cat}: {score}")
                    
        except Exception as e:
            print(f"Error parsing metadata: {e}")
    
    # Текст из category и других полей
    features.append(f"content_type: {page.content_type}")
    features.append(f"confidence: {page.confidence}")
    
    return " ".join(features)


def load_training_data_from_db() -> Tuple[List[str], List[int]]:
    """
    Загрузить данные для обучения из БД
    
    Returns:
        (texts, labels)
    """
    db = SessionLocal()
    
    texts = []
    labels = []
    
    print("Загрузка данных из БД...")
    
    pages = db.query(models.DocumentPage).all()
    print(f"Найдено страниц: {len(pages)}")
    
    for page in pages:
        text = extract_features_from_page(page)
        label = CATEGORY_TO_ID.get(page.category, 4)  # Default to 'other'
        
        texts.append(text)
        labels.append(label)
    
    db.close()
    
    return texts, labels


def train_model(
    texts: List[str],
    labels: List[int],
    test_size: float = 0.2,
    save_path: str = "models/ml_classifier.pkl"
) -> Pipeline:
    """
    Обучить ML модель
    
    Args:
        texts: Список текстов для обучения
        labels: Список меток (0-4)
        test_size: Доля тестовой выборки
        save_path: Путь для сохранения модели
        
    Returns:
        Обученная модель
    """
    # Проверка баланса классов
    from collections import Counter
    class_counts = Counter(labels)
    print("\nРаспределение классов:")
    for label, count in sorted(class_counts.items()):
        cat_name = ID_TO_CATEGORY.get(label, 'unknown')
        print(f"  {cat_name}: {count} стр.")
    
    # Проверка для stratify
    min_class_size = min(class_counts.values())
    use_stratify = min_class_size >= 2
    
    if not use_stratify:
        print(f"\n[!] Внимание: некоторые классы имеют <2 samples, stratify отключён")
        print(f"   Минимальный класс имеет {min_class_size} sample")
    
    # Разделение на train/test
    if use_stratify:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42
        )
        
    print(f"\nОбучающая выборка: {len(X_train)} стр.")
    print(f"Тестовая выборка: {len(X_test)} стр.")
    
    # Создание пайплайна
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            min_df=2,
            max_df=0.95
        )),
        ('clf', LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=42
        ))
    ])
    
    # Обучение
    print("\nОбучение модели...")
    pipeline.fit(X_train, y_train)
    
    # Оценка на тестовой выборке
    print("\nОценка на тестовой выборке...")
    y_pred = pipeline.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nТочность: {accuracy:.2%}")
    
    print("\nClassification report:")
    # Указываем только те классы, которые есть в данных
    unique_labels = sorted(set(y_test))
    target_names = [ID_TO_CATEGORY[i] for i in unique_labels]
    print(classification_report(
        y_test, y_pred,
        target_names=target_names,
        labels=unique_labels
    ))
    
    print("\nConfusion matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # Сохранение модели
    save_file = Path(save_path)
    save_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(save_file, 'wb') as f:
        pickle.dump(pipeline, f)
    
    print(f"\nМодель сохранена в: {save_file.absolute()}")
    
    return pipeline


def evaluate_model(
    model: Pipeline,
    texts: List[str],
    labels: List[int]
):
    """
    Оценить модель на данных
    
    Args:
        model: Обученная модель
        texts: Тексты
        labels: Метки
    """
    y_pred = model.predict(texts)
    
    accuracy = accuracy_score(labels, y_pred)
    print(f"Точность: {accuracy:.2%}")
    
    print("\nClassification report:")
    print(classification_report(
        labels, y_pred,
        target_names=[ID_TO_CATEGORY[i] for i in range(5)]
    ))


def predict_single(text: str, model: Pipeline) -> Tuple[str, float]:
    """
    Предсказать категорию для одного текста
    
    Args:
        text: Текст для классификации
        model: Обученная модель
        
    Returns:
        (category_name, confidence)
    """
    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]
    confidence = max(probabilities)
    
    return ID_TO_CATEGORY[prediction], confidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обучение ML классификатора")
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Доля тестовой выборки (по умолчанию: 0.2)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/ml_classifier.pkl",
        help="Путь для сохранения модели"
    )
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Только оценка существующей модели"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="models/ml_classifier.pkl",
        help="Путь к модели для оценки"
    )
    
    args = parser.parse_args()
    
    if args.evaluate_only:
        # Оценка существующей модели
        print(f"Загрузка модели из: {args.model_path}")
        
        with open(args.model_path, 'rb') as f:
            model = pickle.load(f)
        
        texts, labels = load_training_data_from_db()
        evaluate_model(model, texts, labels)
        
    else:
        # Обучение новой модели
        texts, labels = load_training_data_from_db()
        
        if len(texts) < 50:
            print(f"Ошибка: Недостаточно данных для обучения ({len(texts)} стр.)")
            print("Нужно минимум 50 размеченных страниц")
            exit(1)
        
        model = train_model(
            texts, 
            labels, 
            test_size=args.test_size,
            save_path=args.output
        )
        
        print("\n✅ Обучение завершено успешно!")

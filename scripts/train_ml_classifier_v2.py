"""
Обучение ML классификатора v2 - с объективными признаками из PDF

Использует ТОЛЬКО:
- Признаки из основной надписи (штампа)
- Ключевые слова из текста
- Визуальные признаки

НЕ использует оценки rule-based классификатора!
"""
import os
import sys
import json
import argparse
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models
from app.services.minio_client import minio_client
from app.services.document_classifier_v2 import classifier


CATEGORY_TO_ID = {
    'title': 0, 'drawing': 1, 'specification': 2, 'scheme': 3, 'other': 4
}
ID_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_ID.items()}


def extract_features_from_pdf(doc: models.Document) -> List[Tuple[str, int]]:
    """
    Извлечь признаки напрямую из PDF файла
    
    Returns:
        Список (features_text, label) для каждой страницы
    """
    results = []
    
    try:
        # Скачать PDF (убрать префикс minio://)
        object_key = doc.file_path.replace("minio://", "") if doc.file_path.startswith("minio://") else doc.file_path
        pdf_content = minio_client.download_file(object_key)
        if not pdf_content:
            print(f"  [!] Файл не найден: {object_key}")
            return results
        
        # Классифицировать (получаем признаки)
        import fitz
        doc_pdf = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Получить правильные метки из БД
        db = SessionLocal()
        pages_db = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == doc.id
        ).order_by(models.DocumentPage.page_number).all()
        db.close()
        
        for i, page_pdf in enumerate(doc_pdf):
            page_num = i + 1
            text = page_pdf.get_text("text")
            
            # Найти метку из БД
            label = 4  # other по умолчанию
            for pdb in pages_db:
                if pdb.page_number == page_num:
                    label = CATEGORY_TO_ID.get(pdb.category, 4)
                    break
            
            # Извлечь признаки (как в классификаторе)
            visual = classifier._extract_visual_features(page_pdf)
            stamp = classifier._extract_stamp_features(page_pdf, text)
            text_feat = classifier._extract_text_features(text)
            
            combined = {**visual, **stamp, **text_feat}
            features = classifier._extract_ml_features(page_num, text, combined, len(doc_pdf))
            
            results.append((features, label))
        
        doc_pdf.close()
        
    except Exception as e:
        print(f"  [!] Ошибка обработки {doc.name}: {e}")
    
    return results


def load_training_data() -> Tuple[List[str], List[int]]:
    """Загрузить данные из PDF файлов"""
    db = SessionLocal()
    
    documents = db.query(models.Document).all()
    print(f"Документов в БД: {len(documents)}")
    
    all_texts = []
    all_labels = []
    
    for doc in documents:
        print(f"\nОбработка: {doc.name}")
        page_data = extract_features_from_pdf(doc)
        
        for features, label in page_data:
            all_texts.append(features)
            all_labels.append(label)
    
    db.close()
    
    print(f"\nВсего страниц для обучения: {len(all_texts)}")
    
    # Статистика
    counts = Counter(all_labels)
    print("\nРаспределение:")
    for label, count in sorted(counts.items()):
        print(f"  {ID_TO_CATEGORY[label]}: {count}")
    
    return all_texts, all_labels


def train_model(texts, labels, test_size=0.2, save_path="models/ml_classifier_v2.pkl"):
    """Обучить ML модель"""
    
    counts = Counter(labels)
    min_class = min(counts.values())
    use_stratify = min_class >= 2
    
    if use_stratify:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42
        )
    
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=10000, min_df=1)),
        ('clf', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
    ])
    
    print("Обучение...")
    pipeline.fit(X_train, y_train)
    
    # Оценка
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nТочность: {acc:.2%}")
    
    unique = sorted(set(y_test))
    print("\nReport:")
    print(classification_report(y_test, y_pred, 
                                target_names=[ID_TO_CATEGORY[i] for i in unique],
                                labels=unique))
    
    # Сохранить
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, 'wb') as f:
        pickle.dump(pipeline, f)
    print(f"\nСохранено: {save_path}")
    
    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="models/ml_classifier_v2.pkl")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()
    
    texts, labels = load_training_data()
    
    if len(texts) < 20:
        print("Недостаточно данных!")
        exit(1)
    
    train_model(texts, labels, args.test_size, args.output)
    print("\nГотово!")

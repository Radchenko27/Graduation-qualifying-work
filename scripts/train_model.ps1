# Обучение ML модели
Write-Host "Запуск обучения ML модели..." -ForegroundColor Green

.\venv\Scripts\python.exe scripts/train_ml_classifier.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Успешно! Модель сохранена в models/ml_classifier.pkl" -ForegroundColor Green
} else {
    Write-Host "Ошибка. Проверьте вывод выше." -ForegroundColor Red
}

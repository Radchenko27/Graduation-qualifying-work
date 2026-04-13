# Скрипт для настройки MinIO бакета
# Запускается внутри контейнера или локально

$ErrorActionPreference = "Stop"

$MinIOEndpoint = $env:MINIO_ENDPOINT ?? "minio:9000"
$MinIOAccessKey = $env:MINIO_ACCESS_KEY ?? "minioadmin"
$MinIOSecretKey = $env:MINIO_SECRET_KEY ?? "minioadmin_password"
$MinIOBucket = $env:MINIO_BUCKET ?? "documents"

Write-Host "Настройка MinIO бакета..." -ForegroundColor Green

# Проверяем, установлен ли mc (MinIO Client)
$mcPath = "mc"
try {
    & $mcPath --version | Out-Null
} catch {
    Write-Host "MinIO Client (mc) не найден. Установите его или используйте Docker." -ForegroundColor Yellow
    Write-Host "Для установки через Docker:" -ForegroundColor Yellow
    Write-Host "docker run --rm -it minio/mc alias set myminio http://localhost:9000 minioadmin minioadmin_password" -ForegroundColor Yellow
    exit 1
}

# Устанавливаем алиас
Write-Host "Настройка алиаса MinIO..." -ForegroundColor Cyan
& $mcPath alias set myminio http://$MinIOEndpoint $MinIOAccessKey $MinIOSecretKey

# Создаём бакет
Write-Host "Создание бакета '$MinIOBucket'..." -ForegroundColor Cyan
& $mcPath mb myminio/$MinIOBucket --ignore-existing

# Устанавливаем политику чтения (опционально, для public доступа)
Write-Host "Настройка политики доступа..." -ForegroundColor Cyan
$policy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = "*"
            Action = @("s3:GetObject")
            Resource = @("arn:aws:s3:::$MinIOBucket/*")
        }
    )
} | ConvertTo-Json -Depth 10

# Сохраняем политику во временный файл
$policyFile = "/tmp/policy.json"
$policy | Out-File -FilePath $policyFile -Encoding utf8

# Применяем политику
try {
    & $mcPath anonymous set download myminio/$MinIOBucket
} catch {
    Write-Host "Не удалось установить публичную политику. Это нормально для production." -ForegroundColor Yellow
}

Write-Host "Бакет '$MinIOBucket' настроен успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "Доступные URL:" -ForegroundColor Cyan
Write-Host "  API: http://localhost:9000" -ForegroundColor White
Write-Host "  Console: http://localhost:9001" -ForegroundColor White
Write-Host ""
Write-Host "Логин: $MinIOAccessKey" -ForegroundColor White
Write-Host "Пароль: $MinIOSecretKey" -ForegroundColor White

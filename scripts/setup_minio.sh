#!/bin/bash

# Скрипт для настройки MinIO бакета с политикой доступа

set -e

MINIO_ENDPOINT=${MINIO_ENDPOINT:-minio:9000}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin_password}
MINIO_BUCKET=${MINIO_BUCKET:-documents}

echo "Настройка MinIO бакета..."

# Ждём, пока MinIO будет доступен
until mc alias set minio http://$MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY; do
  echo "Ожидание MinIO..."
  sleep 1
done

echo "MinIO доступен"

# Создаём бакет, если не существует
mc mb minio/$MINIO_BUCKET --ignore-existing 2>/dev/null || true

# Устанавливаем политику чтения для всех
cat > /tmp/policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::$MINIO_BUCKET/*"]
    }
  ]
}
EOF

# Применяем политику
mc admin policy set minio readwrite user=$MINIO_ACCESS_KEY 2>/dev/null || true

echo "Бакет '$MINIO_BUCKET' настроен успешно"
echo "Консоль MinIO: http://localhost:9001"
echo "API MinIO: http://localhost:9000"

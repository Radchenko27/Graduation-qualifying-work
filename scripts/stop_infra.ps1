# Script to stop PostgreSQL and MinIO containers

Write-Host "Stopping infrastructure containers..." -ForegroundColor Yellow

docker-compose stop db minio

Write-Host "Infrastructure stopped." -ForegroundColor Green

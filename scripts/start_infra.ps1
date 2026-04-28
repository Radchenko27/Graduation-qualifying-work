# Script to start PostgreSQL and MinIO containers (without FastAPI app)

Write-Host "Starting infrastructure containers..." -ForegroundColor Green

# Build and start only db and minio
docker-compose up -d db minio

# Wait for services to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check PostgreSQL
for ($i = 0; $i -lt 12; $i++) {
    $result = docker exec graduatingwork-db-1 pg_isready -U postgres 2>&1
    if ($result -like "*ready*" -or $result -like "*accepted*") {
        Write-Host "PostgreSQL is ready!" -ForegroundColor Green
        break
    }
    Write-Host "Waiting... ($($i+1)/12)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

# Check MinIO
Write-Host "Waiting for MinIO to be ready..." -ForegroundColor Yellow
for ($i = 0; $i -lt 12; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "MinIO is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Ignore errors, continue waiting
    }
    Write-Host "Waiting... ($($i+1)/12)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

# Apply migrations
Write-Host "Applying database migrations..." -ForegroundColor Green
alembic upgrade head

# Initialize database with test data
Write-Host "Initializing database with test data..." -ForegroundColor Green
python scripts/init_db.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Infrastructure is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host "MinIO:      localhost:9000" -ForegroundColor White
Write-Host "API Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "Frontend:   http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Now run: uvicorn app.main:app --reload" -ForegroundColor Yellow
Write-Host ""

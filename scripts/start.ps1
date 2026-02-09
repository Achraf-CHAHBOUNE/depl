Write-Host "Starting services..."

docker-compose down -v

docker-compose build

docker-compose up -d

./scripts/init_db.ps1
Write-Host "Restarting services..."

docker-compose down 

docker-compose build

docker-compose up -d
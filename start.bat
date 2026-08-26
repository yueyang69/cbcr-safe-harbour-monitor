@echo off
REM CbCR Safe Harbour - Quick Start Script for Windows

echo 🚀 CbCR Safe Harbour - Starting deployment...

REM Check if .env exists, if not copy from example
if not exist .env (
    echo 📝 Creating .env from .env.example...
    copy .env.example .env
    echo ⚠️  Please edit .env file to set your MINIMAX_API_KEY (optional^)
    echo    Without API key, the system will use mock AI responses.
)

REM Stop any running containers
echo 🛑 Stopping existing containers...
docker-compose down 2>nul

REM Build and start services
echo 🔨 Building Docker images...
docker-compose build --no-cache

echo 🚀 Starting services...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check service health
echo 🏥 Checking service health...
docker-compose ps

echo.
echo ✅ Deployment complete!
echo.
echo 📊 Access the application:
echo    Frontend: http://localhost:5173
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 📝 Default test users:
echo    - Subsidiary: X-User-Role: subsidiary
echo    - HQ: X-User-Role: hq
echo    - Admin: X-User-Role: admin
echo.
echo 🔍 View logs:
echo    docker-compose logs -f
echo.
echo 🛑 Stop services:
echo    docker-compose down
echo.
pause

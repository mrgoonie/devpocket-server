#!/bin/bash

# DevPocket Server Startup Script

set -e

echo "🚀 Starting DevPocket Server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose not found. Please install docker-compose."
    exit 1
fi

echo "🔧 Building Docker images..."
docker-compose build

echo "🗄️  Starting database services..."
docker-compose up -d mongo redis

echo "⏳ Waiting for databases to be ready..."
sleep 10

echo "🚀 Starting DevPocket API..."
docker-compose up -d devpocket-api

echo "🌐 Starting Nginx proxy..."
docker-compose up -d nginx

echo "✅ DevPocket Server started successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌍 Access Points:"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo "  • Main API: http://localhost:80"
echo ""
echo "📋 Useful Commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo "  • Restart API: docker-compose restart devpocket-api"
echo ""
echo "🎉 Happy coding with DevPocket!"
#!/bin/bash
set -e

APP_NAME=codemate-backend

echo "[+] Stopping old container..."
docker stop $APP_NAME || true
docker rm $APP_NAME || true
docker rmi $APP_NAME || true

echo "[+] Building image..."
docker build -t $APP_NAME -f docker/Dockerfile .

echo "[+] Running container..."
docker run -d --name $APP_NAME -p 8080:8080 $APP_NAME

echo "[+] Cleaning up Docker build cache..."
docker builder prune -f

echo "[✓] Deployed at $(date)"

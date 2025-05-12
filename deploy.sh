#!/bin/bash
set -e

echo "[+] Stopping old container..."
docker stop codemate-backend || true
docker rm codemate-backend || true
docker rmi codemate-backend || true

echo "[+] Building image..."
docker build -t codemate-backend -f docker/Dockerfile .

echo "[+] Running container..."
docker run -d --name codemate-backend -p 8080:8080 codemate-backend

echo "[✓] Deployed at $(date)"

#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

echo "Updating packages..."
apt-get update -y
apt-get install -y python3-venv python3-pip nginx certbot python3-certbot-nginx postgresql-client

echo "Setting up directory..."
mkdir -p /root/avatar
cd /root/avatar
tar -xzf /root/avatar_deploy.tar.gz

echo "Setting up Python environment..."
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
pip install -r bot/requirements.txt || true
pip install gunicorn httptools uvloop

echo "Updating .env..."
sed -i 's|MINI_APP_URL=.*|MINI_APP_URL=https://frontend-omega-seven-47.vercel.app|' backend/.env
sed -i 's|ENVIRONMENT=.*|ENVIRONMENT=production|' backend/.env
cp backend/.env bot/.env

echo "Running migrations..."
cd backend
alembic upgrade head
cd ..

echo "Configuring Nginx with nip.io..."
mv /root/nginx_avatar.conf /etc/nginx/sites-available/avatar
ln -sf /etc/nginx/sites-available/avatar /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "Obtaining SSL..."
certbot --nginx -d 103.74.92.72.nip.io --non-interactive --agree-tos -m admin@example.com || true

echo "Setting up Systemd Services..."
mv /root/avatar-backend.service /etc/systemd/system/
mv /root/avatar-bot.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable avatar-backend avatar-bot
systemctl restart avatar-backend avatar-bot

echo "Setup Complete! Backend running at https://103.74.92.72.nip.io"

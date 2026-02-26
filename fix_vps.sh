#!/bin/bash
set -e

# Disable and stop nginx
systemctl stop nginx || true
systemctl disable nginx || true

# Update the service file
mv /root/avatar-backend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable avatar-backend
systemctl restart avatar-backend

# Restart bot as well just in case
systemctl enable avatar-bot || true
systemctl restart avatar-bot || true

# Update Traefik config
mv /root/avatar.yml /etc/dokploy/traefik/dynamic/avatar.yml

echo "Done fixing backend!"

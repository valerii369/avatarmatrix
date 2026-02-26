#!/bin/bash
set -e

# Copy updated backend files
cp /root/avatar/backend/app/routers/sync.py /root/avatar/backup_sync.py 2>/dev/null || true

# Restart backend service to pick up changes
systemctl restart avatar-backend
sleep 2
systemctl status avatar-backend --no-pager | tail -5
echo "Backend restarted."

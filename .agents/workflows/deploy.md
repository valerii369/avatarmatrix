---
description: How to deploy the AVATAR application (Frontend & Backend)
---

This workflow describes the standardized deployment process for both the frontend and the backend.

### 1. Deploy Frontend to Vercel
Run this command from the project root. It handles directory switching and production deployment.
// turbo
```bash
npm run deploy:frontend
```

### 2. Deploy Backend and Bot to VPS (Timeweb)
Run this command from the project root. It uses the unified expect script to sync files and restart services.
// turbo
```bash
expect deploy_vps.exp
```

### Verification
After deployment, confirm the system is operational:
1. **Health Check**: `curl https://avatar.aiguro.pro/health` (should return version `1.0.1+`)
2. **Bot Check**: Send a message to the Telegram bot to ensure it's responsive.

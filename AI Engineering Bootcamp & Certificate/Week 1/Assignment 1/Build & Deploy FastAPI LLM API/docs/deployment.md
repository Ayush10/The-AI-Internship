# Deployment Guide — VPS (Monorepo)

## Overview
The repo root is `The AI Internship/` (monorepo). This assignment lives at:
```
AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/
```
Deployed at: `https://theaiinternship.ayushojha.com/aiengineeringbootcamp/week1/assignment1/`

---

## 1. DNS Setup

Add an **A record** in your domain registrar (where `ayushojha.com` is managed):

| Field | Value |
|-------|-------|
| Type  | A |
| Host  | theaiinternship |
| Value | 72.62.82.57 |
| TTL   | 300 (or Auto) |

Wait a few minutes for DNS propagation. Verify with:
```bash
dig theaiinternship.ayushojha.com +short
# Should return: 72.62.82.57
```

---

## 2. VPS Setup (SSH to 72.62.82.57)

### Clone the monorepo
```bash
ssh ayush@72.62.82.57

mkdir -p ~/apps
cd ~/apps
git clone <your-github-repo-url> the-ai-internship
```

### Set up the assignment's venv
```bash
cd ~/apps/the-ai-internship/AI\ Engineering\ Bootcamp\ \&\ Certificate/Week\ 1/Assignment\ 1/Build\ \&\ Deploy\ FastAPI\ LLM\ API/

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Create .env file
```bash
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
DEFAULT_PROVIDER=openai
EOF
```

### Test the app
```bash
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8001
# Visit http://72.62.82.57:8001/health to verify
```

---

## 3. Systemd Service

Create the service file:
```bash
sudo nano /etc/systemd/system/week1-assignment1.service
```

Paste:
```ini
[Unit]
Description=AI Internship - Week 1 Assignment 1 API
After=network.target

[Service]
User=ayush
WorkingDirectory=/home/ayush/apps/the-ai-internship/AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API
ExecStart=/home/ayush/apps/the-ai-internship/AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5
EnvironmentFile=/home/ayush/apps/the-ai-internship/AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable week1-assignment1
sudo systemctl start week1-assignment1
sudo systemctl status week1-assignment1
```

---

## 4. Nginx Configuration

Create the Nginx config:
```bash
sudo nano /etc/nginx/sites-available/theaiinternship.ayushojha.com
```

Paste:
```nginx
server {
    listen 80;
    server_name theaiinternship.ayushojha.com;

    location /aiengineeringbootcamp/week1/assignment1/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and test:
```bash
sudo ln -s /etc/nginx/sites-available/theaiinternship.ayushojha.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. SSL with Let's Encrypt

```bash
sudo certbot --nginx -d theaiinternship.ayushojha.com
```

Certbot will auto-update the Nginx config to add SSL. Verify:
```bash
curl https://theaiinternship.ayushojha.com/aiengineeringbootcamp/week1/assignment1/health
```

---

## 6. Updating (after git push)

```bash
ssh ayush@72.62.82.57
cd ~/apps/the-ai-internship
git pull
sudo systemctl restart week1-assignment1
```

---

## Monorepo Notes

Future assignments/projects can be added under the same repo and deployed as separate services:
- Each gets its own systemd service (different port: 8002, 8003, etc.)
- Each gets its own Nginx location block under the same subdomain
- Example: `/aiengineeringbootcamp/week2/assignment1/` → port 8002

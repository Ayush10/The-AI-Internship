# Deployment Guide — Coolify (Docker)

## Overview

The repo root is `The-AI-Internship/` (monorepo). This assignment lives at:
```
AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/
```

**Live URL:** https://theaiinternship.ayushojha.com

---

## Architecture

- **Platform:** VPS at `72.62.82.57`, managed by [Coolify](https://coolify.ayushojha.com) (self-hosted PaaS)
- **Container:** Docker, built from `Dockerfile` at repo root
- **Reverse Proxy:** Traefik (managed by Coolify), auto-SSL via Let's Encrypt
- **Auto-Deploy:** GitHub webhook triggers rebuild on every push to `main`

---

## Coolify Configuration

| Field | Value |
|-------|-------|
| App UUID | `hkw4co8cs8000scckg404s4w` |
| Project UUID | `dk8kkwc8k0c8osowk4s4ccsw` |
| Server | Personal Portfolio (`pok4wwo8wo8wgo8cc0g80s4c`) |
| Domain | `https://theaiinternship.ayushojha.com` |
| Build Pack | Dockerfile |
| Git Repo | `git@github.com:Ayush10/The-AI-Internship.git` |
| Branch | `main` |
| Exposed Port | `8000` |
| Deploy Key UUID | `c48g8ccgw804sowkk4wkos40` |

---

## Environment Variables

Set these in Coolify UI or API:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `DEFAULT_PROVIDER` | Default LLM provider (`gemini`, `openai`, or `anthropic`) |

---

## Dockerfile

The `Dockerfile` at the repo root handles the nested directory structure:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /repo
RUN cp -r "/repo/AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/"* . && \
    rm -rf /repo
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Auto-Deploy Webhook

| Field | Value |
|-------|-------|
| GitHub Hook ID | `596261411` |
| Webhook Secret | `5bc28cfb9ad39472b88260b5bfa45f78` |
| Webhook URL | `https://coolify.ayushojha.com/webhooks/source/github/events/manual?token=5bc28cfb9ad39472b88260b5bfa45f78&uuid=hkw4co8cs8000scckg404s4w` |

Every push to `main` triggers an automatic rebuild and deploy.

---

## Manual Deploy

Via Coolify API:
```bash
curl -X POST "https://coolify.ayushojha.com/api/v1/deploy?uuid=hkw4co8cs8000scckg404s4w" \
  -H "Authorization: Bearer <COOLIFY_API_TOKEN>"
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Web UI |
| GET | `/docs` | FastAPI auto-generated docs |
| POST | `/summarize` | Text summarization |
| POST | `/analyze-sentiment` | Sentiment analysis |
| POST | `/chat` | Chat interface |
| POST | `/enhance-prompt` | Prompt enhancement |

---

## Monorepo Notes

Future assignments/projects can share the same Coolify app by updating the `Dockerfile` to serve multiple services, or can be deployed as separate Coolify apps from the same repo.

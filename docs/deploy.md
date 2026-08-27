# Deployment

This document explains simple containerized deployment for the AI Project Reviewer.

Build locally:

```bash
docker build -t ai-project-reviewer:latest .
```

Run with Docker:

```bash
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="$GEMINI_MODEL" \
  ai-project-reviewer:latest
```

For local iterative development, use docker-compose:

```bash
docker compose up --build
```

Notes:
- `backend/models` contains the trained model artifact; ensure it is persisted between runs if you retrain in-container.
- For production, run behind a reverse proxy and configure HTTPS and secrets via your orchestrator.

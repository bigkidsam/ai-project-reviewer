# AI Project Reviewer

AI Project Reviewer is a FastAPI backend for reviewing GitHub repositories. It
clones a repository, runs static analysis on Python files, calculates basic
quality metrics, and generates an AI-assisted review summary with Gemini.

## Setup

```bash
python -m pip install -r requirements.txt
```

Add your Gemini API key in `.env`:

```bash
GEMINI_API_KEY=your-valid-gemini-api-key
```

## Run Backend

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

Open the static dashboard:

```text
frontend/index.html
```

## Review Endpoint

```http
POST /review
GET /review/{review_id}
GET /health
```

Example body:

```json
{
  "repo_url": "https://github.com/psf/requests",
  "max_files": 10
}
```

The response includes:

- persisted `review_id`
- repository metadata
- analyzed file paths
- structured findings with severity
- metrics such as issue density and quality score
- raw analyzer output
- an AI review summary

You can change the local pipeline target with environment variables:

```bash
python backend/app/test_pipeline.py --repo-url https://github.com/psf/requests --max-files 10
```

# Architecture

AI Project Reviewer has a FastAPI backend that accepts a GitHub repository URL,
clones the repository into `backend/temp_repos`, runs static analysis on Python
files, calculates review metrics, and asks Gemini for a summarized engineering
review.

## Backend Flow

1. `app/api/review.py` receives a `/review` request.
2. `github_fetcher.py` clones or refreshes the target repository, skips noisy
   generated folders, and collects repository metadata.
3. `static_analysis.py` runs pylint against each selected Python file and parses
   issues into structured findings.
4. `metrics.py` calculates file counts, severity counts, category counts, issue
   density, and a quality score.
5. `ai_reviewer.py` sends metrics, metadata, structured findings, and raw issue
   text to Gemini using `GEMINI_API_KEY`.

## Future Areas

- `models/` is reserved for database models.
- `schemas/` contains request and response contracts.
- `utils/` is reserved for shared helpers.
- `frontend/` is reserved for a React client.

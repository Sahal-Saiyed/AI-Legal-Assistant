# AI Legal Assistant

## API smoke tests

Start the backend from the project root:

```powershell
uvicorn backend.app.main:app --reload
```

Check process health:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

Ask legal questions:

```powershell
$questions = @(
    "How do I file an FIR?",
    "What are my consumer rights if an online seller refuses a refund?",
    "How do I become an astronaut?"
)

foreach ($question in $questions) {
    $body = @{ question = $question } | ConvertTo-Json
    Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:8000/api/v1/ask" `
        -ContentType "application/json" `
        -Body $body
}
```

Interactive OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Authentication and MongoDB Atlas

Recommended Atlas names:

- Project: `JuriGPT`
- Cluster: `jurigpt-cluster`
- Database: `jurigpt`
- User collection: `users` (created automatically)
- Database user: `jurigpt_app`

Copy `.env.example` to `.env`, replace all placeholder secrets, add the Atlas
connection string, and allow the backend machine's IP address in Atlas Network
Access. Install the updated requirements before starting FastAPI:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Place the application logo at `frontend/src/assets/logo.png`. The UI uses a
legal-scale fallback icon when this file is absent.

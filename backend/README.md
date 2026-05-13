# Backend

FastAPI backend for the secure file encryption and sharing platform.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Swagger

```text
http://localhost:8000/docs
```

## Important

The current implementation is a scaffold with draft flows. The next step is to connect the services to MySQL transactions and replace demo responses with actual database-backed logic.

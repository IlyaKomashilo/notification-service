from fastapi import FastAPI

app = FastAPI(title="Notification Service")

@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "service": "Notification Service",
    }

# запуск ./.venv/bin/uvicorn src.main:app --reload --host 127.0.0.1 --port 9000
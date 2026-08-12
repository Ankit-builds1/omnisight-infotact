from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight-backend")

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "OmniSight backend is running"}

@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        logger.warning("Received invalid JSON payload")
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid JSON"})

    logger.info(f"Webhook received: {data}")
    return {"status": "received", "data": data}
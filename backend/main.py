from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "OmniSight backend is running"}

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    return {"status": "received", "data": data}
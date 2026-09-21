from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
import redis 
import json
import os

app = FastAPI()
REDIS_HOST = os.getenv("REDIS_HOST", "redis-queue")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

QUEUE_NAME = "github_tasks"

@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.json()

    task_data = {
        "event": request.headers.get("X-Github-Event"),
        "payload": payload
    }

    r.rpush(QUEUE_NAME, json.dumps(task_data))

    return {"status": "queued", "message": "Event buffered sucessfully"}


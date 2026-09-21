from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
import redis 
import json

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, db=0)

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


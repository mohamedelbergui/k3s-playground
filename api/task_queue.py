import redis
import json
from config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

def push_task(image_id, filename, filter_name, width, height):
    message = json.dumps({
        "image_id": image_id,
        "filename": filename,
        "filter": filter_name,
        "width": width,
        "height": height
    })
    r.lpush("image_tasks", message)
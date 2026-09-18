import redis
import json
from PIL import Image, ImageFilter
import os
from dotenv import load_dotenv
import psycopg2


POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

conn = psycopg2.connect(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
)

ORIGINALS_FOLDER = "/worker/uploads/originals"
PROCESSED_FOLDER = "/worker/uploads/processed"

def resize_image(image, width, height):
    return image.resize((width, height))

FILTERS = {
    "none": None,
    "blur": ImageFilter.BLUR,
    "sharpen": ImageFilter.SHARPEN,
    "edges": ImageFilter.FIND_EDGES,
    "smooth": ImageFilter.SMOOTH,
    "smooth_more": ImageFilter.SMOOTH_MORE,
    "contour": ImageFilter.CONTOUR,
    "emboss": ImageFilter.EMBOSS,
    "detail": ImageFilter.DETAIL,
    "edge_enhance": ImageFilter.EDGE_ENHANCE,
    "edge_enhance_more": ImageFilter.EDGE_ENHANCE_MORE,
    "gaussian_blur": ImageFilter.GaussianBlur(radius=5),
    "unsharp_mask": ImageFilter.UnsharpMask(),
    "min_filter": ImageFilter.MinFilter(size=3),
    "max_filter": ImageFilter.MaxFilter(size=3),
    "mode_filter": ImageFilter.ModeFilter(size=3),
}

def apply_filter(image, filter_name):
    return image.filter(FILTERS[filter_name])

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

with conn.cursor() as cur:
    while True:
        raw_task = r.rpop("image_tasks")
        if raw_task:
            task = None
            try:
                task = json.loads(raw_task)

                image = Image.open(ORIGINALS_FOLDER + "/" + task['filename'])
                resized = resize_image(
                    image=image,
                    width=int(task['width']),
                    height=int(task['height']),
                )
                filtered = apply_filter(image=resized, filter_name=task['filter']) if task['filter'] else resized
                filtered.save(PROCESSED_FOLDER + "/" + task['filename'])

                cur.execute("UPDATE task SET status=%s WHERE id=%s", ("done", task['image_id']))
                conn.commit()

            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Failed to process task {raw_task}: {e}", flush=True)

                if task and task.get('image_id') is not None:
                    try:
                        cur.execute("UPDATE task SET status=%s WHERE id=%s", ("failed", task['image_id']))
                        conn.commit()
                    except Exception as db_err:
                        conn.rollback()
                        print(f"[ERROR] Failed to update status to 'failed' for task {raw_task}: {db_err}", flush=True)
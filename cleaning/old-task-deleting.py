from dotenv import load_dotenv
import psycopg2
import os
import sys

load_dotenv()
CLEANING_AFTER = int(os.getenv("CLEANING_AFTER"))

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

try:
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
except Exception as e:
    print(str(e), flush=True)
    sys.exit(1)

ORIGINALS_FOLDER = "/app/uploads/originals"
PROCESSED_FOLDER = "/app/uploads/processed"

with conn.cursor() as cur:
    cur.execute(
        """
        SELECT id, file_name FROM task
        WHERE 
        deleted
        AND deleted_at IS NOT NULL
        AND deleted_at <= NOW() - (%s * INTERVAL '1 day')
        """
        , (CLEANING_AFTER,))
    to_delete = cur.fetchall()
    for task in to_delete:
        try:
            task_id, filename = task
            for folder in (ORIGINALS_FOLDER, PROCESSED_FOLDER):
                path = os.path.join(folder, filename)
                if os.path.exists(path):
                    os.remove(path)
            cur.execute(
                """
                DELETE FROM task
                WHERE
                id=%s
                """
                , (task_id,)
                )
            conn.commit()
        except Exception as e:
            print(str(e), flush=True)

conn.close()  
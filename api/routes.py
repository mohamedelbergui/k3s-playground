from task_queue import push_task
from flask import Blueprint, request, jsonify, render_template
import uuid
from db import create_task, get_task, soft_delete_image, get_gallery_images, get_trash_images, restore_image
import os
from datetime import datetime
from flask import send_from_directory
import psycopg2
import redis


bp=Blueprint("routes", __name__)
UPLOAD_FOLDER = "/api/uploads/originals"
PROCESSED_FOLDER = "/api/uploads/processed"
os.makedirs(UPLOAD_FOLDER,exist_ok=True)

@bp.route("/upload", methods=["POST","GET"])
def upload():
    if request.method=='POST':
        try:
            image_id = str(uuid.uuid4())
            image=request.files["image"]
            file_name = str(datetime.now())+"__"+image.filename
            filter_name = request.form.get("filter", "none")
            width = int(request.form.get("width", 300))
            height = int(request.form.get("height", 300))

            image.save(os.path.join(UPLOAD_FOLDER, file_name))

            create_task(image_id, file_name,filter_name,width,height)
            push_task(image_id, file_name,filter_name,width,height)
            return jsonify({"image_id": image_id}), 202
        except Exception as e:
            return jsonify({"Error": str(e)})
    return render_template("upload.html")

@bp.route("/status/<image_id>", methods=["GET"])
def status(image_id):
    task = get_task(image_id)
    if not task:
        return jsonify({"error": "not found"}), 404
    return jsonify({"status": task.status})

@bp.route("/images/<string:task_id>", methods=["DELETE"])
def delete_image(task_id):
    result = soft_delete_image(task_id)

    if not result["success"]:
        if result["error"] == "not_found":
            return jsonify({"message": "Image not found"}), 404
        if result["error"] == "already_deleted":
            return jsonify({"message": "Image already deleted"}), 409

    return jsonify({
        "message": "Image moved to trash",
        "task_id": result["task_id"],
        "deleted_at": result["deleted_at"]
    }), 200

@bp.route("/files/originals/<string:file_name>", methods=["GET"])
def serve_original(file_name):
    return send_from_directory(UPLOAD_FOLDER, file_name)


@bp.route("/files/processed/<string:file_name>", methods=["GET"])
def serve_processed(file_name):
    return send_from_directory(PROCESSED_FOLDER, file_name)

@bp.route("/", methods=["GET"])
@bp.route("/gallery", methods=["GET"])
def gallery():
    images = get_gallery_images()
    return render_template("gallery.html", images=images)

@bp.route("/trash", methods=["GET"])
def trash():
    images = get_trash_images()
    return render_template("trash.html", images=images)


@bp.route("/images/<string:task_id>/restore", methods=["POST"])
def restore_image_route(task_id):
    result = restore_image(task_id)

    if not result["success"]:
        if result["error"] == "not_found":
            return jsonify({"message": "Image not found"}), 404
        if result["error"] == "not_deleted":
            return jsonify({"message": "Image is not deleted"}), 409

    return jsonify({"message": "Image restored", "task_id": result["task_id"]}), 200


# Health checks

@bp.route("/health/live")
def live():
    return {"status": "alive"}, 200

@bp.route("/health/ready")
def ready():
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=1
        )
        conn.close()
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.close()
    except Exception:
        return {"status":"not ready"}, 503

    return {"status": "ready"}, 200
from task_queue import push_task
from flask import Blueprint, request, jsonify, render_template
import uuid
from db import create_task, get_task
import os
from datetime import datetime

bp=Blueprint("routes", __name__)
UPLOAD_FOLDER = "/api/uploads/originals"
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

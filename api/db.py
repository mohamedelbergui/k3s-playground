from models import db, Task
from datetime import datetime, timezone

def create_task(image_id, file_name,filter_name, width, height):
    task = Task(
        id=image_id,
        file_name=file_name,
        filter_name=filter_name,
        width=width,
        height=height
    )
    db.session.add(task)
    db.session.commit()

def get_task(image_id):
    return Task.query.get(image_id)



def soft_delete_image(id: str) -> dict:
    """
    Marks an image as deleted (soft delete) without touching the physical file.
    Returns a dict describing the outcome so the route layer can build the HTTP response.
    """
    image = Task.query.filter_by(id=id).first()

    if image is None:
        return {"success": False, "error": "not_found"}

    if image.deleted:
        return {"success": False, "error": "already_deleted"}

    image.deleted = True
    image.deleted_at = datetime.now(timezone.utc)

    db.session.commit()

    return {"success": True, "id": image.uid, "deleted_at": image.deleted_at.isoformat()}

def get_gallery_images():
    """
    Returns all non-deleted tasks, most recent first, for display in the gallery.
    """
    tasks = Task.query.filter_by(deleted=False).order_by(Task.created_at.desc()).all()

    return [
        {
            "id": task.id,
            "file_name": task.file_name,
            "filter_name": task.filter_name,
            "status": task.status,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for task in tasks
    ]
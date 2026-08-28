from models import db, Task

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
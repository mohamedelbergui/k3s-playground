from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Task(db.Model):
    __table_name__ = "tasks"
    id = db.Column(db.String, primary_key=True)
    file_name = db.Column(db.String, nullable=False)
    filter_name = db.Column(db.String, nullable=True)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, default="pending")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    

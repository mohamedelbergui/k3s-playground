from flask import Flask
from routes import bp
from models import db
from config import Config

def create_app(config=Config):
    app=Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    app.register_blueprint(bp)
    return app
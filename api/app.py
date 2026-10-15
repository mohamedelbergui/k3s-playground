from flask import Flask
from routes import bp
from models import db
from config import Config

def create_app():
    app=Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    app.register_blueprint(bp)
    return app
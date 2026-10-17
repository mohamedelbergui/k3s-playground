from run import app
from models import db

import models  

with app.app_context():
    db.create_all()
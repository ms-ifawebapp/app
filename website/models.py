from datetime import datetime
from website import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firstname = db.Column(db.String(50))
    lastname = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    passwordhash = db.Column(db.String(255))
    appadmin = db.Column(db.Boolean)
    creationdate = db.Column(db.DateTime, default=datetime.now)
    updatedate = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        self.passwordhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passwordhash, password)

class surveymodes(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    initial = db.Column(db.Boolean)

class surveys(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer)
    mode_id = db.Column(db.Integer, db.ForeignKey('surveymodes.id'))
    creationdate = db.Column(db.DateTime, default=datetime.now)
    updatedate = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class comments(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete="CASCADE"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    comment = db.Column(db.Text)
    edited = db.Column(db.Boolean)
    creationdate = db.Column(db.DateTime, default=datetime.now)
    updatedate = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class roles(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    security = db.Column(db.Boolean)
    data = db.Column(db.Boolean)

class roleassignments(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete="CASCADE"), primary_key=True)

class surveyoptions(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete="CASCADE"), primary_key=True)
    value = db.Column(db.DateTime)
    info = db.Column(db.String(100))

class surveyanswers(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete="CASCADE"))
    option_id = db.Column(db.Integer, db.ForeignKey('surveyoptions.id', ondelete="CASCADE"))
    user_id = db.Column(db.Integer)
    displayname = db.Column(db.String(50))
    answer = db.Column(db.Boolean)
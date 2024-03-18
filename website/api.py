from flask import Blueprint, request
from website import db
from .models import users, surveys

api = Blueprint('api', __name__)

#Login-Page for existing users
@api.route('/api/getsurveys', methods=['GET'])
def login():   
    return surveys.query.all()
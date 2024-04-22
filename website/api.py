from flask import Blueprint, request, jsonify
from website import db
from .models import surveys, surveyoptions

api = Blueprint('api', __name__)

#API-Request for surveys
@api.route('/api/getsurveys', methods=['GET'])
def getsurveys():  
    current_surveys = surveys.query.all() 

    # Serialize each row into JSON
    json_data = []
    for row in current_surveys:
        json_row = {
            'id': row.id,
            'title': row.title,
            'description': row.description,
            'user_id': row.user_id,
            'mode_id': row.mode_id,
            'creationdate': row.creationdate,
            'updatedate': row.updatedate
        }
        json_data.append(json_row)

    return jsonify(json_data)

#API-Request for options
@api.route('/api/getoptions/<survey_id>', methods=['GET'])
def getoptions(survey_id):  
    current_options = surveyoptions.query.filter_by(survey_id=survey_id).all() 

    # Serialize each row into JSON
    json_data = []
    for row in current_options:
        json_row = {
            'id': row.id,
            'survey_id': row.survey_id,
            'value': row.value,
            'info': row.info
        }
        json_data.append(json_row)

    return jsonify(json_data)
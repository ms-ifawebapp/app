from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email
from flask_login import login_user, logout_user, current_user
from website import db, login
from .models import users, surveys, surveyanswers, surveyoptions, comments, roleassignments, roles

views = Blueprint('views', __name__)

class UserForm(FlaskForm):
    submit = SubmitField('Speichern')    

    @classmethod
    def add_options(cls, option_id, id):
        setattr(cls, f'option{id}-{option_id}',BooleanField('answer'))
    
    @classmethod
    def add_displayname(cls, displayname, id):
        setattr(cls, f'displayname{id}',StringField('displayname', default=displayname))

    @classmethod
    def add_user_id(cls, user_id, id):
        setattr(cls, f'user_id{id}',IntegerField('user_id', default=user_id))

@views.route('/')
def index():
    return render_template("index.html")

@views.route('/survey/<int:survey_id>', methods=['GET', 'POST'])
def survey(survey_id):   
    survey = surveys.query.get(survey_id)
    existing_options = surveyoptions.query.filter_by(survey_id=survey_id).all()
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    
    UserRow = UserForm()
    row_count = 0
    value_entries = len(existing_options)+2

    if current_user.is_authenticated:
        user = users.query.filter_by(id=current_user.id).first()
        current_id = current_user.id
        current_displayname = user.firstname + ' ' + user.lastname
    else:
        current_id ='none'
        current_displayname = ''

    for user in existing_user_answers:
        answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        if len(answers) != len(existing_options):
            for possible_option in existing_options:
                if not surveyanswers.query.filter_by(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname).first():
                    new_option = surveyanswers(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname,answer=False)
                    db.session.add(new_option)
                    db.session.commit()

    user_already_answered = False
    
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    for user in existing_user_answers:
        UserRow.add_displayname(user.displayname,row_count)
        UserRow.add_user_id(user.user_id, row_count)
        if user.user_id == current_id and current_id != 'none':
            user_already_answered == True
        else:
            getattr(UserRow, f'displayname{row_count}').render_kw = {'readonly': True}
            getattr(UserRow, f'user_id{row_count}').render_kw = {'readonly': True}

            answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
            for answer in answers:
                UserRow.add_options(answer.option_id,row_count)
                if user.user_id == current_id and current_id != 'none':
                    getattr(UserRow, f'user_id{answer.option_id,row_count}').render_kw = {'disabled': 'disabled'}
        row_count += 1

    if not user_already_answered:
        UserRow.add_displayname(current_displayname,row_count)
        UserRow.add_user_id(current_id,row_count)

        answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        for answer in answers:
            UserRow.add_options(answer.option_id,row_count)

    if request.method == 'POST':
        print('post')
        

    return render_template('survey.html', survey=survey, form=UserRow, existing_options=existing_options, value_entries=value_entries, row_count=row_count)
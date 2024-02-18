from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email
from flask_login import login_user, logout_user, current_user
from website import db, login
from .models import users, surveys, surveyanswers, surveyoptions, comments, roleassignments, roles

views = Blueprint('views', __name__)

class UserForm(FlaskForm):
    displayname = StringField('displayname')
    user_id = IntegerField('user_id')
    editable = BooleanField('editable')    

    @classmethod
    def add_attribute(cls, existing_options):
        for answer in existing_options:
            setattr(cls, f'option{answer.id}',BooleanField('answer'))

@views.route('/')
def index():
    return render_template("index.html")

@views.route('/survey/<int:survey_id>', methods=['GET', 'POST'])
def survey(survey_id):   
    survey = surveys.query.get(survey_id)
    existing_options = surveyoptions.query.filter_by(survey_id=survey_id).all()
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()

    UserForm.add_attribute(existing_options)
    
    if current_user.is_authenticated:
        user = users.query.filter_by(id=current_user.id).first()
        current_id = current_user.id
        current_displayname = user.firstname + ' ' + user.lastname
    else:
        current_id ='none'

    for user in existing_user_answers:
        answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        available_options = surveyoptions.query.filter_by(survey_id=survey_id).all()
        if len(answers) != len(available_options):
            for possible_option in available_options:
                if not surveyanswers.query.filter_by(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname).first():
                    new_option = surveyanswers(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname,answer=False)
                    db.session.add(new_option)
                    db.session.commit()

    forms = []
    user_already_answered = False
    
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    for user in existing_user_answers:
        existing_UserForm = UserForm()
        existing_UserForm.displayname.data = user.displayname
        existing_UserForm.user_id.data = user.user_id
        if user.user_id == current_id and current_id != 'none':
            user_already_answered == True
            existing_UserForm.editable.data = True
        else:
            existing_UserForm.editable.data = False

        if request.method=='GET':
            answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
            for answer in answers:
                answer_field = getattr(existing_UserForm, f'option{answer.option_id}')
                answer_field.data = answer.answer

        forms.append(existing_UserForm)

    if not user_already_answered:
        new_UserForm = UserForm()
        new_UserForm.editable.data = True
        if request.method=='GET':
            if current_user.is_authenticated:
                new_UserForm.displayname.data = current_displayname
                new_UserForm.user_id.data = current_id
            for name, field in new_UserForm._fields.items():
                if name.startswith('option'):
                    field.data = False
        forms.append(new_UserForm)

    for form in forms:
        print(form._fields['displayname'].data)

    if request.method == 'POST':
        print('post')
        for form in forms:
            answer_displayname = form._fields['displayname'].data
            answer_user_id = form._fields['user_id'].data

            print(answer_displayname)

            if form._fields['editable'].data:
                if answer_displayname.strip() == '':
                    flash('Huch, da fehlt ein Name', 'error')
                    pass
                else:
                    existing_usernames = surveyanswers.query.filter_by(survey_id=survey_id, user_id=answer_user_id, displayname=answer_displayname).all()
                    if not user_already_answered and len(existing_usernames) > 0:
                        flash('Dieser Name wurde bereits verwendet.', 'error')
                        pass
                    else:
                        for name, field in form._fields.items():
                            if name.startswith('option'):
                                option_id = name.replace('option', '')
                                existing_answer = surveyanswers.query.filter_by(survey_id=survey_id, option_id=option_id, user_id=answer_user_id, displayname=answer_displayname).first()
                                if existing_answer:
                                    existing_answer.answer = field.data
                                    db.session.commit()
                                else:
                                    new_answer = surveyanswers(survey_id=survey_id, option_id=option_id, user_id=answer_user_id, displayname=answer_displayname,answer=field.data)
                                    db.session.add(new_answer)
                                    db.session.commit()


                                if field.data:
                                    print(name + ' is true')
                                else:
                                    print(name + ' is false')
        return redirect(url_for('views.survey', survey_id=survey_id))

    return render_template('survey.html', survey=survey, forms=forms, existing_options=existing_options)
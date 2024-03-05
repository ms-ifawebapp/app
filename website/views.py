from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField, DateTimeField, SelectField
from wtforms.validators import DataRequired, Email
from flask_login import current_user
from website import db
from .models import users, surveys, surveyanswers, surveyoptions, comments, roles, roleassignments, surveymodes
from datetime import datetime
from .functions import verifyPermission, verifyMode

views = Blueprint('views', __name__)

#Form for the survey-page to list all answers
class UserForm(FlaskForm):
    submitbtn = SubmitField('Antworten')
    updatebtn = SubmitField('Aktualisieren')
    dynamic_fields = []    

    @classmethod
    def add_options(cls,option_id,row_count,value):
        setattr(cls,f'option_{row_count}_{option_id}',BooleanField('answer', default=value))
        cls.dynamic_fields.append(f'option_{row_count}_{option_id}')
    
    @classmethod
    def add_displayname(cls,displayname,row_count):
        setattr(cls,f'displayname_{row_count}_',StringField('displayname', default=displayname))
        cls.dynamic_fields.append(f'displayname_{row_count}_')

    @classmethod
    def add_user_id(cls,user_id,row_count):
        setattr(cls,f'user_id_{row_count}_',IntegerField('user_id', default=user_id))
        cls.dynamic_fields.append(f'user_id_{row_count}_')

    @classmethod
    def add_delete(cls,row_count,user_id,displayname):
        setattr(cls,f'delete_{row_count}_{displayname}_{user_id}',SubmitField('Löschen'))
        cls.dynamic_fields.append(f'delete_{row_count}_{displayname}_{user_id}')

    @classmethod
    def remove_dynamic_fields(cls):
        for field in cls.dynamic_fields:
            delattr(cls, field)
        cls.dynamic_fields = []

#Form to create a new survey
class NewSurveyForm(FlaskForm):
    title = StringField('Titel', validators=[DataRequired()])
    description = StringField('Beschreibung')
    submit = SubmitField('Erstellen') 

#Form to add an option for a survey
class NewOptionForm(FlaskForm):
    datetime = DateTimeField('Zeit (yyy-MM-dd hh:mm:ss)', validators=[DataRequired()])
    info = StringField('Zusatzinfo')
    submit = SubmitField('Erstellen')

#Form to create a new comment on a survey-page
class CommentForm(FlaskForm):
    Comment = StringField('Kommentar',validators=[DataRequired()])
    submitComment = SubmitField('Speichern')

#Form to change permissions of a survey
class PermissionForm(FlaskForm):
    mode = SelectField('Modus')
    modebtn = SubmitField('Aktualisieren')
    newemail = StringField('E-Mail', validators=[Email()])
    newpermission = SelectField('Berechtigung')
    submitbtn = SubmitField('Hinzufügen')

    def __init__(self):
        # Populate choices dynamically during form initialization
        self.newpermission.choices = [(str(role.id), role.name) for role in roles.query.all()]
        self.mode.choices = [(str(mode.id), mode.name) for mode in surveymodes.query.all()]

    @classmethod
    def add_permission(self,user_id,row_count,role_id):
        setattr(self, f'email_{row_count}_{user_id}',StringField('E-Mail', default=(users.query.get(user_id).email)))
        setattr(self, f'permission_{row_count}_{user_id}',SelectField('Berechtigung', choices=[(str(role.id), role.name) for role in roles.query.all()], default=role_id))
        setattr(self, f'updatebtn_{row_count}_{user_id}',SubmitField('Aktualisieren'))
        setattr(self, f'deletebtn_{row_count}_{user_id}',SubmitField('Löschen'))
        

#Initial page which is shown when connecting to the website
@views.route('/')
def index():
    user_surveys = ''
    if current_user.is_authenticated:
        user_surveys = surveys.query.filter_by(user_id=current_user.id)

    return render_template("index.html", surveys=user_surveys, current_user=current_user)

#Main page to show a survey and its related answers, comments
@views.route('/survey/<int:survey_id>', methods=['GET', 'POST'])
def survey(survey_id):   

    #Check if called survey exists and cancle if not existing
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('Diese Umfrage existiert nicht', 'error')
        return redirect(url_for('views.index'))
    
    if not verifyMode(survey_id):
        flash('Du hast leider keine Berechtigung', 'error')
        return redirect(url_for('views.index'))

    #get the existing options and answers
    existing_options = surveyoptions.query.filter_by(survey_id=survey_id).all()
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    
    #Initialize Form for ansers. Answers will be added below
    UserRows = UserForm()
    print(UserRows.dynamic_fields)
    UserRows.remove_dynamic_fields()
    print(dir(UserRows))
    row_count = 0
    value_entries = len(existing_options)+2

    #set variables related to the user
    if current_user.is_authenticated:
        user = users.query.get(current_user.id)
        current_id = current_user.id
        current_displayname = user.firstname + ' ' + user.lastname
    else:
        current_id ='none'
        current_displayname = ''

    #check the permission-level on the page for the current user
    if verifyPermission(survey_id,current_id,'security'):
        is_contributor = True
        is_admin = True
    elif verifyPermission(survey_id,current_id,'data'):
        is_contributor = True
        is_admin = False
    else:
        is_contributor = False
        is_admin = False

    #check if options got added since the last call of the page.
    #if yes, the new option will be added as false to prevent missing values
    for user in existing_user_answers:
        answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        if len(answers) != len(existing_options):
            for possible_option in existing_options:
                if not surveyanswers.query.filter_by(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname).first():
                    new_option = surveyanswers(survey_id=survey_id, option_id=possible_option.id, user_id=user.user_id,displayname=user.displayname,answer=False)
                    db.session.add(new_option)
                    db.session.commit()

    #set boolean to check after the loop if the current user already answered
    user_already_answered = False
    
    #add all the existing answers to the before created Form and set the permissions by modifing the read-only property
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    for user in existing_user_answers:
        UserRows.add_displayname(user.displayname,row_count)
        UserRows.add_user_id(user.user_id, row_count)
        if user.user_id == current_id:
            user_already_answered = True
        getattr(UserRows, f'displayname_{row_count}_').render_kw = {'readonly': True}
        getattr(UserRows, f'user_id_{row_count}_').render_kw = {'readonly': True}

        answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        for answer in answers:
            UserRows.add_options(answer.option_id,row_count,answer.answer)
            if not user.user_id == current_id and not verifyPermission(survey_id,current_id,'data'):
                getattr(UserRows, f'option_{row_count}_{answer.option_id}').render_kw = {'disabled': 'disabled'}
        UserRows.add_delete(row_count,user.user_id, user.displayname)
        if not user.user_id == current_id and not verifyPermission(survey_id,current_id,'data'):
            getattr(UserRows, f'delete_{row_count}_{user.displayname}_{user.user_id}').render_kw = {'style': 'display: none;'}
        row_count += 1

    #if user_already_answered is still false, none of the Form-Answers are from the current user. 
    #In this case an option to add a new value is created
    if not user_already_answered:
        UserRows.add_displayname(current_displayname,row_count)
        UserRows.add_user_id(current_id,row_count)

        answers = surveyoptions.query.filter_by(survey_id=survey_id).all()
        for answer in answers:
            UserRows.add_options(answer.id,row_count,False)

    #Initialize the comment form to add the option for new comments and read all existing comments from db including names of the user
    CommentsForm = CommentForm()
    survey_comments = db.session.query(comments, users).join(users, comments.user_id == users.id).filter(comments.survey_id == survey_id).all()

    #process any submit request
    if request.method == 'POST':
        #This happens if an answer is provided, updated or deleted. Comments are handled below
        if any('submitbtn' in key for key in request.form) or any('updatebtn' in key for key in request.form) or any('delete_' in key for key in request.form):
            row_displayname = ''
            row_user_id = ''
            mode = ''
            #Go trough all the fields and handle different scenarios based on the fieldname
            for name, field in UserRows._fields.items():
                #check if a new answer was added or an existing one was modified
                if name.startswith('submitbtn') and field.data:
                    mode = 'submit'
                elif name.startswith('updatebtn') and field.data:
                    mode = 'update'

                #get the displayname of the affected row
                if name.startswith('displayname'):
                    if field.data.strip() == '' and mode == 'submit':
                        flash('Dir fehlt da noch ein Name', 'error')
                        return render_template('survey.html', survey=survey, form=UserRows, existing_options=existing_options, value_entries=value_entries, row_count=row_count, current_user=current_user,commentform=CommentsForm,survey_comments=survey_comments, is_contributor=is_contributor, is_admin=is_admin)
                    else:
                        row_displayname = field.data

                #get the user id of the current row (can also be none)
                elif name.startswith('user_id'):
                    row_user_id = field.data

                #get the answer if the field is not disabled. disabled fields can be skipped to save ressources as they couldn't be modified
                elif name.startswith('option') and field.render_kw != {'disabled': 'disabled'}:
                    current_option_id = field.name.split('_')[-1]
                    existing_answer = surveyanswers.query.filter_by(survey_id=survey_id, option_id=current_option_id, user_id=row_user_id,displayname=row_displayname).first()
                    if existing_answer and mode == 'update':
                        existing_answer.answer = field.data
                        db.session.commit()
                    elif mode == 'submit':
                        new_answer = surveyanswers(survey_id=survey_id, option_id=current_option_id, user_id=row_user_id, displayname=row_displayname,answer=field.data)
                        db.session.add(new_answer)
                        db.session.commit()
                
                #delete all related answers of a row if the delete-button was clicked
                if name.startswith('delete') and field.data:
                    answer_displayname = name.split('_')[-2]
                    answers_to_delete = surveyanswers.query.filter_by(displayname=answer_displayname).all()
                    for answer in answers_to_delete:
                        db.session.delete(answer)
                        db.session.commit()

        #if the submitcomment-button was used, add the new comment to the db
        if 'submitComment' in request.form:
            if CommentsForm.Comment.data != '':
                newComment = comments(survey_id=survey_id, user_id=current_id,comment=CommentsForm.Comment.data)
                db.session.add(newComment)
                db.session.commit()
            else:
                flash('Du musst zuerst einen Kommentar eingeben.', 'error')
        return redirect(url_for('views.survey',survey_id=survey_id))
    return render_template('survey.html', survey=survey, form=UserRows, existing_options=existing_options, value_entries=value_entries, row_count=row_count, current_user=current_user,commentform=CommentsForm,survey_comments=survey_comments, is_contributor=is_contributor, is_admin=is_admin)

#Function to create a new survey
@views.route('/newsurvey', methods=['GET', 'POST'])
def newsurvey():
    print(dir(UserForm))
    #check if user is authenticated, as each survey needs an owner
    if not current_user.is_authenticated:
        flash('Für diese Aktion musst du angemeldet sein', 'error')
        return redirect(url_for('auth.login',next=request.path))
    
    #Create the Form
    NewSurvey = NewSurveyForm()

    #Process the fields of a form if they are returned
    if request.method == 'POST':
        if NewSurvey.title.data != '':
            def_mode = surveymodes.query.filter_by(initial=True).first()
            newValue = surveys(title=NewSurvey.title.data, description=NewSurvey.description.data, user_id=current_user.id, mode_id=def_mode.id)
            db.session.add(newValue)
            admin_role = roles.query.filter_by(security=True, data=True).first()
            survey_roles = roleassignments(user_id=current_user.id,role_id=admin_role.id,survey_id=newValue.id)
            db.session.add(survey_roles)
            db.session.commit()
            return redirect(url_for('views.survey',survey_id=newValue.id))
    return render_template('newsurvey.html', form=NewSurvey, current_user=current_user)

#Function to create a new option for an existing survey
@views.route('/newoption/<int:survey_id>', methods=['GET', 'POST'])
def newoption(survey_id):
    #check if user is authenticated, as modification is not allowed for everyone
    if not current_user.is_authenticated:
        flash('Für diese Aktion musst du angemeldet sein', 'error')
        return redirect(url_for('auth.login'))
    
    #check if survey even exists
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    #check if the current user is allowed to modify the data of the survey
    if not verifyPermission(survey_id,current_user.id,'data'):
        flash('Du bist dazu leider nicht berechtigt', 'error')
        return redirect(url_for('views.survey',survey_id=survey_id))
    
    #get all Options and create form
    options = surveyoptions.query.filter_by(survey_id=survey_id).all()
    NewOption = NewOptionForm()

    #Set a default-value, which can be changed by the user
    if request.method == 'GET':
        NewOption.datetime.data = datetime.now()

    #insert new value on submit
    if request.method == 'POST':
        if NewOption.datetime.data != '':
            NewOption = surveyoptions(survey_id=survey_id, value=NewOption.datetime.data, info=NewOption.info.data)
            db.session.add(NewOption)
            db.session.commit()
            return redirect(url_for('views.survey',survey_id=survey_id))
    return render_template('newoption.html', form=NewOption, current_user=current_user, options=options, survey_id=survey_id)

#delete existing comment
@views.route('/deletecomment/<int:comment_id>', methods=['GET', 'POST'])
def deletecomment(comment_id):
    #verify the permission of the current user
    comment = comments.query.filter_by(id=comment_id).first()
    if not verifyPermission(comment.survey_id,current_user.id,'data'):
        flash('Du bist dazu leider nicht berechtigt', 'error')
        return redirect(url_for('views.survey',survey_id=comment.survey_id))
    
    #delete comment if user is permitted
    else:
        db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('views.survey',survey_id=comment.survey_id))

#show page to modify a comment
@views.route('/modifycomment/<int:comment_id>', methods=['GET', 'POST'])
def modifycomment(comment_id):
    #verify the permission of the current user
    comment = comments.query.filter_by(id=comment_id).first()
    if not verifyPermission(comment.survey_id,current_user.id,'data'):
        flash('Du bist dazu leider nicht berechtigt!', 'error')
        return redirect(url_for('views.survey',survey_id=comment.survey_id))
    
    #initialize the form and set the value to the existing comment
    modifyComment = CommentForm()
    if request.method == 'GET':
        modifyComment.Comment.data = comment.comment
    
    #update the comment on submit
    if request.method == 'POST':
        comment.comment = modifyComment.Comment.data
        comment.edited = True
        db.session.commit()
        flash('Kommentar wurde geändert!', 'success')
        return redirect(url_for('views.survey',survey_id=comment.survey_id))

    return render_template('modifycomment.html', form=modifyComment, current_user=current_user, survey_id=comment.survey_id)

#delete an existing option of a survey
@views.route('/deleteoption/<int:option_id>', methods=['GET', 'POST'])
def deleteoption(option_id):
    
    #verify if the option and survey even exist
    option = surveyoptions.query.get(option_id)
    survey = surveys.query.get(option.survey_id)

    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    if not option:
        flash('This option does not exist', 'error')
        return redirect(url_for('views.survey',survey_id=option.survey_id))

    #verify the permissions
    if not verifyPermission(option.survey_id,current_user.id,'data'):
        flash('Du bist dazu leider nicht berechtigt', 'error')
        return redirect(url_for('views.survey',survey_id=option.survey_id))
    
    #execute the deletion if all checkes are passed
    else:
        db.session.delete(option)
        db.session.commit()
        return redirect(url_for('views.newoption',survey_id=survey.id))

#delete an entire survey, based on the sql models all options and answers will be deleted with it 
@views.route('/deletesurvey/<int:survey_id>', methods=['GET', 'POST'])
def deletesurvey(survey_id):

    #check if survey exists
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    #verify the permissions
    if not verifyPermission(survey_id,current_user.id,'data'):
        flash('Du bist dazu leider nicht berechtigt!', 'error')
        return redirect(url_for('views.index'))
    
    #delete if checks are passed
    else:
        db.session.delete(survey)
        db.session.commit()
        flash('Umfrage wurde gelöscht!', 'success')
        return redirect(url_for('views.index'))
    
#show page to modify permissions
@views.route('/modifypermissions/<int:survey_id>', methods=['GET', 'POST'])
def modifypermissions(survey_id):
    #check if survey exists
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    #verify the permissions
    if not verifyPermission(survey_id,current_user.id,'security'):
        flash('Du bist dazu leider nicht berechtigt!', 'error')
        return redirect(url_for('views.survey',survey_id=survey_id))
    
    #Initialize the form, as the validations are passed
    modifyPermissions = PermissionForm()

    if request.method == 'GET':
        modifyPermissions.mode.data = survey.mode_id
    row_count = 0

    #add existing values
    assigned_roles = roleassignments.query.filter_by(survey_id=survey_id)
    for user in assigned_roles:
        modifyPermissions.add_permission(user.user_id,row_count,user.role_id)

        #Set permission field to ready only if user id is the current user to prevent lockout
        if current_user.id == user.user_id:
            getattr(modifyPermissions, f'email_{row_count}_{user.user_id}').render_kw = {'readonly': True}
            getattr(modifyPermissions, f'permission_{row_count}_{user.user_id}').render_kw = {'disabled': 'disabled'}
            getattr(modifyPermissions, f'updatebtn_{row_count}_{user.user_id}').render_kw = {'style': 'display: none;'}
            getattr(modifyPermissions, f'deletebtn_{row_count}_{user.user_id}').render_kw = {'style': 'display: none;'}
        
        row_count += 1

    #update the comment on submit
    if request.method == 'POST':
        #This happens if a permission is added
        if any('submitbtn' in key for key in request.form):
            new_user = users.query.filter_by(email=modifyPermissions.newemail.data).first()
            new_role_id = modifyPermissions.newpermission.data

            if new_user:
                new_permission = roleassignments(user_id=new_user.id, role_id=new_role_id, survey_id=survey_id)
                db.session.add(new_permission)
                db.session.commit()
                flash('Berechtigungen wurden geändert!', 'success')
            else:
                flash('Benutzer konnte nicht hinzugefügt werden!', 'error')

        if any(key.startswith('updatebtn') for key in request.form) or any(key.startswith('deletebtn') for key in request.form):
            for name, field in modifyPermissions._fields.items():
                #check if an answer was updated or deleted
                if name.startswith('updatebtn') and field.data:
                    user_id = name.split("_")[-1]
                    role_id = getattr(modifyPermissions, f'permission_{name.split("_")[-2]}_{name.split("_")[-1]}').data
                    modified_role = roleassignments.query.filter_by(user_id=user_id, survey_id=survey_id).first()
                    modified_role.role_id = role_id
                    db.session.commit()
                elif name.startswith('deletebtn') and field.data:
                    user_id = name.split("_")[-1]
                    deleted_role = roleassignments.query.filter_by(user_id=user_id, survey_id=survey_id).first()
                    db.session.delete(deleted_role)
                    db.session.commit()
        
        if any(key.startswith('modebtn') for key in request.form):
            print(modifyPermissions.mode.data)
            if survey.mode_id != modifyPermissions.mode.data:
                survey.mode_id = modifyPermissions.mode.data
                db.session.commit()
        return redirect(url_for('views.modifypermissions',survey_id=survey_id))

    return render_template('modifypermissions.html', form=modifyPermissions, row_count=row_count, survey_id=survey_id)
    

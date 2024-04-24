from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from website import db
from .models import users, surveys, surveyanswers, surveyoptions, comments, roles, roleassignments, surveymodes
from datetime import datetime
from .functions import verifyPermission, verifyMode, syncSurveyAnswers, getSurveyAnswers
from .forms import SurveyForm, CommentForm, PermissionForm, NewOptionForm, NewSurveyForm

views = Blueprint('views', __name__)

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
    UserRows = SurveyForm()
    value_entries = len(existing_options)+2

    #set variables related to the user
    if current_user.is_authenticated:
        user = users.query.get(current_user.id)
        current_id = current_user.id
        current_displayname = user.firstname + ' ' + user.lastname
        existing_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.displayname).filter_by(survey_id=survey_id,displayname=current_displayname).group_by(surveyanswers.displayname).all()
        taken_usernames = 0
        while(existing_answers):
            taken_usernames += 1
            trimmed_displayname = current_displayname.strip('123456789')
            current_displayname = trimmed_displayname + str(taken_usernames)
            existing_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.displayname).filter_by(survey_id=survey_id,displayname=current_displayname).group_by(surveyanswers.displayname).all()
    else:
        current_id =''
        current_displayname = ''

    #check the permission-level on the page for the current user
    if verifyPermission(survey_id,'security'):
        is_contributor = True
        is_admin = True
    elif verifyPermission(survey_id,'data'):
        is_contributor = True
        is_admin = False
    else:
        is_contributor = False
        is_admin = False

    #check if options got added since the last call of the page.
    #if yes, the new option will be added as false to prevent missing values
    for user in existing_user_answers:
        syncSurveyAnswers(user.user_id,user.displayname,survey_id)

    #set boolean to check after the loop if the current user already answered
    user_already_answered = False
    #get the data from the database
    survey_data = getSurveyAnswers(survey_id, is_admin, is_contributor)

    #check if current user is in the array of the database
    for entry in survey_data['values']:
        if entry['user_id'] == current_id:
            user_already_answered = True

    #if user_already_answered is still false, none of the Form-Answers are from the current user. 
    #In this case an option to add a new value is created
    if not user_already_answered:
        answer_data = {
            'displayname': current_displayname,
            'user_id': current_id,
            'editable': True,
            'options': []
        }

        #create all answers as false, as he didn't answer yet
        answers = surveyoptions.query.filter_by(survey_id=survey_id).all()
        for option in answers:
            option_data = {
                'option_id': option.id,
                'value': False
            }
            answer_data['options'].append(option_data)

        survey_data['values'].append(answer_data)

    #Initialize the forms including data
    UserRows = SurveyForm(data=survey_data)
    CommentsForm = CommentForm()

    survey_comments = db.session.query(comments, users).join(users, comments.user_id == users.id).filter(comments.survey_id == survey_id).all()

    #process any submit request
    if request.method == 'POST':
        #This happens if an answer is provided
        if UserRows.submitbtn.data:
            #check only the last entry, as this is the latest one
            answer = UserRows.values[-1]

            #check if a displayname is provided and valid
            if not answer.displayname.data:
                flash('Dir fehlt da noch ein Name', 'error')
                return render_template('survey.html', survey=survey, form=UserRows, existing_options=existing_options, value_entries=value_entries, current_user=current_user,commentform=CommentsForm,survey_comments=survey_comments, is_contributor=is_contributor, is_admin=is_admin, user_already_answered=user_already_answered)

            #check if displayname is available
            used_displayname = surveyanswers.query.with_entities(surveyanswers.survey_id,surveyanswers.displayname).filter_by(survey_id=survey_id,displayname=answer.displayname.data).group_by(surveyanswers.displayname).all()
            if used_displayname:
                flash('Dieser Name wurde bereits verwendet', 'error')
                return render_template('survey.html', survey=survey, form=UserRows, existing_options=existing_options, value_entries=value_entries, current_user=current_user,commentform=CommentsForm,survey_comments=survey_comments, is_contributor=is_contributor, is_admin=is_admin, user_already_answered=user_already_answered)

            #go trough all options and insert them into db
            for option in answer.options:
                new_answer = surveyanswers(survey_id=survey_id, option_id=option.option_id.data,user_id=answer.user_id.data, displayname=answer.displayname.data,answer=option.value.data)
                db.session.add(new_answer)
                db.session.commit()
            
            #synchronize db-values if there was a change or not all checkboxes were in the response
            syncSurveyAnswers(answer.user_id.data,answer.displayname.data,survey_id)

        #Proccess the update of values
        elif UserRows.updatebtn.data:
            for answer in UserRows.values:
                for data in survey_data['values']:
                    #check values that could have been edited
                    if data['displayname'] == answer.displayname.data and data['editable']:
                        for survey_option in data['options']:
                            for option in answer.options:
                                #check if the value was changed and update the db session
                                if survey_option['option_id'] == option.option_id.data and survey_option['value'] != option.value.data:
                                    existing_answer = surveyanswers.query.filter_by(survey_id=survey_id,option_id=survey_option['option_id'],displayname=data['displayname']).first()
                                    existing_answer.answer = option.value.data
            #update db if a value was changed    
            if db.session.dirty:
                db.session.commit()
            #synchronize db-values if there was a change or not all checkboxes were in the response
            syncSurveyAnswers(answer.user_id.data,answer.displayname.data,survey_id)

        #Add a new comment
        elif CommentsForm.submitComment.data:
            if CommentsForm.Comment.data != '':
                newComment = comments(survey_id=survey_id, user_id=current_id,comment=CommentsForm.Comment.data)
                db.session.add(newComment)
                db.session.commit()
            else:
                flash('Du musst zuerst einen Kommentar eingeben.', 'error')
        else:
            #check which delete button was pressend and delte the according values
            for answer in UserRows.values:
                if answer.deletebtn.data:
                    answers_to_delete = surveyanswers.query.filter_by(survey_id=survey_id,displayname=answer.displayname.data).all()
                    for value in answers_to_delete:
                        db.session.delete(value)
                        db.session.commit()
                        
        return redirect(url_for('views.survey',survey_id=survey_id))   
    
    return render_template('survey.html', survey=survey, form=UserRows, existing_options=existing_options, value_entries=value_entries, current_user=current_user,commentform=CommentsForm,survey_comments=survey_comments, is_contributor=is_contributor, is_admin=is_admin, user_already_answered=user_already_answered)

#Function to create a new survey
@views.route('/newsurvey', methods=['GET', 'POST'])
def newsurvey():
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
@login_required
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
    if not verifyPermission(survey_id,'data'):
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
@login_required
def deletecomment(comment_id):
    #verify the permission of the current user
    comment = comments.query.filter_by(id=comment_id).first()
    if not verifyPermission(comment.survey_id,'data'):
        flash('Du bist dazu leider nicht berechtigt', 'error')
        return redirect(url_for('views.survey',survey_id=comment.survey_id))
    
    #delete comment if user is permitted
    else:
        db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('views.survey',survey_id=comment.survey_id))

#show page to modify a comment
@views.route('/modifycomment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def modifycomment(comment_id):
    #verify the permission of the current user
    comment = comments.query.filter_by(id=comment_id).first()
    if not verifyPermission(comment.survey_id,'data'):
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
@login_required
def deleteoption(option_id):
    
    #verify if the option and survey even exist
    option = surveyoptions.query.filter_by(id=option_id).first()
    survey = surveys.query.get(option.survey_id)

    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    if not option:
        flash('This option does not exist', 'error')
        return redirect(url_for('views.survey',survey_id=option.survey_id))

    #verify the permissions
    if not verifyPermission(option.survey_id,'data'):
        flash('Du bist dazu leider nicht berechtigt', 'error')
        return redirect(url_for('views.survey',survey_id=option.survey_id))
    
    #execute the deletion if all checkes are passed
    else:
        db.session.delete(option)
        db.session.commit()
        return redirect(url_for('views.newoption',survey_id=survey.id))

#delete an entire survey, based on the sql models all options and answers will be deleted with it 
@views.route('/deletesurvey/<int:survey_id>', methods=['GET', 'POST'])
@login_required
def deletesurvey(survey_id):

    #check if survey exists
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('This survey does not exist', 'error')
        return redirect(url_for('views.index'))
    
    #verify the permissions
    if not verifyPermission(survey_id,'data'):
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
@login_required
def modifypermissions(survey_id):
    #check if survey exists
    survey = surveys.query.get(survey_id)
    if not survey:
        flash('Diese Umfrage existiert nicht', 'error')
        return redirect(url_for('views.index'))
    
    #verify the permissions
    if not verifyPermission(survey_id,'security'):
        flash('Du bist dazu leider nicht berechtigt!', 'error')
        return redirect(url_for('views.survey',survey_id=survey_id))

    # Initialize the form
    modifyPermissions = PermissionForm()

    if request.method == 'GET':
        modifyPermissions.mode.data = survey.mode_id

        # Add existing values
        assigned_roles = roleassignments.query.filter_by(survey_id=survey_id)
        for user in assigned_roles:
            modifyPermissions.add_permission(user.user_id, user.role_id)

    #update the comment on submit
    if request.method == 'POST':
        #This happens if a permission is added
        if modifyPermissions.submitbtn.data:
            new_user = users.query.filter_by(email=modifyPermissions.newemail.data).first()
            new_role_id = modifyPermissions.newpermission.data

            if new_user:
                new_permission = roleassignments(user_id=new_user.id, role_id=new_role_id, survey_id=survey_id)
                db.session.add(new_permission)
                db.session.commit()
                flash('Berechtigungen wurden geändert!', 'success')
                return redirect(url_for('views.modifypermissions',survey_id=survey_id))
            else:
                flash('Benutzer konnte nicht hinzugefügt werden!', 'error')
        elif modifyPermissions.modebtn.data:
            if survey.mode_id != modifyPermissions.mode.data:
                survey.mode_id = modifyPermissions.mode.data
                db.session.commit()
                flash('Berechtigungen wurden geändert!', 'success')
                return redirect(url_for('views.modifypermissions',survey_id=survey_id))
        else:
            #check which delete button was pressend and delte the according values
            for existingpermission in modifyPermissions.permissions:
                if existingpermission.user_id.data != current_user.id:
                    if existingpermission.deletebtn.data:
                        deleted_role = roleassignments.query.filter_by(user_id=existingpermission.user_id.data, survey_id=survey_id).first()
                        db.session.delete(deleted_role)
                        db.session.commit()
                        flash('Berechtigungen wurden geändert!', 'success')
                        return redirect(url_for('views.modifypermissions',survey_id=survey_id))
                    elif existingpermission.updatebtn.data:
                        modified_role = roleassignments.query.filter_by(user_id=existingpermission.user_id.data, survey_id=survey_id).first()
                        modified_role.role_id = existingpermission.permission.data
                        db.session.commit()
                        flash('Berechtigungen wurden geändert!', 'success')
                        return redirect(url_for('views.modifypermissions',survey_id=survey_id))

    return render_template('modifypermissions.html', form=modifyPermissions, survey_id=survey_id)
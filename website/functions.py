from website import db
from .models import roles, roleassignments, users, surveymodes, surveys, surveyanswers, surveyoptions
from flask_login import current_user
 
#Verifies the permission of a user related to a survey
#With the level data he can modify values of the answers or comment
#The level security is used for chaning any permissions
def verifyPermission(survey_id,type):
        valid_types = {'security', 'data'}

        if not current_user.is_authenticated:
            return False

        if type not in valid_types:
            raise ValueError(f"Invalid type '{type}'. Valid levels are: {', '.join(valid_types)}")
        
        if survey_id != '' and current_user.id != '':
            if users.query.get(current_user.id).appadmin == True:
                return True
            elif type == 'security':
                available_roles = roles.query.filter_by(security=True)
                for role in available_roles:
                    if roleassignments.query.filter_by(survey_id=survey_id, role_id=role.id, user_id=current_user.id).first():
                        return True
                return False
            elif type == 'data':
                available_roles = roles.query.filter_by(data=True)
                for role in available_roles:
                    if roleassignments.query.filter_by(survey_id=survey_id, role_id=role.id, user_id=current_user.id).first():
                        return True
                return False

#Verify if the current user can access a survey
def verifyMode(survey_id):
    survey = surveys.query.get(survey_id)
    current_mode = surveymodes.query.get(survey.mode_id)

    if current_user.is_authenticated and users.query.get(current_user.id).appadmin:
        return True

    if current_mode.name == 'open':
        return True
    elif current_mode.name == 'authenticated' and current_user.is_authenticated:
        return True
    elif current_mode.name == 'invited' and current_user.is_authenticated:
        if roleassignments.query.filter_by(survey_id=survey_id, user_id=current_user.id).first():
            return True
    
    #Happens when none of the cases apply
    return False


#Function is used to insert the basic values like roles or an initial admin-account
def init_database():
    if not roles.query.filter_by(security=True, data=True).first():
        admin_role = roles(name='Admin',security=True, data=True)
        db.session.add(admin_role)
        db.session.commit()

    if not roles.query.filter_by(security=False, data=True).first():
        contributor_role = roles(name='Mitwirkender',security=False, data=True)
        db.session.add(contributor_role)
        db.session.commit()

    if not roles.query.filter_by(security=False, data=False).first():
        member_role = roles(name='Mitglied',security=False, data=False)
        db.session.add(member_role)

    if not users.query.filter_by(email='admin@wennwo.ch').first():
        base_admin = users(firstname='Webapp', lastname='Administrator', email='admin@wennwo.ch', appadmin=True, passwordhash='scrypt:32768:8:1$S9igEYmxFb4XMNuc$3ff7078e5ca7f87dd4e3bb8d63ec6086a2270f2450bf42e1896960c1c0f25d556cb08e674eb76c249fa0c9c4d27e14c82f782153f0f76f7fcc24ed24f22b9a3b')
        db.session.add(base_admin)

    if not surveymodes.query.filter_by(name='open').first():
        open_mode = surveymodes(name='open', initial=True)
        db.session.add(open_mode)

    if not surveymodes.query.filter_by(name='authenticated').first():
        auth_mode = surveymodes(name='authenticated', initial=False)
        db.session.add(auth_mode)

    if not surveymodes.query.filter_by(name='invited').first():
        invite_mode = surveymodes(name='invited', initial=False)
        db.session.add(invite_mode)

    if db.session.new:
        db.session.commit()

#Fill up Survey-Answers of a user if they are missing
def syncSurveyAnswers(user_id,displayname,survey_id):
    existing_options = surveyoptions.query.filter_by(survey_id=survey_id).all()
    answers = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user_id,displayname=displayname).all()
    if len(answers) != len(existing_options):
        for possible_option in existing_options:
            if not surveyanswers.query.filter_by(survey_id=survey_id, option_id=possible_option.id, user_id=user_id,displayname=displayname).first():
                new_option = surveyanswers(survey_id=survey_id, option_id=possible_option.id, user_id=user_id,displayname=displayname,answer=False)
                db.session.add(new_option)

        if db.session.new:
            db.session.commit()

def getSurveyAnswers(survey_id, is_admin, is_contributor):
    survey_data = {
        'values': []
    }
    
    #add all the existing answers to the before created Form and set the permissions by modifing the read-only property
    existing_user_answers = surveyanswers.query.with_entities(surveyanswers.survey_id, surveyanswers.user_id,surveyanswers.displayname).filter_by(survey_id=survey_id).group_by(surveyanswers.user_id,surveyanswers.displayname).all()
    for user in existing_user_answers:

        #check if user is authenticated and set the permission level
        if current_user.is_authenticated:
            if is_admin or is_contributor or user.user_id == current_user.id:
                editable = True
            else:
                editable = False
        else:
            editable = False

        #set answer data
        answer_data = {
            'displayname': user.displayname,
            'user_id': user.user_id,
            'editable': editable,
            'options': []
        }

        #add option data
        options = surveyanswers.query.filter_by(survey_id=survey_id,user_id=user.user_id,displayname=user.displayname).all()
        for option in options:
            option_data = {
                'option_id': option.option_id,
                'value': option.answer
            }
            answer_data['options'].append(option_data)

        survey_data['values'].append(answer_data)

    return survey_data
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField, DateTimeField, SelectField, FieldList, FormField, PasswordField
from wtforms.validators import DataRequired, Email
from .models import users, roles, surveymodes

class SurveyOptions(FlaskForm):
    option_id = IntegerField('id')
    value = BooleanField('option', default=False)

class SurveyAnswer(FlaskForm):
    displayname = StringField('displayname')
    user_id = IntegerField('user_id')
    options = FieldList(FormField(SurveyOptions),min_entries=0)
    editable = BooleanField('Bearbeiten')
    deletebtn = SubmitField('Löschen')

class SurveyForm(FlaskForm):
    submitbtn = SubmitField('Antworten')
    updatebtn = SubmitField('Aktualisieren')
    values = FieldList(FormField(SurveyAnswer), min_entries=0)

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

#Form to list all existing permissions
class PermissionSubForm(FlaskForm):
    email = StringField('E-Mail', validators=[Email()])
    user_id = IntegerField('user_id')
    permission = SelectField('Berechtigung')
    updatebtn = SubmitField('Aktualisieren')
    deletebtn = SubmitField('Löschen')

    def __init__(self, *args, **kwargs):
        super(PermissionSubForm, self).__init__(*args, **kwargs)
        # Populate choices dynamically during form initialization
        self.permission.choices = [(str(role.id), role.name) for role in roles.query.all()]

class PermissionForm(FlaskForm):
    mode = SelectField('Modus')
    modebtn = SubmitField('Aktualisieren')
    newemail = StringField('E-Mail', validators=[Email()])
    newpermission = SelectField('Berechtigung')
    submitbtn = SubmitField('Hinzufügen')
    permissions = FieldList(FormField(PermissionSubForm), min_entries=0)

    def __init__(self, *args, **kwargs):
        super(PermissionForm, self).__init__(*args, **kwargs)
        # Populate choices dynamically during form initialization
        self.newpermission.choices = [(str(role.id), role.name) for role in roles.query.all()]
        self.mode.choices = [(str(mode.id), mode.name) for mode in surveymodes.query.all()]

    def add_permission(self, user_id, role_id):
        subform = PermissionSubForm()
        subform.email = users.query.get(user_id).email
        subform.permission = role_id
        subform.user_id = user_id
        subform.process()
        self.permissions.append_entry(subform)

class LoginForm(FlaskForm):
    email = StringField('E-Mail', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    remember = BooleanField('Angemeldet bleiben')
    submit = SubmitField('Anmelden')

class RegistrationForm(FlaskForm):
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    firstname = StringField('Vorname', validators=[DataRequired()])
    lastname = StringField('Nachname', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    passwordconfirm = PasswordField('Passwort bestätigen', validators=[DataRequired()])
    submit = SubmitField('Registrieren')
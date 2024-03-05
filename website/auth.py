from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_login import login_user, logout_user, current_user
from website import db
from .models import users

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

auth = Blueprint('auth', __name__)

#Login-Page for existing users
@auth.route('/login', methods=['GET', 'POST'])
def login():
    #redirect users, that are already signed in
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))
    
    #Generate Login-Form
    form = LoginForm()

    #Validate the request if a user presses the button
    if request.method == 'POST':
        user = users.query.filter_by(email=form.email.data).first()
        if user is None or not users.check_password(user, form.password.data):
            flash('Ungültiges Login', category='error')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember.data)
        next_page = request.args.get('next')
        if not next_page:
            next_page = url_for('views.index')
        return redirect(next_page)    
    return render_template("login.html",form=form, current_user=current_user)

#Logout signed in user
@auth.route('/logout')
def logout():
    logout_user()
    flash('Du wurdest erfolgreich abgemeldet!', category='success')
    return render_template("/index.html", current_user=current_user)

#Register new users
@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    #Redirect user if he is alerady signed in
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))
    
    #Generate Form
    form = RegistrationForm()

    #Process the request if submit is pressed
    if request.method == 'POST':
        #check if passwords match
        if form.password.data != form.passwordconfirm.data:
            flash('Deine Passwörter stimmen nicht überein!', category='error')
            pass

        #check if email is not alerady in use
        if users.query.filter_by(email=form.email.data).first():
            flash('Ungültige Email!', category='error')
            pass

        #create user if checks are passed
        else:
            user = users(firstname=form.firstname.data, lastname=form.lastname.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Willkommen bei Wennwo', category='success')
            return redirect(url_for('views.index'))
    return render_template("signup.html",form=form, current_user=current_user)
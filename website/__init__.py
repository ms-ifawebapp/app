from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

login = LoginManager()
db = SQLAlchemy()
migrate = Migrate()

def start_app():
    #init app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'VerySafeKey'
    csrf = CSRFProtect(app)

    # Configuring the Flask app to connect to the MySQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/ms-ifawebapp-database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

    #init variables
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    #import modules
    from .views import views
    from .auth import auth
    from .models import users, surveys, comments, roles, roleassignments, surveyoptions, surveyanswers
    from .functions import init_database
        
    #init the database with the basic values needed
    with app.app_context():
        init_database()

    #load user
    @login.user_loader
    def load_user(id):
        return users.query.get(int(id))
    
    #Disable caching and improve seurity https://flask.palletsprojects.com/en/2.0.x/security/
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    #register blueprints of the pages
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    return app
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

login = LoginManager()
db = SQLAlchemy()
migrate = Migrate()

def start_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'VerySafeKey'

    # Configuring the Flask app to connect to the MySQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/ms-ifawebapp-database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    from .views import views
    from .auth import auth
    from .models import users, surveys, comments, roles, roleassignments, surveyoptions, surveyanswers

    @login.user_loader
    def load_user(id):
        return users.query.get(int(id))

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    return app
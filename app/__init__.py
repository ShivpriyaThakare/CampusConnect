import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Create upload directories if not exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'banners'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'logos'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'receipts'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)

    # Register all SQLAlchemy models and set Flask-Login user loader
    from app import models as _models  # noqa: F401
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Apply idempotent schema upgrades for existing databases
    ensure_schema_updates(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.coordinator import coordinator_bp
    from app.routes.student import student_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(coordinator_bp, url_prefix='/coordinator')
    app.register_blueprint(student_bp, url_prefix='/student')

    # Custom Jinja Template Filters & Context
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter('datetimeformat')
    def datetime_format_filter(value, format='%B %d, %Y at %I:%M %p'):
        if value is None:
            return ""
        return value.strftime(format)

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app


def ensure_schema_updates(app):
    """Safely add new columns/tables to existing SQLite/MySQL databases without data loss."""
    from sqlalchemy import inspect, text

    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table('clubs'):
            club_cols = {col['name'] for col in inspector.get_columns('clubs')}
            alter_statements = []
            if 'category' not in club_cols:
                alter_statements.append("ALTER TABLE clubs ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'General'")
            if 'contact_info' not in club_cols:
                alter_statements.append("ALTER TABLE clubs ADD COLUMN contact_info VARCHAR(150)")
            if 'is_archived' not in club_cols:
                alter_statements.append("ALTER TABLE clubs ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
            if alter_statements:
                with db.engine.begin() as conn:
                    for stmt in alter_statements:
                        conn.execute(text(stmt))
        db.create_all()

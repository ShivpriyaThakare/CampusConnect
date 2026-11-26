import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campus-connect-super-secret-key-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    
    # Database Configuration
    # Defaults to MySQL connection string, or SQLite fallback for development
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'campus_connect')

    # Construct DB URI: Use DATABASE_URL if set, else test MySQL or fallback to SQLite
    DEFAULT_SQLITE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'campus_connect.db')}"
    DEFAULT_MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', DEFAULT_SQLITE_URI)


class ProductionConfig(Config):
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

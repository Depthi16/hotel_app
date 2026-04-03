import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-hotel-key'
    # Database Config - Handle PostgreSQL (SSL) and local MySQL fallback
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        # Ensure SSL requirement is set for cloud databases
        if 'sslmode' not in db_url and 'render.com' in db_url:
            separator = '&' if '?' in db_url else '?'
            db_url += f'{separator}sslmode=require'
            
    SQLALCHEMY_DATABASE_URI = db_url or 'mysql+pymysql://root:root@localhost/hotel_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection Stability for Cloud (Fixes SSL decryption error)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    
    # Mail Config (Mock)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'noreply@grandhorizon.com'

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-hotel-key'
    # Updated to use root as user and root as password
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:root@localhost/hotel_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail Config (Mock)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'noreply@grandhorizon.com'

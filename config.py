import os
import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cravecart-super-secret-key-2026-delicious'
    DATABASE_PATH = os.path.join(BASE_DIR, 'cravecart.db')
    DEBUG = True
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Allows localhost development
    SESSION_COOKIE_NAME = 'cravecart_session'

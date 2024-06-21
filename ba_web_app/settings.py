# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
import os

from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"

SECRET_KEY = env.str("SECRET_KEY")
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT")
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
CACHE_TYPE = (
    "flask_caching.backends.SimpleCache"  # Can be "MemcachedCache", "RedisCache", etc.
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

WTF_CSRF_CHECK_DEFAULT = False

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = env.str("UPLOAD_FOLDER", default=PROJECT_PATH + "/uploads")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
DATABASE_URL = f"sqlite:///{PROJECT_PATH}/db.sqlite"
SQLALCHEMY_DATABASE_URI = DATABASE_URL
print(f"SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}")
# Database just use SQLite locally for now
# get directory of this file
#SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URL")

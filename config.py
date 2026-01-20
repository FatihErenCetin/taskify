# -*- coding: utf-8 -*-
"""
Configuration Settings for Smart Task Manager
==============================================
Central configuration file for all app settings.
AI features can be toggled on/off here.
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    
    # === Flask Core ===
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # === Database ===
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///taskify.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # === Babel / i18n ===
    BABEL_DEFAULT_LOCALE = 'tr'
    BABEL_SUPPORTED_LOCALES = ['tr', 'en']
    
    # === AI Features Toggle ===
    # Set to False to disable AI and use only keyword-based analysis
    AI_ENABLED = os.environ.get('AI_ENABLED', 'true').lower() == 'true'
    
    # Individual AI feature toggles
    AI_CATEGORY_ENABLED = os.environ.get('AI_CATEGORY_ENABLED', 'true').lower() == 'true'
    AI_PRIORITY_ENABLED = os.environ.get('AI_PRIORITY_ENABLED', 'true').lower() == 'true'
    AI_COMMENT_ENABLED = os.environ.get('AI_COMMENT_ENABLED', 'true').lower() == 'true'
    AI_DATE_PARSER_ENABLED = os.environ.get('AI_DATE_PARSER_ENABLED', 'true').lower() == 'true'
    
    # AI Model Settings
    AI_CATEGORY_MODEL = 'valhalla/distilbart-mnli-12-1'
    AI_COMMENT_MODEL = 'google/flan-t5-small'
    AI_CONFIDENCE_THRESHOLD = 0.4  # Minimum confidence for AI predictions
    
    # === Task Settings ===
    DEFAULT_PRIORITY = 2  # 1=High, 2=Normal, 3=Low
    DEFAULT_CATEGORY = 'General'
    
    # Priority mapping
    PRIORITY_LABELS = {
        1: {'en': 'High', 'tr': 'Yüksek'},
        2: {'en': 'Normal', 'tr': 'Normal'},
        3: {'en': 'Low', 'tr': 'Düşük'}
    }
    
    # Category mapping (Internal → Display)
    CATEGORIES = {
        'Work': {'en': 'Work', 'tr': 'İş'},
        'Personal': {'en': 'Personal', 'tr': 'Kişisel'},
        'Health': {'en': 'Health', 'tr': 'Sağlık'},
        'Education': {'en': 'Education', 'tr': 'Eğitim'},
        'Finance': {'en': 'Finance', 'tr': 'Finans'},
        'General': {'en': 'General', 'tr': 'Genel'},
    }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    AI_ENABLED = True  # Enable AI in development


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # In production, you might want to disable AI for performance
    # AI_ENABLED = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AI_ENABLED = False  # Disable AI in tests for speed


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
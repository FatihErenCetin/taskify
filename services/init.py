# -*- coding: utf-8 -*-
"""
Services Module
===============
Business logic layer connecting app.py with core NLP components.
"""

from .nlp_service import NLPService
from .stats_service import StatsService

__all__ = ['NLPService', 'StatsService']
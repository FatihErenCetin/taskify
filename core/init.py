# -*- coding: utf-8 -*-
"""
Core Module
===========
Contains AI/NLP components for task analysis.
"""

from .predictor import (
    analyze_task_ai,
    analyze_task_keywords,
    extract_date_from_text,
    get_deadline_alert
)

from .stats_ai import generate_ai_comment

__all__ = [
    'analyze_task_ai',
    'analyze_task_keywords', 
    'extract_date_from_text',
    'get_deadline_alert',
    'generate_ai_comment'
]
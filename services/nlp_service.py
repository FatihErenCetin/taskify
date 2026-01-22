# -*- coding: utf-8 -*-
"""
NLP Service
===========
Service layer for NLP operations.
Provides a clean interface between app.py and core NLP components.
Handles AI toggle logic based on configuration.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from flask import current_app

from core.predictor import (
    analyze_task_ai,
    analyze_task_keywords,
    extract_date_from_text,
    extract_date_simple,
    get_deadline_alert,
    get_nlp_status
)


class NLPService:
    """
    NLP Service class for task analysis.
    
    Automatically chooses between AI and keyword-based analysis
    based on application configuration.
    """
    
    @staticmethod
    def analyze_task(title: str, description: str = "", 
                     use_ai: bool = None) -> Dict[str, Any]:
        """
        Analyze task text and return category, priority predictions.
        
        Args:
            title: Task title
            description: Task description (optional)
            use_ai: Override AI setting (None = use config)
            
        Returns:
            Dict containing:
                - category: Predicted category string
                - priority: Predicted priority (1-3)
                - deadline: Extracted deadline (if any)
                - category_source: How category was determined
                - priority_source: How priority was determined
                - deadline_source: How deadline was determined
        """
        full_text = f"{title} {description}".strip()
        
        # Determine if AI should be used
        if use_ai is None:
            try:
                use_ai = current_app.config.get('AI_ENABLED', False) and \
                         current_app.config.get('AI_CATEGORY_ENABLED', False)
            except RuntimeError:
                # Outside application context
                use_ai = False
        
        # Extract deadline from text
        deadline, deadline_source = NLPService.extract_deadline(full_text)
        
        # Analyze with appropriate method
        if use_ai:
            result = analyze_task_ai(full_text, deadline)
        else:
            result = analyze_task_keywords(full_text, deadline)
        
        # Add deadline info
        result['deadline'] = deadline
        result['deadline_source'] = deadline_source
        
        return result
    
    @staticmethod
    def extract_deadline(text: str, use_ai: bool = None) -> Tuple[Optional[datetime], str]:
        """
        Extract deadline from natural language text.
        
        Args:
            text: Text to search for date references
            use_ai: Use advanced dateparser (None = use config)
            
        Returns:
            Tuple of (datetime or None, source string)
        """
        # Determine if advanced parsing should be used
        if use_ai is None:
            try:
                use_ai = current_app.config.get('AI_DATE_PARSER_ENABLED', False)
            except RuntimeError:
                use_ai = False
        
        deadline = None
        source = 'none'
        
        if use_ai:
            # Try advanced dateparser first
            deadline = extract_date_from_text(text)
            if deadline:
                source = 'ai_parser'
        
        # Fall back to simple extraction
        if deadline is None:
            deadline = extract_date_simple(text)
            if deadline:
                source = 'simple_parser'
        
        return deadline, source
    
    @staticmethod
    def get_task_alert(deadline) -> Optional[Dict[str, str]]:
        """
        Get deadline alert information for UI display.
        
        Args:
            deadline: Task deadline (datetime or string)
            
        Returns:
            Alert dict with msg_key, color, icon, days
        """
        return get_deadline_alert(deadline)
    
    @staticmethod
    def get_category_display(category: str, language: str = 'tr') -> str:
        """
        Get localized category display name.
        
        Args:
            category: Internal category name (English)
            language: Target language code
            
        Returns:
            Localized category name
        """
        try:
            categories = current_app.config.get('CATEGORIES', {})
            if category in categories:
                return categories[category].get(language, category)
        except RuntimeError:
            pass
        
        # Fallback translations
        fallback = {
            'Work': {'tr': 'İş', 'en': 'Work'},
            'Personal': {'tr': 'Kişisel', 'en': 'Personal'},
            'Health': {'tr': 'Sağlık', 'en': 'Health'},
            'Education': {'tr': 'Eğitim', 'en': 'Education'},
            'Finance': {'tr': 'Finans', 'en': 'Finance'},
            'General': {'tr': 'Genel', 'en': 'General'},
        }
        
        return fallback.get(category, {}).get(language, category)
    
    @staticmethod
    def get_priority_display(priority: int, language: str = 'tr') -> str:
        """
        Get localized priority display name.
        
        Args:
            priority: Priority integer (1-3)
            language: Target language code
            
        Returns:
            Localized priority name
        """
        try:
            priorities = current_app.config.get('PRIORITY_LABELS', {})
            if priority in priorities:
                return priorities[priority].get(language, str(priority))
        except RuntimeError:
            pass
        
        # Fallback translations
        fallback = {
            1: {'tr': 'Yüksek', 'en': 'High'},
            2: {'tr': 'Normal', 'en': 'Normal'},
            3: {'tr': 'Düşük', 'en': 'Low'},
        }
        
        return fallback.get(priority, {}).get(language, str(priority))
    
    @staticmethod
    def get_status() -> Dict[str, bool]:
        """
        Get NLP service status.
        
        Returns:
            Dict with availability of each NLP component
        """
        status = get_nlp_status()
        
        # Add config status
        try:
            status['ai_enabled_config'] = current_app.config.get('AI_ENABLED', False)
            status['ai_category_enabled'] = current_app.config.get('AI_CATEGORY_ENABLED', False)
            status['ai_date_parser_enabled'] = current_app.config.get('AI_DATE_PARSER_ENABLED', False)
        except RuntimeError:
            status['ai_enabled_config'] = False
            status['ai_category_enabled'] = False
            status['ai_date_parser_enabled'] = False
        
        return status
    
    @staticmethod
    def get_all_categories() -> list:
        """Get list of all available categories."""
        return ['Work', 'Personal', 'Health', 'Education', 'Finance', 'General']
    
    @staticmethod
    def get_all_priorities() -> list:
        """Get list of all priority levels."""
        return [
            {'value': 1, 'key': 'high'},
            {'value': 2, 'key': 'normal'},
            {'value': 3, 'key': 'low'},
        ]
# -*- coding: utf-8 -*-
"""
NLP Predictor Module
====================
Hybrid NLP engine for task analysis.
Supports both keyword-based and AI-based classification.

Features:
    - Category detection (keyword + AI)
    - Priority calculation (keyword + deadline)
    - Date extraction from natural language
    - Deadline alerts for UI
"""

import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Optional imports (may not be available)
try:
    from dateparser.search import search_dates
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


# ============================================================
# CONSTANTS & KEYWORDS
# ============================================================

# Category keywords for rule-based classification (Turkish & English)
CATEGORY_KEYWORDS = {
    'Work': [
        # Turkish
        'toplantı', 'rapor', 'sunum', 'müşteri', 'proje', 'ofis', 'iş', 
        'kod', 'yazılım', 'bug', 'deploy', 'analiz', 'mail', 'email',
        # English
        'meeting', 'report', 'presentation', 'client', 'project', 'office',
        'work', 'code', 'software', 'deadline', 'task', 'review'
    ],
    'Personal': [
        # Turkish
        'alışveriş', 'market', 'ev', 'aile', 'arkadaş', 'hediye', 
        'tatil', 'gezi', 'yemek', 'temizlik', 'kira', 'fatura',
        # English
        'shopping', 'home', 'family', 'friend', 'gift', 'vacation',
        'travel', 'food', 'personal', 'cleaning', 'rent'
    ],
    'Health': [
        # Turkish
        'doktor', 'hastane', 'ilaç', 'egzersiz', 'spor', 'koşu',
        'diyet', 'randevu', 'sağlık', 'ameliyat', 'diş', 'göz',
        # English
        'doctor', 'hospital', 'medicine', 'exercise', 'sport', 'run',
        'diet', 'appointment', 'health', 'surgery', 'dentist', 'gym'
    ],
    'Education': [
        # Turkish
        'ders', 'sınav', 'ödev', 'okul', 'kurs', 'kitap', 'öğren',
        'çalış', 'eğitim', 'üniversite', 'tez', 'makale', 'araştırma',
        # English
        'lesson', 'exam', 'homework', 'school', 'course', 'book',
        'learn', 'study', 'education', 'university', 'thesis', 'research'
    ],
    'Finance': [
        # Turkish
        'fatura', 'ödeme', 'banka', 'kredi', 'vergi', 'maaş',
        'para', 'hesap', 'borç', 'yatırım',
        # English
        'bill', 'payment', 'bank', 'credit', 'tax', 'salary',
        'money', 'account', 'debt', 'investment', 'finance'
    ],
}

# Priority keywords with weight scores
PRIORITY_KEYWORDS = {
    'high': {
        # Turkish
        'acil': 50, 'hemen': 40, 'kritik': 50, 'önemli': 30,
        'yarın': 35, 'mutlaka': 40, 'ivedi': 45, 'bugün': 45,
        # English
        'urgent': 50, 'critical': 50, 'important': 30, 'asap': 45,
        'immediately': 45, 'today': 40, 'tomorrow': 35, 'must': 35
    },
    'low': {
        # Turkish
        'belki': -20, 'sonra': -15, 'ileride': -20, 
        'acele yok': -25, 'zaman olursa': -20,
        # English
        'maybe': -20, 'later': -15, 'eventually': -20,
        'no rush': -25, 'whenever': -20, 'someday': -15
    }
}

# AI Model labels (English for the model)
AI_CANDIDATE_LABELS = ['Work', 'School', 'Home', 'Health', 'Social', 'Shopping', 'Finance']
AI_LABELS_MAP = {
    'Work': 'Work',
    'School': 'Education', 
    'Home': 'Personal',
    'Health': 'Health',
    'Social': 'Personal',
    'Shopping': 'Personal',
    'Finance': 'Finance'
}

# Global AI classifier (lazy loaded)
_ai_classifier = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_text(text: str) -> str:
    """Normalize text: lowercase and remove punctuation."""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


def _get_ai_classifier():
    """Lazy load the AI classifier model."""
    global _ai_classifier
    
    if _ai_classifier is None and TRANSFORMERS_AVAILABLE:
        try:
            _ai_classifier = pipeline(
                "zero-shot-classification",
                model="valhalla/distilbart-mnli-12-1"
            )
        except Exception as e:
            print(f"⚠️ Failed to load AI classifier: {e}")
            return None
    
    return _ai_classifier


def _translate_to_english(text: str) -> str:
    """Translate text to English for AI model."""
    if not TRANSLATOR_AVAILABLE:
        return text
    
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text


# ============================================================
# KEYWORD-BASED ANALYSIS (Always Available)
# ============================================================

def detect_category_keywords(text: str) -> Optional[str]:
    """
    Detect category using keyword matching.
    
    Args:
        text: Task text to analyze
        
    Returns:
        Category string or None if no match
    """
    text_clean = _clean_text(text)
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_clean:
                return category
    
    return None


def calculate_priority_keywords(text: str, deadline: datetime = None) -> int:
    """
    Calculate priority score using keywords and deadline.
    
    Args:
        text: Task text to analyze
        deadline: Optional deadline datetime
        
    Returns:
        Priority integer (1=High, 2=Normal, 3=Low)
    """
    score = 0
    text_clean = _clean_text(text)
    
    # Check high priority keywords
    for word, points in PRIORITY_KEYWORDS['high'].items():
        if word in text_clean:
            score += points
    
    # Check low priority keywords
    for word, points in PRIORITY_KEYWORDS['low'].items():
        if word in text_clean:
            score += points  # points are negative
    
    # Deadline urgency
    if deadline:
        days_left = (deadline - datetime.now()).days
        if days_left < 0:
            score += 70  # Overdue
        elif days_left == 0:
            score += 60  # Today
        elif days_left == 1:
            score += 45  # Tomorrow
        elif days_left < 3:
            score += 30  # Within 3 days
        elif days_left < 7:
            score += 15  # Within a week
    
    # Convert score to priority level
    if score >= 40:
        return 1  # High
    elif score >= 15:
        return 2  # Normal
    else:
        return 3  # Low


def analyze_task_keywords(text: str, deadline: datetime = None) -> Dict[str, Any]:
    """
    Analyze task using only keyword matching (no AI).
    
    Args:
        text: Task text (title + description)
        deadline: Optional deadline
        
    Returns:
        Dict with category, priority, and sources
    """
    category = detect_category_keywords(text) or 'General'
    priority = calculate_priority_keywords(text, deadline)
    
    return {
        'category': category,
        'priority': priority,
        'category_source': 'keyword',
        'priority_source': 'keyword'
    }


# ============================================================
# AI-BASED ANALYSIS (Optional)
# ============================================================

def detect_category_ai(text: str, confidence_threshold: float = 0.4) -> Optional[str]:
    """
    Detect category using AI zero-shot classification.
    
    Args:
        text: Task text to analyze
        confidence_threshold: Minimum confidence score
        
    Returns:
        Category string or None if confidence too low
    """
    classifier = _get_ai_classifier()
    
    if classifier is None:
        return None
    
    try:
        # Translate to English for better AI performance
        text_en = _translate_to_english(text)
        
        result = classifier(text_en, AI_CANDIDATE_LABELS)
        
        if result['scores'][0] >= confidence_threshold:
            ai_label = result['labels'][0]
            return AI_LABELS_MAP.get(ai_label, 'General')
    except Exception as e:
        print(f"⚠️ AI classification failed: {e}")
    
    return None


def analyze_task_ai(text: str, deadline: datetime = None, 
                    confidence_threshold: float = 0.4) -> Dict[str, Any]:
    """
    Analyze task using hybrid approach (keywords first, then AI).
    
    Args:
        text: Task text (title + description)
        deadline: Optional deadline
        confidence_threshold: Minimum AI confidence
        
    Returns:
        Dict with category, priority, and sources
    """
    # Try keyword detection first (fast)
    category = detect_category_keywords(text)
    category_source = 'keyword' if category else None
    
    # Fall back to AI if no keyword match
    if category is None:
        category = detect_category_ai(text, confidence_threshold)
        category_source = 'ai' if category else None
    
    # Final fallback
    if category is None:
        category = 'General'
        category_source = 'default'
    
    # Priority is always keyword-based (more reliable)
    priority = calculate_priority_keywords(text, deadline)
    
    return {
        'category': category,
        'priority': priority,
        'category_source': category_source,
        'priority_source': 'keyword'
    }


# ============================================================
# DATE EXTRACTION
# ============================================================

def extract_date_from_text(text: str, prefer_future: bool = True) -> Optional[datetime]:
    """
    Extract date from natural language text.
    
    Args:
        text: Text containing date references (e.g., "yarın", "next Monday")
        prefer_future: If True, ambiguous dates resolve to future
        
    Returns:
        Extracted datetime or None
    """
    if not DATEPARSER_AVAILABLE:
        return None
    
    try:
        settings = {'PREFER_DATES_FROM': 'future'} if prefer_future else {}
        results = search_dates(text, languages=['tr', 'en'], settings=settings)
        
        if results:
            return results[0][1]  # Return first found date
    except Exception as e:
        print(f"⚠️ Date parsing failed: {e}")
    
    return None


def extract_date_simple(text: str) -> Optional[datetime]:
    """
    Simple date extraction without dateparser library.
    Handles basic Turkish and English date keywords.
    
    Args:
        text: Text to search for dates
        
    Returns:
        Extracted datetime or None
    """
    text_lower = text.lower()
    now = datetime.now()
    
    # Turkish keywords
    if 'bugün' in text_lower or 'today' in text_lower:
        return now.replace(hour=23, minute=59, second=59)
    
    if 'yarın' in text_lower or 'tomorrow' in text_lower:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    
    if 'haftaya' in text_lower or 'next week' in text_lower:
        return (now + timedelta(days=7)).replace(hour=23, minute=59, second=59)
    
    if 'bu hafta' in text_lower or 'this week' in text_lower:
        days_until_friday = (4 - now.weekday()) % 7
        return (now + timedelta(days=days_until_friday)).replace(hour=23, minute=59, second=59)
    
    # Day names (Turkish)
    days_tr = {
        'pazartesi': 0, 'salı': 1, 'çarşamba': 2, 
        'perşembe': 3, 'cuma': 4, 'cumartesi': 5, 'pazar': 6
    }
    
    for day_name, day_num in days_tr.items():
        if day_name in text_lower:
            days_ahead = day_num - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
    
    # Day names (English)
    days_en = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2,
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in days_en.items():
        if day_name in text_lower:
            days_ahead = day_num - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
    
    return None


# ============================================================
# UI HELPERS
# ============================================================

def get_deadline_alert(deadline) -> Optional[Dict[str, str]]:
    """
    Generate deadline alert for UI display.
    
    Args:
        deadline: Deadline datetime or string
        
    Returns:
        Dict with msg, color, icon for Bootstrap alerts
    """
    if not deadline:
        return None
    
    # Parse string to datetime if needed
    if isinstance(deadline, str):
        try:
            deadline = datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                deadline = datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError:
                return None
    
    days = (deadline - datetime.now()).days
    
    if days < 0:
        return {
            'msg_key': 'deadline_overdue',
            'color': 'danger',
            'icon': 'exclamation-triangle-fill',
            'days': abs(days)
        }
    elif days == 0:
        return {
            'msg_key': 'deadline_today',
            'color': 'warning',
            'icon': 'fire',
            'days': 0
        }
    elif days == 1:
        return {
            'msg_key': 'deadline_tomorrow',
            'color': 'warning',
            'icon': 'clock-fill',
            'days': 1
        }
    elif days < 3:
        return {
            'msg_key': 'deadline_soon',
            'color': 'info',
            'icon': 'clock',
            'days': days
        }
    elif days < 7:
        return {
            'msg_key': 'deadline_this_week',
            'color': 'secondary',
            'icon': 'calendar-week',
            'days': days
        }
    
    return None


# ============================================================
# CHECK AVAILABILITY
# ============================================================

def get_nlp_status() -> Dict[str, bool]:
    """
    Get status of NLP components.
    
    Returns:
        Dict with availability of each component
    """
    return {
        'dateparser': DATEPARSER_AVAILABLE,
        'translator': TRANSLATOR_AVAILABLE,
        'transformers': TRANSFORMERS_AVAILABLE,
        'ai_classifier': _get_ai_classifier() is not None
    }
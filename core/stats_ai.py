# -*- coding: utf-8 -*-
"""
AI Comment Generator
====================
Generates personalized productivity comments using AI.
Falls back to template-based comments when AI is unavailable.
"""

from typing import Dict, Any, Optional

# Optional imports
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False


# Global AI model (lazy loaded)
_comment_generator = None


def _get_comment_generator():
    """Lazy load the text generation model."""
    global _comment_generator
    
    if _comment_generator is None and TRANSFORMERS_AVAILABLE:
        try:
            _comment_generator = pipeline(
                "text2text-generation",
                model="google/flan-t5-small"
            )
        except Exception as e:
            print(f"⚠️ Failed to load comment generator: {e}")
            return None
    
    return _comment_generator


def _translate_to_turkish(text: str) -> str:
    """Translate text to Turkish."""
    if not TRANSLATOR_AVAILABLE:
        return text
    
    try:
        return GoogleTranslator(source='en', target='tr').translate(text)
    except:
        return text


def generate_ai_comment(stats: Dict[str, Any], language: str = 'tr') -> str:
    """
    Generate AI-powered productivity comment.
    
    Args:
        stats: Dictionary containing user statistics
            - completion_rate: Percentage of completed tasks
            - total_tasks: Total number of tasks
            - completed_tasks: Number of completed tasks
            - focus_score: Average priority of completed tasks
            - most_planned_category: Most frequently planned category
            - most_completed_category: Most completed category
        language: Target language ('tr' or 'en')
        
    Returns:
        Personalized comment string
    """
    generator = _get_comment_generator()
    
    if generator is None:
        # Fall back to template-based comment
        return generate_template_comment(stats, language)
    
    try:
        # Build prompt
        prompt = (
            f"Context: A user has a task completion rate of {stats.get('completion_rate', 0)}%, "
            f"has managed {stats.get('total_tasks', 0)} total tasks, "
            f"completed {stats.get('completed_tasks', 0)} tasks, "
            f"and focuses on {stats.get('most_completed_category', 'various')} tasks. "
            f"Task: Write a one-sentence motivational feedback for this user."
        )
        
        result = generator(prompt, max_length=60, do_sample=False)
        comment = result[0]['generated_text']
        
        # Translate to Turkish if needed
        if language == 'tr':
            comment = _translate_to_turkish(comment)
        
        return comment
        
    except Exception as e:
        print(f"⚠️ AI comment generation failed: {e}")
        return generate_template_comment(stats, language)


def generate_template_comment(stats: Dict[str, Any], language: str = 'tr') -> str:
    """
    Generate template-based comment (fallback when AI unavailable).
    
    Args:
        stats: User statistics dictionary
        language: Target language ('tr' or 'en')
        
    Returns:
        Template comment string
    """
    completion_rate = stats.get('completion_rate', 0)
    total_tasks = stats.get('total_tasks', 0)
    best_category = stats.get('most_completed_category', 'General')
    
    # Templates for different performance levels
    templates = {
        'tr': {
            'no_tasks': "Henüz görev eklenmemiş. İlk görevinizi ekleyerek başlayın!",
            'low': f"Tamamlama oranınız %{completion_rate}. Daha küçük görevlerle başlamayı deneyin!",
            'medium': f"İyi gidiyorsunuz! %{completion_rate} tamamlama oranıyla {total_tasks} görevi yönetiyorsunuz.",
            'high': f"Mükemmel performans! %{completion_rate} tamamlama oranıyla harikasınız. {best_category} alanında çok başarılısınız!",
            'perfect': f"Olağanüstü! Tüm görevlerinizi tamamladınız. {best_category} alanında uzmanlaştınız!"
        },
        'en': {
            'no_tasks': "No tasks yet. Start by adding your first task!",
            'low': f"Your completion rate is {completion_rate}%. Try starting with smaller tasks!",
            'medium': f"Good progress! You're managing {total_tasks} tasks with {completion_rate}% completion rate.",
            'high': f"Excellent performance! {completion_rate}% completion rate is impressive. You excel at {best_category}!",
            'perfect': f"Outstanding! You've completed all your tasks. You've mastered {best_category}!"
        }
    }
    
    lang_templates = templates.get(language, templates['en'])
    
    if total_tasks == 0:
        return lang_templates['no_tasks']
    elif completion_rate < 30:
        return lang_templates['low']
    elif completion_rate < 70:
        return lang_templates['medium']
    elif completion_rate < 100:
        return lang_templates['high']
    else:
        return lang_templates['perfect']


def get_performance_badge(completion_rate: float, language: str = 'tr') -> Dict[str, str]:
    """
    Get performance badge based on completion rate.
    
    Args:
        completion_rate: Task completion percentage
        language: Target language
        
    Returns:
        Dict with badge name, color, and icon
    """
    badges = {
        'tr': {
            'beginner': {'name': 'Başlangıç', 'color': 'secondary', 'icon': 'seedling'},
            'bronze': {'name': 'Bronz', 'color': 'warning', 'icon': 'medal'},
            'silver': {'name': 'Gümüş', 'color': 'info', 'icon': 'award'},
            'gold': {'name': 'Altın', 'color': 'warning', 'icon': 'trophy'},
            'platinum': {'name': 'Platin', 'color': 'primary', 'icon': 'gem'},
        },
        'en': {
            'beginner': {'name': 'Beginner', 'color': 'secondary', 'icon': 'seedling'},
            'bronze': {'name': 'Bronze', 'color': 'warning', 'icon': 'medal'},
            'silver': {'name': 'Silver', 'color': 'info', 'icon': 'award'},
            'gold': {'name': 'Gold', 'color': 'warning', 'icon': 'trophy'},
            'platinum': {'name': 'Platinum', 'color': 'primary', 'icon': 'gem'},
        }
    }
    
    lang_badges = badges.get(language, badges['en'])
    
    if completion_rate < 20:
        return lang_badges['beginner']
    elif completion_rate < 40:
        return lang_badges['bronze']
    elif completion_rate < 60:
        return lang_badges['silver']
    elif completion_rate < 80:
        return lang_badges['gold']
    else:
        return lang_badges['platinum']


def is_ai_available() -> bool:
    """Check if AI comment generation is available."""
    return _get_comment_generator() is not None
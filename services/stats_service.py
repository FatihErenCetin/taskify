# -*- coding: utf-8 -*-
"""
Statistics Service
==================
Service layer for user statistics and analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter
from flask import current_app
import hashlib

from models import db, Task, User
from core.stats_ai import (
    generate_ai_comment,
    generate_template_comment,
    get_performance_badge,
    is_ai_available
)


class StatsService:
    """
    Statistics service for user analytics.
    """
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dict containing all user statistics
        """
        # Get all user tasks
        all_tasks = Task.query.filter_by(user_id=user_id).all()
        completed_tasks = [t for t in all_tasks if t.is_completed]
        active_tasks = [t for t in all_tasks if not t.is_completed]
        overdue_tasks = [t for t in active_tasks if t.is_overdue]
        
        total = len(all_tasks)
        completed = len(completed_tasks)
        
        if total == 0:
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'active_tasks': 0,
                'overdue_tasks': 0,
                'completion_rate': 0,
                'focus_score': 0,
                'most_planned_category': 'N/A',
                'most_completed_category': 'N/A',
                'avg_completion_time': None,
                'tasks_by_category': {},
                'tasks_by_priority': {},
                'weekly_completed': 0,
                'streak_days': 0
            }
        
        # Completion rate
        completion_rate = round((completed / total) * 100, 1)
        
        # Focus score (average priority of completed tasks, inverted so lower = better focus)
        focus_score = 0
        if completed_tasks:
            avg_priority = sum(t.priority for t in completed_tasks) / completed
            focus_score = round(4 - avg_priority, 1)  # Convert to 1-3 scale where higher = better
        
        # Category analysis
        all_categories = [t.category for t in all_tasks]
        completed_categories = [t.category for t in completed_tasks]
        
        most_planned = Counter(all_categories).most_common(1)
        most_completed = Counter(completed_categories).most_common(1)
        
        # Tasks by category
        tasks_by_category = dict(Counter(all_categories))
        
        # Tasks by priority
        priority_counts = Counter(t.priority for t in all_tasks)
        tasks_by_priority = {
            'high': priority_counts.get(1, 0),
            'normal': priority_counts.get(2, 0),
            'low': priority_counts.get(3, 0)
        }
        
        # Average completion time
        avg_completion_time = None
        completion_times = []
        for task in completed_tasks:
            if task.completed_at and task.created_at:
                delta = task.completed_at - task.created_at
                completion_times.append(delta.total_seconds() / 3600)  # Hours
        
        if completion_times:
            avg_hours = sum(completion_times) / len(completion_times)
            if avg_hours < 24:
                avg_completion_time = f"{avg_hours:.1f}h"
            else:
                avg_completion_time = f"{avg_hours/24:.1f}d"
        
        # Weekly completed
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_completed = len([
            t for t in completed_tasks 
            if t.completed_at and t.completed_at > week_ago
        ])
        
        # Streak calculation (consecutive days with completed tasks)
        streak_days = StatsService._calculate_streak(completed_tasks)
        
        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'active_tasks': len(active_tasks),
            'overdue_tasks': len(overdue_tasks),
            'completion_rate': completion_rate,
            'focus_score': focus_score,
            'most_planned_category': most_planned[0][0] if most_planned else 'N/A',
            'most_completed_category': most_completed[0][0] if most_completed else 'N/A',
            'avg_completion_time': avg_completion_time,
            'tasks_by_category': tasks_by_category,
            'tasks_by_priority': tasks_by_priority,
            'weekly_completed': weekly_completed,
            'streak_days': streak_days
        }
    
    @staticmethod
    def _calculate_streak(completed_tasks: List[Task]) -> int:
        """Calculate current streak of consecutive days with completions."""
        if not completed_tasks:
            return 0
        
        # Get unique completion dates
        completion_dates = set()
        for task in completed_tasks:
            if task.completed_at:
                completion_dates.add(task.completed_at.date())
        
        if not completion_dates:
            return 0
        
        # Check streak from today backwards
        streak = 0
        current_date = datetime.utcnow().date()
        
        while current_date in completion_dates:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
    
    @staticmethod
    def _calculate_stats_hash(stats: Dict[str, Any]) -> str:
        """Calculate hash of stats to detect changes."""
        key_values = f"{stats.get('total_tasks', 0)}_{stats.get('completed_tasks', 0)}_{stats.get('completion_rate', 0)}"
        return hashlib.md5(key_values.encode()).hexdigest()

    @staticmethod
    def get_ai_comment(user_id: int, language: str = 'tr',
                       use_ai: bool = None) -> str:
        """
        Generate productivity comment for user with caching.

        Args:
            user_id: User ID
            language: Target language ('tr' or 'en')
            use_ai: Override AI setting

        Returns:
            Comment string
        """
        stats = StatsService.get_user_stats(user_id)
        user = User.query.get(user_id)

        if not user:
            return generate_template_comment(stats, language)

        # Calculate current stats hash
        current_hash = StatsService._calculate_stats_hash(stats)

        # Check if cached comment is still valid
        if (user.ai_comment_cache and
            user.stats_hash == current_hash and
            user.ai_comment_updated_at):
            return user.ai_comment_cache

        # Determine if AI should be used
        if use_ai is None:
            try:
                use_ai = current_app.config.get('AI_ENABLED', False) and \
                         current_app.config.get('AI_COMMENT_ENABLED', False)
            except RuntimeError:
                use_ai = False

        # Generate new comment
        if use_ai and is_ai_available():
            comment = generate_ai_comment(stats, language)
        else:
            comment = generate_template_comment(stats, language)

        # Cache the comment
        user.ai_comment_cache = comment
        user.stats_hash = current_hash
        user.ai_comment_updated_at = datetime.utcnow()
        db.session.commit()

        return comment

    @staticmethod
    def invalidate_ai_comment_cache(user_id: int):
        """Invalidate AI comment cache for a user."""
        user = User.query.get(user_id)
        if user:
            user.stats_hash = None
            db.session.commit()
    
    @staticmethod
    def get_performance_badge(user_id: int, language: str = 'tr') -> Dict[str, str]:
        """
        Get performance badge for user.
        
        Args:
            user_id: User ID
            language: Target language
            
        Returns:
            Badge dict with name, color, icon
        """
        stats = StatsService.get_user_stats(user_id)
        return get_performance_badge(stats['completion_rate'], language)
    
    @staticmethod
    def get_category_breakdown(user_id: int) -> List[Dict[str, Any]]:
        """
        Get detailed category breakdown for charts.
        
        Args:
            user_id: User ID
            
        Returns:
            List of category stats for visualization
        """
        tasks = Task.query.filter_by(user_id=user_id).all()
        
        category_stats = {}
        for task in tasks:
            cat = task.category
            if cat not in category_stats:
                category_stats[cat] = {'total': 0, 'completed': 0}
            
            category_stats[cat]['total'] += 1
            if task.is_completed:
                category_stats[cat]['completed'] += 1
        
        result = []
        for category, stats in category_stats.items():
            completion_rate = 0
            if stats['total'] > 0:
                completion_rate = round((stats['completed'] / stats['total']) * 100, 1)
            
            result.append({
                'category': category,
                'total': stats['total'],
                'completed': stats['completed'],
                'completion_rate': completion_rate
            })
        
        return sorted(result, key=lambda x: x['total'], reverse=True)
    
    @staticmethod
    def get_weekly_progress(user_id: int, weeks: int = 4) -> List[Dict[str, Any]]:
        """
        Get weekly task completion progress.
        
        Args:
            user_id: User ID
            weeks: Number of weeks to include
            
        Returns:
            List of weekly stats
        """
        result = []
        today = datetime.utcnow()
        
        for i in range(weeks):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            # Tasks created this week
            created = Task.query.filter(
                Task.user_id == user_id,
                Task.created_at >= week_start,
                Task.created_at < week_end
            ).count()
            
            # Tasks completed this week
            completed = Task.query.filter(
                Task.user_id == user_id,
                Task.completed_at >= week_start,
                Task.completed_at < week_end
            ).count()
            
            result.append({
                'week_start': week_start.strftime('%Y-%m-%d'),
                'week_label': f"W{today.isocalendar()[1] - i}",
                'created': created,
                'completed': completed
            })
        
        return list(reversed(result))
    
    @staticmethod
    def get_upcoming_deadlines(user_id: int, days: int = 7) -> List[Task]:
        """
        Get tasks with upcoming deadlines.
        
        Args:
            user_id: User ID
            days: Number of days to look ahead
            
        Returns:
            List of tasks with approaching deadlines
        """
        cutoff = datetime.utcnow() + timedelta(days=days)
        
        tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.is_completed == False,
            Task.deadline != None,
            Task.deadline <= cutoff
        ).order_by(Task.deadline.asc()).all()
        
        return tasks
    
    @staticmethod
    def is_ai_available() -> bool:
        """Check if AI features are available."""
        return is_ai_available()

    @staticmethod
    def get_timeline_data(user_id: int, past_days: int = 14, future_days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily timeline data for task events (created and deadlines only).

        Args:
            user_id: User ID
            past_days: Number of days to look back
            future_days: Number of days to look ahead

        Returns:
            List of daily events for timeline visualization
        """
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=past_days)
        end_date = today + timedelta(days=future_days)

        # Get all relevant tasks
        tasks = Task.query.filter_by(user_id=user_id).all()

        # Build daily event map
        daily_events = {}

        # Initialize all days
        current = start_date
        while current <= end_date:
            daily_events[current.isoformat()] = {
                'date': current.isoformat(),
                'created': [],
                'deadlines': []
            }
            current += timedelta(days=1)

        for task in tasks:
            # Created events (only for incomplete tasks)
            if task.created_at and not task.is_completed:
                created_date = task.created_at.date().isoformat()
                if created_date in daily_events:
                    daily_events[created_date]['created'].append({
                        'id': task.id,
                        'title': task.title,
                        'category': task.category
                    })

            # Deadline events (only for incomplete tasks)
            if task.deadline and not task.is_completed:
                deadline_date = task.deadline.date().isoformat()
                if deadline_date in daily_events:
                    daily_events[deadline_date]['deadlines'].append({
                        'id': task.id,
                        'title': task.title,
                        'category': task.category,
                        'is_overdue': task.deadline.date() < today
                    })

        # Convert to sorted list
        result = []
        for date_str in sorted(daily_events.keys()):
            day_data = daily_events[date_str]
            # Only include days with events or today
            if (day_data['created'] or day_data['deadlines'] or
                date_str == today.isoformat()):
                day_data['is_today'] = (date_str == today.isoformat())
                day_data['is_past'] = (date_str < today.isoformat())
                result.append(day_data)

        return result
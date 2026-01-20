# -*- coding: utf-8 -*-
"""
Smart Task Manager - Main Application
=====================================
Flask-based task management with NLP categorization and multi-language support.
"""

from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user, 
    login_required, current_user
)
from flask_babel import Babel, _
from datetime import datetime

from config import get_config
from models import db, User, Task
from services.nlp_service import NLPService
from services.stats_service import StatsService


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app(config_class=None):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    babel.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints (if any)
    # app.register_blueprint(...)
    
    return app


# ============================================================
# EXTENSION INSTANCES
# ============================================================

babel = Babel()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


# ============================================================
# CREATE APP INSTANCE
# ============================================================

app = Flask(__name__)
app.config.from_object(get_config())

# Initialize extensions
db.init_app(app)
babel.init_app(app)
login_manager.init_app(app)


# ============================================================
# BABEL CONFIGURATION
# ============================================================

@babel.localeselector
def get_locale():
    """Select best matching language."""
    if 'language' in session:
        return session['language']
    
    if current_user.is_authenticated and current_user.preferred_language:
        return current_user.preferred_language
    
    return request.accept_languages.best_match(
        app.config['BABEL_SUPPORTED_LOCALES']
    )


@app.route('/set-language/<language>')
def set_language(language):
    """Set user's preferred language."""
    if language in app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = language
        
        if current_user.is_authenticated:
            current_user.preferred_language = language
            db.session.commit()
    
    return redirect(request.referrer or url_for('home'))


# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash(_('login_required'), 'warning')
    return redirect(url_for('login', next=request.url))


# ============================================================
# CONTEXT PROCESSORS
# ============================================================

@app.context_processor
def inject_globals():
    """Inject global variables into templates."""
    return {
        'now': datetime.utcnow(),
        'current_language': get_locale(),
        'ai_enabled': app.config.get('AI_ENABLED', False),
        'NLPService': NLPService,
        'StatsService': StatsService
    }


# ============================================================
# ROUTES - PUBLIC
# ============================================================

@app.route('/')
def home():
    """Home page."""
    return render_template('home.html')


@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@app.route('/contact')
def contact():
    """Contact page."""
    return render_template('contact.html')


# ============================================================
# ROUTES - AUTHENTICATION
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        
        # Validation
        if password != password_confirm:
            flash(_('password_mismatch'), 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash(_('username_taken'), 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash(_('email_taken'), 'danger')
            return redirect(url_for('register'))
        
        # Create user
        user = User(
            username=username,
            email=email,
            preferred_language=get_locale()
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(_('register_success'), 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(_('login_success', username=user.username), 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('tasks'))
        else:
            flash(_('login_error'), 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash(_('logout_success'), 'info')
    return redirect(url_for('home'))


# ============================================================
# ROUTES - TASKS
# ============================================================

@app.route('/tasks')
@login_required
def tasks():
    """Task list page."""
    # Active tasks
    active_tasks = Task.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).all()
    
    # Sort by priority and deadline
    active_tasks_sorted = sorted(
        active_tasks,
        key=lambda t: (t.priority, t.deadline or datetime.max)
    )
    
    # Completed tasks
    completed_tasks = Task.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(Task.completed_at.desc()).limit(10).all()
    
    # Get deadline alerts
    for task in active_tasks_sorted:
        task.alert = NLPService.get_task_alert(task.deadline)
    
    return render_template(
        'tasks.html',
        active_tasks=active_tasks_sorted,
        completed_tasks=completed_tasks
    )


@app.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """Add new task."""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        selected_priority = request.form.get('priority', '0')
        selected_category = request.form.get('category', 'auto')
        deadline_str = request.form.get('deadline', '')
        use_nlp = request.form.get('use_nlp') == 'on'
        
        # Initialize with defaults
        category = app.config['DEFAULT_CATEGORY']
        priority = app.config['DEFAULT_PRIORITY']
        deadline = None
        category_source = 'manual'
        priority_source = 'manual'
        deadline_source = 'manual'
        
        # Parse manual deadline
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                deadline_source = 'manual'
            except ValueError:
                pass
        
        # Use NLP analysis if enabled
        if use_nlp or selected_category == 'auto' or selected_priority == '0':
            analysis = NLPService.analyze_task(
                title, 
                description,
                use_ai=current_user.ai_features_enabled
            )
            
            # Auto category
            if selected_category == 'auto':
                category = analysis['category']
                category_source = analysis['category_source']
            else:
                category = selected_category
            
            # Auto priority
            if selected_priority == '0':
                priority = analysis['priority']
                priority_source = analysis['priority_source']
            else:
                priority = int(selected_priority)
            
            # Extract deadline from text if not manually set
            if not deadline and analysis.get('deadline'):
                deadline = analysis['deadline']
                deadline_source = analysis.get('deadline_source', 'parsed')
        else:
            # Manual selection
            category = selected_category
            priority = int(selected_priority) if selected_priority else 2
        
        # Create task
        new_task = Task(
            title=title,
            description=description,
            category=category,
            priority=priority,
            deadline=deadline,
            category_source=category_source,
            priority_source=priority_source,
            deadline_source=deadline_source,
            user_id=current_user.id,
            assigned_by_id=current_user.id
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        flash(_('task_added'), 'success')
        return redirect(url_for('tasks'))
    
    # GET - show form with categories and priorities
    return render_template(
        'add_task.html',
        categories=NLPService.get_all_categories(),
        priorities=NLPService.get_all_priorities()
    )


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit existing task."""
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description', '')
        task.priority = int(request.form.get('priority', 2))
        task.category = request.form.get('category', 'General')
        
        # Update source to manual since user edited
        task.category_source = 'manual'
        task.priority_source = 'manual'
        
        deadline_str = request.form.get('deadline', '')
        if deadline_str:
            try:
                task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                task.deadline_source = 'manual'
            except ValueError:
                pass
        else:
            task.deadline = None
        
        db.session.commit()
        flash(_('task_updated'), 'success')
        return redirect(url_for('tasks'))
    
    return render_template(
        'edit_task.html',
        task=task,
        categories=NLPService.get_all_categories(),
        priorities=NLPService.get_all_priorities()
    )


@app.route('/tasks/<int:task_id>/delete')
@login_required
def delete_task(task_id):
    """Delete a task."""
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))
    
    db.session.delete(task)
    db.session.commit()
    
    flash(_('task_deleted'), 'info')
    return redirect(url_for('tasks'))


@app.route('/tasks/<int:task_id>/toggle')
@login_required
def toggle_task(task_id):
    """Toggle task completion status."""
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))
    
    if task.is_completed:
        task.mark_incomplete()
    else:
        task.mark_complete()
    
    db.session.commit()
    return redirect(url_for('tasks'))


# ============================================================
# ROUTES - STATISTICS
# ============================================================

@app.route('/stats')
@login_required
def stats():
    """User statistics page."""
    user_stats = StatsService.get_user_stats(current_user.id)
    badge = StatsService.get_performance_badge(current_user.id, get_locale())
    category_breakdown = StatsService.get_category_breakdown(current_user.id)
    weekly_progress = StatsService.get_weekly_progress(current_user.id)
    upcoming = StatsService.get_upcoming_deadlines(current_user.id)
    
    # Get AI comment
    ai_comment = StatsService.get_ai_comment(
        current_user.id, 
        get_locale(),
        use_ai=current_user.ai_features_enabled
    )
    
    return render_template(
        'stats.html',
        stats=user_stats,
        badge=badge,
        category_breakdown=category_breakdown,
        weekly_progress=weekly_progress,
        upcoming_tasks=upcoming,
        ai_comment=ai_comment,
        ai_available=StatsService.is_ai_available()
    )


# ============================================================
# ROUTES - API (for AJAX requests)
# ============================================================

@app.route('/api/analyze', methods=['POST'])
@login_required
def api_analyze():
    """API endpoint for real-time task analysis."""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    analysis = NLPService.analyze_task(
        data['text'],
        data.get('description', ''),
        use_ai=current_user.ai_features_enabled
    )
    
    # Add localized labels
    lang = get_locale()
    analysis['category_display'] = NLPService.get_category_display(
        analysis['category'], lang
    )
    analysis['priority_display'] = NLPService.get_priority_display(
        analysis['priority'], lang
    )
    
    # Format deadline
    if analysis.get('deadline'):
        analysis['deadline_formatted'] = analysis['deadline'].strftime('%Y-%m-%d')
    
    return jsonify(analysis)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for user statistics."""
    stats = StatsService.get_user_stats(current_user.id)
    return jsonify(stats)


@app.route('/api/nlp-status')
@login_required
def api_nlp_status():
    """API endpoint for NLP service status."""
    return jsonify(NLPService.get_status())


# ============================================================
# ROUTES - SETTINGS
# ============================================================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page."""
    if request.method == 'POST':
        # Update language preference
        language = request.form.get('language')
        if language in app.config['BABEL_SUPPORTED_LOCALES']:
            current_user.preferred_language = language
            session['language'] = language
        
        # Update AI preference
        current_user.ai_features_enabled = request.form.get('ai_enabled') == 'on'
        
        db.session.commit()
        flash(_('settings_saved'), 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html')


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ============================================================
# CLI COMMANDS
# ============================================================

@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    db.create_all()
    print('✅ Database initialized.')


@app.cli.command('create-admin')
def create_admin():
    """Create admin user."""
    import getpass
    
    username = input('Admin username: ')
    email = input('Admin email: ')
    password = getpass.getpass('Admin password: ')
    
    admin = User(
        username=username,
        email=email,
        role='admin'
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    print(f'✅ Admin user "{username}" created.')


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Database and tables created successfully.')
        print(f'🤖 AI Features: {"Enabled" if app.config["AI_ENABLED"] else "Disabled"}')
        print(f'🌍 Default Language: {app.config["BABEL_DEFAULT_LOCALE"]}')
    
    app.run(debug=True, port=5000)
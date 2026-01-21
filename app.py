# -*- coding: utf-8 -*-
"""
Smart Task Manager - Main Application
=====================================
Flask-based task management with NLP categorization and multi-language support.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_babel import Babel, _
from flask_wtf.csrf import CSRFProtect
from datetime import datetime

from config import get_config
from models import db, User, Task, Group, group_members
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
    #babel.init_app(app)
    #login_manager.init_app(app)
    
    # Register blueprints (if any)
    # app.register_blueprint(...)
    
    return app

# ============================================================
# LOCALE SELECTOR FUNCTION
# ============================================================

def get_locale():
    """Select best matching language."""
    # Check session first
    if 'language' in session:
        return session['language']

    # Check user preference
    try:
        if current_user.is_authenticated and hasattr(current_user, 'preferred_language'):
            if current_user.preferred_language:
                return current_user.preferred_language
    except:
        pass


# ============================================================
# CREATE APP INSTANCE
# ============================================================

app = Flask(__name__)
app.config.from_object(get_config())

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# Initialize CSRF protection
csrf = CSRFProtect(app)

#babel.init_app(app)

# ============================================================
# EXTENSION INSTANCES
# ============================================================

# Initialize Babel with locale_selector (Flask-Babel 3.0+ syntax)
babel = Babel(app, locale_selector=get_locale)


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
    """Task list page with optional group filter."""
    # Get filter parameter
    group_id = request.args.get('group_id', type=int)

    # Get groups user administers (for dropdown)
    administered_groups = Group.query.filter_by(admin_id=current_user.id).all()

    # Determine view mode
    selected_group = None
    is_group_view = False

    if group_id:
        # Validate user is admin of this group
        selected_group = Group.query.filter_by(id=group_id, admin_id=current_user.id).first()
        if selected_group:
            is_group_view = True

    if is_group_view and selected_group:
        # GROUP VIEW: Tasks assigned BY current_user TO group members
        member_ids = [m.id for m in selected_group.members]

        # Active tasks assigned to group members by current user
        active_tasks = Task.query.filter(
            Task.user_id.in_(member_ids),
            Task.assigned_by_id == current_user.id,
            Task.is_completed == False
        ).all()

        # Completed tasks assigned to group members by current user
        completed_tasks = Task.query.filter(
            Task.user_id.in_(member_ids),
            Task.assigned_by_id == current_user.id,
            Task.is_completed == True
        ).order_by(Task.completed_at.desc()).limit(20).all()
    else:
        # SELF VIEW: Current user's own tasks (existing behavior)
        active_tasks = Task.query.filter_by(
            user_id=current_user.id,
            is_completed=False
        ).all()

        completed_tasks = Task.query.filter_by(
            user_id=current_user.id,
            is_completed=True
        ).order_by(Task.completed_at.desc()).limit(10).all()

    # Sort active tasks by priority and deadline
    active_tasks_sorted = sorted(
        active_tasks,
        key=lambda t: (t.priority, t.deadline or datetime.max)
    )

    # Get deadline alerts
    for task in active_tasks_sorted:
        task.alert = NLPService.get_task_alert(task.deadline)

    return render_template(
        'tasks.html',
        active_tasks=active_tasks_sorted,
        completed_tasks=completed_tasks,
        administered_groups=administered_groups,
        selected_group=selected_group,
        is_group_view=is_group_view
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
        analysis_mode = request.form.get('analysis_mode', 'rule')  # manual, rule, ai

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

        # Determine analysis mode
        if analysis_mode == 'manual':
            # Full manual mode - no automatic analysis
            category = selected_category if selected_category != 'auto' else 'General'
            priority = int(selected_priority) if selected_priority != '0' else 2
            category_source = 'manual'
            priority_source = 'manual'
        elif analysis_mode in ('rule', 'ai'):
            # Automatic analysis mode
            use_ai = (analysis_mode == 'ai')

            analysis = NLPService.analyze_task(
                title,
                description,
                use_ai=use_ai
            )

            # Auto category
            if selected_category == 'auto':
                category = analysis['category']
                category_source = analysis['category_source']
            else:
                category = selected_category
                category_source = 'manual'

            # Auto priority
            if selected_priority == '0':
                priority = analysis['priority']
                priority_source = analysis['priority_source']
            else:
                priority = int(selected_priority)
                priority_source = 'manual'

            # Extract deadline from text if not manually set
            if not deadline and analysis.get('deadline'):
                deadline = analysis['deadline']
                deadline_source = analysis.get('deadline_source', 'parsed')
        
        # Determine task assignment
        assign_to_id = current_user.id
        assign_to_str = request.form.get('assign_to', '')
        if assign_to_str and assign_to_str != str(current_user.id):
            # Verify user is in one of current_user's groups
            assigned_user_id = int(assign_to_str)
            my_groups = Group.query.filter_by(admin_id=current_user.id).all()
            valid_member_ids = set()
            for g in my_groups:
                for member in g.members:
                    valid_member_ids.add(member.id)
            if assigned_user_id in valid_member_ids:
                assign_to_id = assigned_user_id

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
            user_id=assign_to_id,
            assigned_by_id=current_user.id
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        flash(_('task_added'), 'success')
        return redirect(url_for('tasks'))
    
    # GET - show form with categories and priorities
    # Grup admini ise, grubundaki üyeleri getir
    assignable_users = []
    my_groups = Group.query.filter_by(admin_id=current_user.id).all()
    if my_groups:
        seen_ids = set()
        for g in my_groups:
            for member in g.members:
                if member.id not in seen_ids:
                    assignable_users.append(member)
                    seen_ids.add(member.id)

    return render_template(
        'add_task.html',
        categories=NLPService.get_all_categories(),
        priorities=NLPService.get_all_priorities(),
        users=assignable_users,
        groups=my_groups
    )


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit existing task."""
    task = Task.query.get_or_404(task_id)
    
    # Sadece görevi atayan kişi düzenleyebilir
    if task.assigned_by_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        selected_priority = request.form.get('priority', '0')
        selected_category = request.form.get('category', 'auto')
        analysis_mode = request.form.get('analysis_mode', 'manual')
        
        # Varsayılan değerler (mevcut değerler)
        category = task.category
        priority = task.priority
        category_source = task.category_source
        priority_source = task.priority_source
        
        # Analiz moduna göre işlem yap
        if analysis_mode == 'manual':
            # Manuel mod - form değerlerini doğrudan kullan
            category = selected_category if selected_category != 'auto' else task.category
            priority = int(selected_priority) if selected_priority != '0' else task.priority
            category_source = 'manual'
            priority_source = 'manual'
        elif analysis_mode in ('rule', 'ai'):
            # Yeniden analiz modu
            use_ai = (analysis_mode == 'ai')
            
            analysis = NLPService.analyze_task(
                title,
                description,
                use_ai=use_ai
            )
            
            # Kategori: Otomatik mi elle mi seçilmiş?
            if selected_category == 'auto':
                category = analysis['category']
                category_source = analysis['category_source']
            else:
                category = selected_category
                category_source = 'manual'
            
            # Öncelik: Otomatik mi elle mi seçilmiş?
            if selected_priority == '0':
                priority = analysis['priority']
                priority_source = analysis['priority_source']
            else:
                priority = int(selected_priority)
                priority_source = 'manual'
        
        # Görev alanlarını güncelle
        task.title = title
        task.description = description
        task.category = category
        task.priority = priority
        task.category_source = category_source
        task.priority_source = priority_source
        
        # Deadline
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
    """Delete a task. Only the creator (assigner) can delete."""
    task = Task.query.get_or_404(task_id)

    # Sadece görevi oluşturan/atayan kişi silebilir
    if task.assigned_by_id != current_user.id:
        flash('Sadece gorevi atayan kisi silebilir.', 'danger')
        return redirect(url_for('tasks'))

    db.session.delete(task)
    db.session.commit()

    flash(_('task_deleted'), 'info')

    # Preserve group_id if coming from group view
    group_id = request.args.get('group_id', type=int)
    if group_id:
        return redirect(url_for('tasks', group_id=group_id))
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
# ROUTES - GROUPS
# ============================================================

@app.route('/groups')
@login_required
def groups():
    """List user's groups."""
    # Gruplar: Admin olduklarım + Üye olduklarım
    administered_groups = Group.query.filter_by(admin_id=current_user.id).all()
    member_groups = current_user.groups.all()

    return render_template(
        'groups.html',
        administered_groups=administered_groups,
        member_groups=member_groups
    )


@app.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    """Create a new group."""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        member_ids = request.form.getlist('members')

        # Create group
        group = Group(
            name=name,
            description=description,
            admin_id=current_user.id
        )
        db.session.add(group)
        db.session.flush()  # Get group ID

        # Add selected members
        for member_id in member_ids:
            user = User.query.get(int(member_id))
            if user and user.id != current_user.id:
                group.add_member(user)

        db.session.commit()
        flash('Grup basariyla olusturuldu!', 'success')
        return redirect(url_for('groups'))

    # GET - show form with all users except current
    all_users = User.query.filter(User.id != current_user.id).all()
    return render_template('create_group.html', users=all_users)


@app.route('/groups/<int:group_id>')
@login_required
def view_group(group_id):
    """View group details."""
    group = Group.query.get_or_404(group_id)

    # Check access: must be admin or member
    if not group.is_admin(current_user) and not group.is_member(current_user):
        flash('Bu gruba erisim izniniz yok.', 'danger')
        return redirect(url_for('groups'))

    return render_template('view_group.html', group=group)


@app.route('/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    """Edit group (admin only)."""
    group = Group.query.get_or_404(group_id)

    if not group.is_admin(current_user):
        flash('Sadece grup admini duzenleyebilir.', 'danger')
        return redirect(url_for('groups'))

    if request.method == 'POST':
        group.name = request.form['name']
        group.description = request.form.get('description', '')

        # Update members
        new_member_ids = set(map(int, request.form.getlist('members')))
        current_member_ids = set(m.id for m in group.members.all())

        # Remove members not in new list
        for member_id in current_member_ids - new_member_ids:
            user = User.query.get(member_id)
            if user:
                group.remove_member(user)

        # Add new members
        for member_id in new_member_ids - current_member_ids:
            user = User.query.get(member_id)
            if user and user.id != current_user.id:
                group.add_member(user)

        db.session.commit()
        flash('Grup guncellendi!', 'success')
        return redirect(url_for('view_group', group_id=group_id))

    all_users = User.query.filter(User.id != current_user.id).all()
    current_members = [m.id for m in group.members.all()]

    return render_template(
        'edit_group.html',
        group=group,
        users=all_users,
        current_members=current_members
    )


@app.route('/groups/<int:group_id>/delete')
@login_required
def delete_group(group_id):
    """Delete group (admin only)."""
    group = Group.query.get_or_404(group_id)

    if not group.is_admin(current_user):
        flash('Sadece grup admini silebilir.', 'danger')
        return redirect(url_for('groups'))

    db.session.delete(group)
    db.session.commit()

    flash('Grup silindi.', 'info')
    return redirect(url_for('groups'))


# ============================================================
# ROUTES - SETTINGS
# ============================================================

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    # Get user statistics
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, is_completed=True).count()
    active_tasks = total_tasks - completed_tasks

    # Calculate completion rate
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

    return render_template(
        'profile.html',
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        active_tasks=active_tasks,
        completion_rate=completion_rate
    )


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page."""
    return render_template('settings.html')


@app.route('/settings/profile', methods=['POST'])
@login_required
def settings_profile():
    """Update user profile."""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    
    # Validation
    if not username or not email:
        flash('Kullanici adi ve e-posta zorunludur.', 'danger')
        return redirect(url_for('settings'))
    
    # Check if username is taken (by another user)
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != current_user.id:
        flash('Bu kullanici adi zaten kullaniliyor.', 'danger')
        return redirect(url_for('settings'))
    
    # Check if email is taken (by another user)
    existing_email = User.query.filter_by(email=email).first()
    if existing_email and existing_email.id != current_user.id:
        flash('Bu e-posta adresi zaten kullaniliyor.', 'danger')
        return redirect(url_for('settings'))
    
    # Update user
    current_user.username = username
    current_user.email = email
    db.session.commit()
    
    flash('Profil bilgileri guncellendi.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/password', methods=['POST'])
@login_required
def settings_password():
    """Change user password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    new_password_confirm = request.form.get('new_password_confirm', '')
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Mevcut sifre yanlis.', 'danger')
        return redirect(url_for('settings'))
    
    # Check new passwords match
    if new_password != new_password_confirm:
        flash('Yeni sifreler eslesiyor.', 'danger')
        return redirect(url_for('settings'))
    
    # Check password length
    if len(new_password) < 6:
        flash('Sifre en az 6 karakter olmalidir.', 'danger')
        return redirect(url_for('settings'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Sifre basariyla degistirildi.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/preferences', methods=['POST'])
@login_required
def settings_preferences():
    """Update user preferences."""
    # Update language preference
    language = request.form.get('language')
    if language in app.config['BABEL_SUPPORTED_LOCALES']:
        current_user.preferred_language = language
        session['language'] = language
    
    # Update AI preference
    current_user.ai_features_enabled = request.form.get('ai_enabled') == 'on'
    
    db.session.commit()
    flash('Tercihler kaydedildi.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/clear-tasks')
@login_required
def settings_clear_tasks():
    """Delete all user's tasks."""
    # Delete tasks where user is the owner
    Task.query.filter_by(user_id=current_user.id).delete()
    # Delete tasks user assigned to others
    Task.query.filter_by(assigned_by_id=current_user.id).delete()
    db.session.commit()
    
    flash('Tum gorevler silindi.', 'warning')
    return redirect(url_for('settings'))


@app.route('/settings/delete-account')
@login_required
def settings_delete_account():
    """Delete user account and all data."""
    user_id = current_user.id
    
    # Delete user's tasks
    Task.query.filter_by(user_id=user_id).delete()
    Task.query.filter_by(assigned_by_id=user_id).delete()
    
    # Delete user's groups
    Group.query.filter_by(admin_id=user_id).delete()
    
    # Logout and delete user
    logout_user()
    User.query.filter_by(id=user_id).delete()
    db.session.commit()
    
    flash('Hesabiniz basariyla silindi.', 'info')
    return redirect(url_for('home'))


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
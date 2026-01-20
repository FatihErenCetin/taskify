"""
Smart Task Manager - Main Application
=====================================
A Flask-based to-do application with NLP categorization and prioritization.
Supports multiple languages via Flask-Babel.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, g
#from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_babel import Babel, _
#from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from models import db, User, Task


# ==========================================
# NLP CATEGORIZATION SYSTEM
# ==========================================

# Category keywords (Turkish)
CATEGORY_KEYWORDS = {
    'Work': ['toplantı', 'meeting', 'rapor', 'sunum', 'müşteri', 'proje', 'mail', 'email', 'ofis', 'deadline', 'report', 'presentation', 'client', 'project', 'office'],
    'Personal': ['alışveriş', 'market', 'ev', 'aile', 'arkadaş', 'hediye', 'tatil', 'gezi', 'yemek', 'shopping', 'home', 'family', 'friend', 'gift', 'vacation', 'travel', 'food'],
    'Health': ['doktor', 'hastane', 'ilaç', 'egzersiz', 'spor', 'koşu', 'diyet', 'randevu', 'sağlık', 'ameliyat', 'doctor', 'hospital', 'medicine', 'exercise', 'sport', 'run', 'diet', 'appointment', 'health', 'surgery'],
    'Education': ['ders', 'sınav', 'ödev', 'okul', 'kurs', 'kitap', 'öğren', 'çalış', 'eğitim', 'lesson', 'exam', 'homework', 'school', 'course', 'book', 'learn', 'study', 'education'],
    'Finance': ['fatura', 'ödeme', 'banka', 'kredi', 'vergi', 'maaş', 'para', 'hesap', 'bill', 'payment', 'bank', 'credit', 'tax', 'salary', 'money', 'account'],
}

# Category weights for priority calculation
CATEGORY_WEIGHTS = {
    'Work': 3,
    'Personal': 1,
    'Health': 5,
    'Education': 2,
    'Finance': 4,
    'General': 1
}

# Priority keywords
PRIORITY_KEYWORDS = {
    'high': ['acil', 'hemen', 'bugün', 'kritik', 'önemli', 'urgent', 'yarın', 'doktor', 'sağlık', 'randevu', 'mutlaka', 'immediately', 'today', 'critical', 'important', 'tomorrow', 'must'],
    'low': ['belki', 'bir ara', 'sonra', 'ileride', 'zaman olursa', 'maybe', 'later', 'sometime', 'eventually', 'whenever'],
}


def determine_category(text):
    """
    Determine task category from text using keyword matching.

    Args:
        text: Task title and/or description

    Returns:
        Category string (Work, Personal, Health, Education, Finance, or General)
    """
    text = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return 'General'


def determine_priority(text):
    """
    Determine task priority from text using keyword matching.

    Args:
        text: Task title and/or description

    Returns:
        Priority integer (1=High, 2=Normal, 3=Low)
    """
    text = text.lower()

    for keyword in PRIORITY_KEYWORDS['high']:
        if keyword in text:
            return 1  # High

    for keyword in PRIORITY_KEYWORDS['low']:
        if keyword in text:
            return 3  # Low

    return 2  # Normal


def calculate_priority_score(task):
    """
    Calculate a sorting score for tasks based on priority, deadline, and category.
    Lower score = higher urgency = shown first.

    Args:
        task: Task model instance

    Returns:
        Float score for sorting
    """
    # Base priority weight
    if task.deadline is not None:
        today = datetime.utcnow()
        days_remaining = (task.deadline - today).days + 1  # Avoid 0
        priority_weight = task.priority * days_remaining - CATEGORY_WEIGHTS.get(task.category, 1)
    else:
        priority_weight = task.priority * 10 - CATEGORY_WEIGHTS.get(task.category, 1)

    # Date weight (older tasks shown first)
    date_weight = task.created_at.timestamp() if task.created_at else 0

    return priority_weight + (date_weight / 1000000)


# ==========================================
# FLASK APPLICATION SETUP
# ==========================================

app = Flask(__name__)

# === Configuration ===
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'gizli-anahtar-degistir-bunu-123!'  #

# === Babel Configuration ===
app.config['BABEL_DEFAULT_LOCALE'] = 'tr'  # Default language: Turkish
app.config['BABEL_SUPPORTED_LOCALES'] = ['tr', 'en']  # Supported languages

# === Initialize Extensions ===
db.init_app(app)
babel = Babel(app)

# === Flask-Login Setup ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Giriş yapılmamışsa yönlendir
#login_manager.login_message = 'Bu sayfayı görmek için giriş yapmalısınız.'
login_manager.login_message_category = 'warning'


# ==========================================
# BABEL LOCALE SELECTOR
# ==========================================

@babel.localeselector
def get_locale():
    """
    Select the best matching language for the user.

    Priority:
        1. User's explicit choice (stored in session)
        2. Browser's Accept-Language header
        3. Default locale (Turkish)
    """
    # Check if user has explicitly selected a language
    if 'language' in session:
        return session['language']

    # Check browser preferences
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])

@app.route('/set-language/<language>')
def set_language(language):
    """
    Set user's preferred language.

    Args:
        language: Language code ('tr' or 'en')
    """
    if language in app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = language

    # Redirect back to previous page or home
    return redirect(request.referrer or url_for('home'))


# ==========================================
# FLASK-LOGIN USER LOADER
# ==========================================
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


# ==========================================
# FLASK-LOGIN UNAUTHORIZED HANDLER
# ==========================================
@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access attempts."""
    flash(_('login_required'), 'warning')
    return redirect(url_for('login', next=request.url))


# ==========================================
# CONTEXT PROCESSORS
# ==========================================
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'now': datetime.utcnow(),
        'current_language': get_locale()
    }


# ==========================================
# ROUTES - PUBLIC PAGES
# ==========================================
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




# ==========================================
# ROUTES - AUTHENTICATION
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
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

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(_('register_success'), 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(_('login_success', username=user.username), 'success')

            # Redirect to requested page or tasks
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




# ==========================================
# ROUTES - TASK MANAGEMENT
# ==========================================
@app.route('/tasks')
@login_required
def tasks():
    """Task list page - shows user's active and completed tasks."""
    # Get active tasks (not completed)
    active_tasks = Task.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).all()

    # Sort by priority score
    active_tasks_sorted = sorted(active_tasks, key=calculate_priority_score)

    # Get completed tasks (newest first)
    completed_tasks = Task.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(Task.completed_at.desc()).all()

    return render_template(
        'tasks.html',
        active_tasks=active_tasks_sorted,
        completed_tasks=completed_tasks
    )


@app.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """Add new task page."""
    if request.method == 'POST':
        # Get form data
        title = request.form['title']
        description = request.form.get('description', '')
        selected_priority = int(request.form.get('priority', 0))
        selected_category = request.form.get('category', 'NLP')
        deadline_str = request.form.get('deadline', '')

        # Combine text for NLP analysis
        full_text = f"{title} {description}"

        # Determine category (NLP or manual)
        if selected_category == 'NLP':
            category = determine_category(full_text)
        else:
            category = selected_category

        # Determine priority (NLP or manual)
        if selected_priority == 0:
            priority = determine_priority(full_text)
        else:
            priority = selected_priority

        # Parse deadline
        deadline = None
        if deadline_str and deadline_str.strip():
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                deadline = None

        # Create new task
        new_task = Task(
            title=title,
            description=description,
            category=category,
            priority=priority,
            deadline=deadline,
            user_id=current_user.id,
            assigned_by_id=current_user.id  # Self-assigned
        )

        db.session.add(new_task)
        db.session.commit()

        flash(_('task_added'), 'success')
        return redirect(url_for('tasks'))

    return render_template('add_task.html')


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit existing task."""
    task = Task.query.get_or_404(task_id)

    # Authorization check
    if task.user_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))

    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description', '')
        task.priority = int(request.form.get('priority', 2))
        task.category = request.form.get('category', 'General')

        deadline_str = request.form.get('deadline', '')
        if deadline_str and deadline_str.strip():
            try:
                task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                pass
        else:
            task.deadline = None

        db.session.commit()
        flash(_('task_updated'), 'success')
        return redirect(url_for('tasks'))

    return render_template('edit_task.html', task=task)


@app.route('/tasks/<int:task_id>/delete')
@login_required
def delete_task(task_id):
    """Delete a task."""
    task = Task.query.get_or_404(task_id)

    # Authorization check
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

    # Authorization check
    if task.user_id != current_user.id:
        flash(_('access_denied'), 'danger')
        return redirect(url_for('tasks'))

    # Toggle status
    if task.is_completed:
        task.mark_incomplete()
    else:
        task.mark_complete()

    db.session.commit()
    return redirect(url_for('tasks'))



# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('errors/500.html'), 500




# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Database and tables created successfully.')

    app.run(debug=True, port=5000)
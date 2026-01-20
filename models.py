from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize the database instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User Model
    Represents a user in the system. Can be an 'admin' or a standard 'user'.
    """
    __tablename__ = 'users'

    # Identity & Authentication
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Stores the hashed password
    
    # Role Management ('admin' or 'user')
    user_role = db.Column(db.String(20), default='user') 
    
    # Metadata
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Relationships ---

    # 1. Tasks assigned TO this user (The user is the performer)
    # Access via: user.tasks
    tasks = db.relationship(
        'Task', 
        foreign_keys='Task.user_id', 
        backref='performer', 
        lazy=True
    )
    
    # 2. Tasks created BY this user (The user is the assigner/creator)
    # Access via: user.created_tasks
    created_tasks = db.relationship(
        'Task', 
        foreign_keys='Task.assigned_by_id', 
        backref='creator', 
        lazy=True
    )

    def get_id(self):
        """
        Override default get_id() for Flask-Login.
        Flask-Login expects 'id', but our primary key is 'user_id'.
        """
        return str(self.user_id)


class Task(db.Model):
    """
    Task Model
    Represents a specific task assigned to a user.
    Includes AI-generated fields for categorization and prioritization.
    """
    __tablename__ = 'tasks'

    # Core Task Info
    task_id = db.Column(db.Integer, primary_key=True)
    task_title = db.Column(db.String(150), nullable=False)
    task_explanation = db.Column(db.Text, nullable=True)  # Detailed description for AI analysis
    
    # Timing & Status
    task_deadline = db.Column(db.DateTime, nullable=True)
    task_date_created = db.Column(db.DateTime, default=datetime.utcnow)
    task_is_completed = db.Column(db.Boolean, default=False)
    task_date_completed = db.Column(db.DateTime, nullable=True)

    # AI-Generated Fields
    task_category = db.Column(db.String(50), default='General')  # e.g., Work, Health, Finance
    task_priority = db.Column(db.Integer, default=50)            # Score from 0 (Low) to 100 (Urgent)

    # --- Foreign Keys ---

    # The user responsible for completing the task
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # The user who created/assigned the task (Could be Admin or the User themselves)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.task_title} - Priority: {self.task_priority}>'
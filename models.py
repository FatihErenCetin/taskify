"""
Database Models for Smart Task Manager
======================================
This module contains SQLAlchemy models for User and Task entities.
Supports role-based access (admin/user) and task assignment between users.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash  # For password hashing

# Initialize the database instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User Model
    ----------
    Represents a user in the system.

    Roles:
        - 'admin': Can assign tasks to other users
        - 'user': Can only manage their own tasks

    Relationships:
        - tasks: Tasks assigned TO this user (user is the performer)
        - created_tasks: Tasks created BY this user (user is the assigner)
    """

    __tablename__ = 'users'

    # === Identity & Authentication ===
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Stores the hashed password
    # === Role Management ===
    role = db.Column(db.String(20), default='user')  # ('admin' or 'user')
    # === Metadata ===
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    # === Preferences ===
    preferred_language = db.Column(db.String(5), default='tr')
    ai_features_enabled = db.Column(db.Boolean, default=True)


    # === Relationships ===

    # Tasks assigned TO this user (user will perform these tasks)
    # Access via: user.tasks
    tasks = db.relationship('Task', 
                            foreign_keys='Task.user_id', 
                            backref='performer', 
                            lazy=True
                           )

    # Tasks created BY this user (user assigned these to others or self)
    # Access via: user.created_tasks
    created_tasks = db.relationship('Task', 
                                      foreign_keys='Task.assigned_by_id', 
                                      backref='creator', 
                                      lazy=True
                                     )

    # === Methods ===
    def set_password(self, password):
        """
        Hash the password and store it in password_hash.
        Uses werkzeug's secure hashing (pbkdf2:sha256 by default).
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Verify a password against the stored hash.
        Returns True if password matches, False otherwise.
        """
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """
        Check if user has admin privileges.
        Returns True if role is 'admin', else False.
        """
        return self.role == 'admin'

    def __repr__(self): 
        """
        String representation of the User.
        Returns the username.
        """
        return f'<User {self.username}>'


class Task(db.Model):
    """
    Task Model
    ----------
    Represents a task in the system.

    Features:
        - NLP-generated category and priority
        - Assignment tracking (who assigned, who performs)
        - Completion status and timestamps

    Priority Scale:
        1 = High (Urgent)
        2 = Normal
        3 = Low

    Categories:
        Work, Personal, Health, Education, Finance, General
    """
    __tablename__ = 'tasks'

    # === Core Task Info ===
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Detailed description for AI analysis
    # === Timing & Status ===
    deadline = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)     # Completion status
    # === NLP-Generated Fields ===
    category = db.Column(db.String(50), default='General')  # e.g., Work, Health, Finance
    priority = db.Column(db.Integer, default=2)            # 1=High, 2=Normal, 3=Low
    # === AI Metadata (for tracking) ===
    category_source = db.Column(db.String(20), default='manual')  # 'manual', 'keyword', 'ai'
    priority_source = db.Column(db.String(20), default='manual')
    deadline_source = db.Column(db.String(20), default='manual')  # 'manual', 'parsed'

    # === Foreign Keys ===

    # The user responsible for completing the task
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # The user who created/assigned the task (Could be Admin or the User themselves)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # === Methods ===

    def mark_complete(self):
        """Mark task as completed with timestamp."""
        self.is_completed = True
        self.completed_at = datetime.utcnow()

    def mark_incomplete(self):
        """Mark task as incomplete, clear completion timestamp."""
        self.is_completed = False
        self.completed_at = None

    @property
    def is_overdue(self):
        """Check if task is past deadline."""
        if self.deadline and not self.is_completed:
            return datetime.utcnow() > self.deadline
        return False

    @property
    def days_until_deadline(self):
        """Get days remaining until deadline."""
        if self.deadline:
            delta = self.deadline - datetime.utcnow()
            return delta.days
        return None

    def __repr__(self):
        status = "✓" if self.is_completed else "○"
        return f'<Task {status} {self.title} (P{self.priority})>'
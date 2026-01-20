from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin # <--- YENİ: Mixin eklendi
from datetime import datetime

db = SQLAlchemy()

# 1. TABLO: Kullanıcılar
# UserMixin sayesinde is_authenticated vb. özellikler otomatik gelir.
class User(UserMixin, db.Model): 
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False) # Şifre
    
    # İlişki
    tasks = db.relationship('Task', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

# 2. TABLO: Görevler (Değişiklik Yok)
class Task(db.Model):
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # AI Alanları
    category = db.Column(db.String(50), default="Genel")
    priority_score = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    
    # User ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.title}>'
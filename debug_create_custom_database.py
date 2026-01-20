import sqlite3
from datetime import datetime, timedelta

def create_custom_databases():
    """Initializes separate databases for users and tasks with specific keys."""
    
    # 1. Setup users.db
    with sqlite3.connect('users.db') as conn_user:
        cursor = conn_user.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_role TEXT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn_user.commit()

    # 2. Setup tasks.db
    with sqlite3.connect('tasks.db') as conn_task:
        cursor = conn_task.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_title TEXT NOT NULL,
                task_explanation TEXT,
                task_deadline TIMESTAMP,
                task_date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                task_is_completed BOOLEAN DEFAULT 0,
                task_date_completed TIMESTAMP,
                task_category TEXT,
                task_priority INTEGER,
                user_id INTEGER,
                assigned_by_id INTEGER
            )
        ''')
        conn_task.commit()
    
    print("✅ Custom databases 'users.db' and 'tasks.db' created successfully.")



def populate_custom_data():
    # 1. Populate users.db
    with sqlite3.connect('users.db') as conn_user:
        cursor = conn_user.cursor()
        users = [
            (1, 'Ahmet_Owner', 'Owner', 'ahmet@taskify.com', 'hash_123', '2026-01-10 09:00:00'),
            (2, 'Selin_Dev', 'Participant', 'selin@taskify.com', 'hash_456', '2026-01-12 10:30:00')
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO users (user_id, username, user_role, email, password, registration_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', users)
        conn_user.commit()

    # 2. Populate tasks.db
    with sqlite3.connect('tasks.db') as conn_task:
        cursor = conn_task.cursor()
        
        # Current time for relative dates
        now = datetime.now()
        
        # Example tasks
        # Format: (title, explanation, deadline, created, is_completed, date_completed, category, priority, user_id, assigned_by_id)
        tasks = [
            # --- AHMET (User ID: 1) ---
            # Completed: Self-assigned
            ('Proje Planı Hazırla', '72 saatlik plan', (now + timedelta(days=1)).isoformat(), 
             (now - timedelta(days=1)).isoformat(), 1, now.isoformat(), 'İş', 1, 1, 1),
            
            # Pending: High Priority
            ('Sunum Dosyası', 'Yatırımcı sunumu için slaytlar', (now + timedelta(days=2)).isoformat(), 
             now.isoformat(), 0, None, 'İş', 1, 1, 1),
            
            # Completed: Finance
            ('Fatura Ödemesi', 'Ofis internet faturası', now.isoformat(), 
             (now - timedelta(hours=5)).isoformat(), 1, now.isoformat(), 'Finans', 2, 1, 1),

            # --- SELİN (User ID: 2) ---
            # Pending: Assigned by Ahmet
            ('Veritabanı Entegrasyonu', 'SQLite tablolarını bağla', (now + timedelta(days=2)).isoformat(), 
             now.isoformat(), 0, None, 'İş', 2, 2, 1),
            
            # Completed: Health (Self-assigned)
            ('Egzersiz', '30 dk yürüyüş', (now + timedelta(hours=5)).isoformat(), 
             (now - timedelta(days=1)).isoformat(), 1, (now - timedelta(hours=1)).isoformat(), 'Sağlık', 3, 2, 2),
            
            # Pending: Education (Self-assigned)
            ('Flask Kursu İzle', 'Section 5 ve 6 videoları', (now + timedelta(days=3)).isoformat(), 
             now.isoformat(), 0, None, 'Eğitim', 2, 2, 2),

            # --- ADDITIONAL TEAM TASKS ---
            # Overdue Task: Selin was assigned by Ahmet but didn't finish
            ('API Dökümantasyonu', 'Swagger dökümanlarını hazırla', (now - timedelta(days=1)).isoformat(), 
             (now - timedelta(days=3)).isoformat(), 0, None, 'İş', 1, 2, 1),
            
            # Completed: Education
            ('Kitap Oku', 'Atomic Habits 20 sayfa', now.isoformat(), 
             (now - timedelta(days=2)).isoformat(), 1, (now - timedelta(days=1)).isoformat(), 'Eğitim', 3, 2, 2),
             
            # Pending: Finance (Assigned by Ahmet to Selin)
            ('Lisans Yenileme', 'Cloud server ödemesi', (now + timedelta(days=5)).isoformat(), 
             now.isoformat(), 0, None, 'Finans', 2, 2, 1)
        ]
        
        cursor.executemany('''
            INSERT INTO tasks (
                task_title, task_explanation, task_deadline, task_date_created, 
                task_is_completed, task_date_completed, task_category, 
                task_priority, user_id, assigned_by_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tasks)
        conn_task.commit()

    print("✅ Databases populated with custom sample data.")

if __name__ == "__main__":
    create_custom_databases()
    populate_custom_data()
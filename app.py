from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash # Şifre güvenliği
from models import db, User, Task
from datetime import datetime

# --- NLP SEÇİMİ (Yedekli Yapı) ---
from nlp_advanced import get_advanced_category, get_ai_priority
# from nlp_helper import get_task_category, calculate_priority_score

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cok-gizli-anahtar' 

db.init_app(app)

# --- LOGIN KURULUMU ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Giriş yapmamışsa buraya at

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 1. GİRİŞ & KAYIT İŞLEMLERİ ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        # Kullanıcı var mı ve şifre doğru mu?
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Kullanıcı zaten var mı?
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış.')
            return redirect(url_for('register'))
        
        # Şifreyi şifrele (Hash) ve kaydet
        # method parametresini tamamen siliyoruz, varsayılanı kullansın.
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user) # Kayıt olunca direkt giriş yap
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 2. ANASAYFA (KORUMALI) ---

@app.route('/')
@login_required # <-- Sadece giriş yapanlar görebilir
def index():
    # Sadece bana ait görevleri VEYA benim atadıklarımı çekebiliriz. 
    # Şimdilik "Tüm görevleri" gösterelim ki takım çalışması görünsün (Hackathon mantığı)
    tasks = Task.query.order_by(Task.is_completed.asc(), Task.priority_score.desc()).all()
    
    # Görev atamak için TÜM kullanıcıları çek (Dropdown için)
    all_users = User.query.all()
    
    # İstatistikler
    total = Task.query.count()
    completed = Task.query.filter_by(is_completed=True).count()
    pending = total - completed
    
    # Kategori sayıları
    cat_counts = {
        "İş": Task.query.filter_by(category="İş").count(),
        "Okul": Task.query.filter_by(category="Okul").count(),
        "Ev": Task.query.filter_by(category="Ev").count(),
        "Sağlık": Task.query.filter_by(category="Sağlık").count(),
        "Diğer": Task.query.filter(Task.category.notin_(["İş", "Okul", "Ev", "Sağlık"])).count()
    }

    return render_template('index.html', 
                           tasks=tasks, 
                           users=all_users, # Kullanıcı listesini HTML'e gönderiyoruz
                           total=total, completed=completed, pending=pending, 
                           cat_counts=cat_counts,
                           current_user=current_user)

# --- 3. EKLEME (GÖREV ATAMA ÖZELLİĞİ) ---

@app.route('/add', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    date_str = request.form.get('deadline')
    assigned_user_id = request.form.get('assigned_user') # Formdan seçilen kullanıcı ID'si
    
    if date_str:
        deadline_obj = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        deadline_obj = datetime.now()

    # AI İşlemleri
    try:
        ai_category = get_advanced_category(title)
        ai_score = get_ai_priority(title, deadline_obj)
    except:
        ai_category = "Genel"
        ai_score = 0

    # Görev kimin üzerine olacak?
    # Eğer listeden biri seçildiyse ona, seçilmediyse bana (current_user).
    target_user_id = int(assigned_user_id) if assigned_user_id else current_user.id

    new_task = Task(
        title=title, 
        deadline=deadline_obj, 
        category=ai_category, 
        priority_score=ai_score, 
        user_id=target_user_id # <-- DİNAMİK ATAMA
    )
    
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('index'))

# --- DİĞERLERİ AYNI ---
@app.route('/complete/<int:id>')
@login_required
def complete_task(id):
    task = Task.query.get(id)
    task.is_completed = not task.is_completed
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))

# Edit rotasını da login_required yapmayı unutma!
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def edit_task(id):
    task = Task.query.get(id)
    if request.method == 'POST':
        task.title = request.form.get('title')
        # ... diğer edit işlemleri aynı ...
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update.html', task=task)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
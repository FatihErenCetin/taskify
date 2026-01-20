from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# ==========================================
# NLP KATEGORİLENDİRME SİSTEMİ
# ==========================================

# Kategori anahtar kelimeleri
KATEGORILER = {
    'İş': ['toplantı', 'meeting', 'rapor', 'sunum', 'müşteri', 'proje', 'mail', 'email', 'ofis', 'deadline'],
    'Kişisel': ['alışveriş', 'market', 'ev', 'aile', 'arkadaş', 'hediye', 'tatil', 'gezi', 'yemek'],
    'Sağlık': ['doktor', 'hastane', 'ilaç', 'egzersiz', 'spor', 'koşu', 'diyet', 'randevu', 'sağlık', 'ameliyat'],
    'Eğitim': ['ders', 'sınav', 'ödev', 'okul', 'kurs', 'kitap', 'öğren', 'çalış', 'eğitim'],
    'Finans': ['fatura', 'ödeme', 'banka', 'kredi', 'vergi', 'maaş', 'para', 'hesap'],
}

KATEGORI_PUANLAR = {'İş': 3,
                    'Kişisel': 1,
                    'Sağlık': 5,
                    'Eğitim': 2,
                    'Finans': 4,
                    'Genel': 1}

# Öncelik anahtar kelimeleri
ONCELIK_KELIMELERI = {
    'yuksek': ['acil', 'hemen', 'bugün', 'kritik', 'önemli', 'urgent', 'yarın', 'doktor', 'sağlık', 'randevu', 'mutlaka'],
    'dusuk': ['belki', 'bir ara', 'sonra', 'ileride', 'zaman olursa'],
}


def kategori_belirle(metin):
    """Metinden kategori belirle"""
    metin = metin.lower()
    
    for kategori, kelimeler in KATEGORILER.items():
        for kelime in kelimeler:
            if kelime in metin:
                return kategori
    
    return 'Genel'  # Eşleşme yoksa


def oncelik_belirle(metin):
    """Metinden öncelik belirle (1=Yüksek, 2=Normal, 3=Düşük)"""
    metin = metin.lower()
    
    for kelime in ONCELIK_KELIMELERI['yuksek']:
        if kelime in metin:
            return 1  # Yüksek
    
    for kelime in ONCELIK_KELIMELERI['dusuk']:
        if kelime in metin:
            return 3  # Düşük
    
    return 2  # Normal


def oncelik_skoru(task):
        # Öncelik ağırlığı (1=en acil → en düşük skor)
        #print(f"Task Öncelik: {task.oncelik}, Kategori: {task.kategori}")

        if task.son_tarih != None:
            bugun = datetime.utcnow()
            if task.son_tarih:
                kalan_gun = (task.son_tarih - bugun).days + 1  # 0 gün kalmasın

            oncelik_agirlik = task.oncelik * kalan_gun - KATEGORI_PUANLAR[task.kategori]
        else:
            oncelik_agirlik = task.oncelik * 10 - KATEGORI_PUANLAR[task.kategori]
        
        # Tarih ağırlığı (eski tarih = düşük skor = daha önce göster)
        tarih_agirlik = task.olusturma_tarihi.timestamp() if task.olusturma_tarihi else 0
        
        return oncelik_agirlik + (tarih_agirlik / 1000000)


# ============================================
# 🏠 ÇOK SAYFALI FLASK UYGULAMASI
# ============================================
# Her @app.route = Bir sayfa adresi

app = Flask(__name__)


# ==========================================
# VERİTABANI AYARLARI
# ==========================================
# SQLite veritabanı dosyası (proje klasöründe oluşacak)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'gizli-anahtar-degistir-bunu-123!'  # Session için gerekli


# Veritabanı nesnesini oluştur
db = SQLAlchemy(app)


# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Giriş yapılmamışsa yönlendir
login_manager.login_message = 'Bu sayfayı görmek için giriş yapmalısınız.'
login_manager.login_message_category = 'warning'


# ==========================================
# MODEL (TABLO) TANIMLAMASI
# ==========================================

# ==========================================
# KULLANICI TABLOSU
# ==========================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişki: Kullanıcının görevleri
    tasks = db.relationship('Task', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


# Flask-Login için kullanıcı yükleyici
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================================
# GÖREV TABLOSU
# ==========================================
# Bu sınıf = Veritabanındaki "Tasks" tablosu
class Task(db.Model):
    """
    Görev tablosu.
    Her satır = Bir görev.
    """
    __tablename__ = 'tasks'  # Tablo adı
    
    # Sütunlar (kolonlar)
    id = db.Column(db.Integer, primary_key=True)  # Otomatik artan ID
    baslik = db.Column(db.String(200), nullable=False)  # Görev başlığı (zorunlu)
    aciklama = db.Column(db.Text)  # Açıklama (opsiyonel)
    tamamlandi = db.Column(db.Boolean, default=False)  # Tamamlandı mı?
    kategori = db.Column(db.String(50), default='Genel')      # Kategori
    oncelik = db.Column(db.Integer, default=2)                 # (1=Yüksek, 2=Normal, 3=Düşük)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)  # Oluşturulma tarihi
    tamamlanma_tarihi = db.Column(db.DateTime, nullable=True)
    son_tarih = db.Column(db.DateTime, nullable=True)  # Due Date
    # Kullanıcı ilişkisi
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    

    def __repr__(self):
        return f'<Task {self.id}: {self.baslik}>'




# ==========================================
# SAYFALAR (ROUTES)
# ==========================================

# ==========================================
# ANA SAYFA
# ==========================================
# Adres: http://127.0.0.1:5000/
# "/" işareti = web sitesinin ana sayfası
@app.route('/')
def ana_sayfa():
    return render_template('mainpage.html')

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# ==========================================
# HAKKIMDA
# ==========================================
# Adres: http://127.0.0.1:5000/aboutme
@app.route('/aboutme')
def aboutme():
    return render_template('aboutme.html')

# ==========================================
# KAYIT OL
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        
        # Validasyon
        if password != password2:
            flash('Şifreler eşleşmiyor!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Bu email zaten kayıtlı!', 'danger')
            return redirect(url_for('register'))
        
        # Yeni kullanıcı oluştur
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


# ==========================================
# GİRİŞ YAP
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Hoş geldin, {user.username}!', 'success')
            
            # Giriş öncesi gitmek istediği sayfaya yönlendir
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('tasks'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'danger')
    
    return render_template('login.html')
    

# ==========================================
# ÇIKIŞ YAP
# ==========================================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'info')
    return redirect(url_for('mainpage'))


# ==========================================
# GÖREVLER
# ==========================================
# Adres: http://127.0.0.1:5000/tasks
@app.route('/tasks')
@login_required
def tasks():
    # Sadece giriş yapan kullanıcının görevleri
    aktif_gorevler = Task.query.filter_by(user_id=current_user.id, tamamlandi=False).all()

    aktif_gorevler_sirali = sorted(aktif_gorevler, key=oncelik_skoru)
    
    # Tamamlanmış görevler: tamamlanma tarihine göre (en yeni önce)
    tamamlanan_gorevler = Task.query.filter_by(user_id=current_user.id, tamamlandi=True).order_by(Task.tamamlanma_tarihi.desc()).all()

    return render_template('tasklist.html', 
                           aktif_gorevler=aktif_gorevler_sirali,
                           tamamlanan_gorevler=tamamlanan_gorevler)
   

# ==========================================
# GÖREV EKLEME
# ==========================================
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        # Formdan verileri al
        baslik = request.form['baslik']
        aciklama = request.form['aciklama']
        secilen_oncelik = int(request.form['oncelik'])
        secilen_kategori = request.form['kategori']
        son_tarih_str = request.form.get('son_tarih')
        #print(f"Seçilen kategori: {secilen_kategori}, Seçilen öncelik: {secilen_oncelik}")
        
        # NLP ile kategori ve öncelik belirle
        # Kategori
        tam_metin = baslik + ' ' + aciklama
        #kategori = kategori_belirle(tam_metin)
        if secilen_kategori == 'NLP':
            kategori = kategori_belirle(tam_metin)
        else:
            kategori = secilen_kategori
        # Öncelik
        if secilen_oncelik == 0:
            oncelik = oncelik_belirle(tam_metin)
        else:
            oncelik = int(secilen_oncelik)
        
        #print(f"Seçilen kategori: {kategori}, Seçilen öncelik: {oncelik}")

        son_tarih = None
        if son_tarih_str and son_tarih_str.strip():
            try:
                son_tarih = datetime.strptime(son_tarih_str, '%Y-%m-%d')
            except ValueError:
                son_tarih = None

        # Yeni görev oluştur
        yeni_gorev = Task(
            baslik=baslik,
            aciklama=aciklama,
            kategori=kategori,
            oncelik=oncelik,
            son_tarih=son_tarih,
            user_id=current_user.id  # Kullanıcıya bağla
        )

        # Veritabanına ekle
        db.session.add(yeni_gorev)
        db.session.commit()

        flash('Görev başarıyla eklendi!', 'success')
        
        # Görev listesine yönlendir
        return redirect(url_for('tasks'))
    
    # GET ise formu göster
    return render_template('add_task.html')


# ==========================================
# GÖREV SİLME
# ==========================================
@app.route('/delete/<int:id>')
@login_required
def delete_task(id):
    # Görevi bul
    gorev = Task.query.get_or_404(id)
    
    # Yetki kontrolü
    if gorev.user_id != current_user.id:
        flash('Bu göreve erişim yetkiniz yok!', 'danger')
        return redirect(url_for('tasks'))

    # Sil
    db.session.delete(gorev)
    db.session.commit()
    
    flash('Görev silindi.', 'info')

    # Listeye dön
    return redirect(url_for('tasks'))


# ==========================================
# GÖREV TAMAMLANDI İŞARETLE
# ==========================================
@app.route('/complete/<int:id>')
@login_required
def complete_task(id):
    # Görevi bul
    gorev = Task.query.get_or_404(id)
    
    # Yetki kontrolü
    if gorev.user_id != current_user.id:
        flash('Bu göreve erişim yetkiniz yok!', 'danger')
        return redirect(url_for('tasks'))

    # Durumu tersine çevir
    gorev.tamamlandi = not gorev.tamamlandi

    # Tamamlanma tarihini kaydet/sıfırla
    if gorev.tamamlandi:
        gorev.tamamlanma_tarihi = datetime.utcnow()
    else:
        gorev.tamamlanma_tarihi = None
    
    # Kaydet
    db.session.commit()
    
    # Listeye dön
    return redirect(url_for('tasks'))


# ==========================================
# İLETİŞİM
# ==========================================
# Adres: http://127.0.0.1:5000/iletisim
@app.route('/iletisim')
def iletisim():
    pass


# ==========================================
# UYGULAMAYI BAŞLAT
# ==========================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        print('✅ Database and tables created.')

    
    app.run(debug=True, port=5000)


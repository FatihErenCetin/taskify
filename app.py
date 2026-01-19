from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


# ==========================================
# NLP KATEGORİLENDİRME SİSTEMİ
# ==========================================

# Kategori anahtar kelimeleri
KATEGORILER = {
    'İş': ['toplantı', 'meeting', 'rapor', 'sunum', 'müşteri', 'proje', 'mail', 'email', 'ofis', 'deadline'],
    'Kişisel': ['alışveriş', 'market', 'ev', 'aile', 'arkadaş', 'hediye', 'tatil', 'gezi', 'yemek'],
    'Sağlık': ['doktor', 'hastane', 'ilaç', 'egzersiz', 'spor', 'koşu', 'diyet', 'randevu'],
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
        oncelik_agirlik = task.oncelik * 10000 / KATEGORI_PUANLAR[task.kategori]
        
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

# Veritabanı nesnesini oluştur
db = SQLAlchemy(app)



# ==========================================
# MODEL (TABLO) TANIMLAMASI
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
    kategori = db.Column(db.String(50), default='Genel')      # 🆕
    oncelik = db.Column(db.Integer, default=2)                 # 🆕 (1=Yüksek, 2=Normal, 3=Düşük)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)  # Oluşturulma tarihi
    tamamlanma_tarihi = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Task {self.id}: {self.baslik}>'




# ==========================================
# SAYFALAR (ROUTES)
# ==========================================

# ==========================================
# SAYFA 1: ANA SAYFA
# ==========================================
# Adres: http://127.0.0.1:5000/
# "/" işareti = web sitesinin ana sayfası
@app.route('/')
def ana_sayfa():
    return render_template('mainpage.html')


# ==========================================
# SAYFA 2: HAKKIMDA
# ==========================================
# Adres: http://127.0.0.1:5000/aboutme
@app.route('/aboutme')
def aboutme():
    return render_template('aboutme.html')
    


# ==========================================
# SAYFA 3: GÖREVLER
# ==========================================
# Adres: http://127.0.0.1:5000/tasks
@app.route('/tasks')
def tasks():
    aktif_gorevler = Task.query.filter_by(tamamlandi=False).all()

    aktif_gorevler_sirali = sorted(aktif_gorevler, key=oncelik_skoru)
    
    # Tamamlanmış görevler: tamamlanma tarihine göre (en yeni önce)
    tamamlanan_gorevler = Task.query.filter_by(tamamlandi=True).order_by(Task.tamamlanma_tarihi.desc()).all()
    
    return render_template('tasklist.html', 
                           aktif_gorevler=aktif_gorevler_sirali,
                           tamamlanan_gorevler=tamamlanan_gorevler)
   

# ==========================================
# GÖREV EKLEME
# ==========================================
@app.route('/add', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        # Formdan verileri al
        baslik = request.form['baslik']
        aciklama = request.form['aciklama']
        secilen_oncelik = int(request.form['oncelik'])
        secilen_kategori = request.form['kategori']
        #print(f"Seçilen kategori: {secilen_kategori}, Seçilen öncelik: {secilen_oncelik}")
        
        # NLP ile kategori ve öncelik belirle
        tam_metin = baslik + ' ' + aciklama
        #kategori = kategori_belirle(tam_metin)
        if secilen_kategori == 'NLP':
            kategori = kategori_belirle(tam_metin)
        else:
            kategori = secilen_kategori

        if secilen_oncelik == 0:
            oncelik = oncelik_belirle(tam_metin)
        else:
            oncelik = int(secilen_oncelik)
        
        #print(f"Seçilen kategori: {kategori}, Seçilen öncelik: {oncelik}")
        # Yeni görev oluştur
        yeni_gorev = Task(
            baslik=baslik,
            aciklama=aciklama,
            kategori=kategori,
            oncelik=oncelik
        )

        # Veritabanına ekle
        db.session.add(yeni_gorev)
        db.session.commit()
        
        # Görev listesine yönlendir
        return redirect(url_for('tasks'))
    
    # GET ise formu göster
    return render_template('add_task.html')


# ==========================================
# GÖREV SİLME
# ==========================================
@app.route('/delete/<int:id>')
def delete_task(id):
    # Görevi bul
    gorev = Task.query.get_or_404(id)
    
    # Sil
    db.session.delete(gorev)
    db.session.commit()
    
    # Listeye dön
    return redirect(url_for('tasks'))


# ==========================================
# GÖREV TAMAMLANDI İŞARETLE
# ==========================================
@app.route('/complete/<int:id>')
def complete_task(id):
    # Görevi bul
    gorev = Task.query.get_or_404(id)
    
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
# SAYFA 4: İLETİŞİM
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


# Taskify - Akilli Gorev Yoneticisi

NLP destekli akilli gorev yonetim uygulamasi. Yapay zeka ile otomatik kategori ve oncelik belirleme ozelligi sunar.

## Ozellikler

- **Akilli NLP Analizi**: Gorev metinlerini analiz ederek otomatik kategori ve oncelik belirler
- **Uc Analiz Modu**: Manuel, Kural Tabanli veya Gelismis AI secenekleri
- **Kullanici Yonetimi**: Kayit, giris, profil yonetimi
- **Grup Sistemi**: Kullanicilar arasi gorev paylasimi
- **Deadline Takibi**: Son tarih uyarilari ve otomatik onceliklendirme
- **Istatistikler**: Tamamlama oranlari, kategori dagilimi, performans rozetleri
- **Coklu Dil Destegi**: Turkce ve Ingilizce arayuz

## Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| Backend | Flask 3.0, Python 3.12 |
| Veritabani | SQLAlchemy, SQLite |
| Kimlik Dogrulama | Flask-Login |
| Coklu Dil | Flask-Babel |
| NLP | Transformers (Zero-shot), dateparser |
| Frontend | Bootstrap 5.3, Glass Morphism UI |

---

## Kurulum

### 1. Depoyu Klonlayin

```bash
git clone https://github.com/kullanici/taskify.git
cd taskify
```

### 2. Sanal Ortam Olusturun

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Bagimliliklari Yukleyin

```bash
pip install -r requirements.txt
```

**CPU-only PyTorch (daha hafif):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

> **Not:** AI ozellikleri icin `transformers` ve `torch` paketleri gereklidir (~2.5GB disk alani).
> AI istemiyorsaniz `requirements.txt` icindeki ilgili satirlari yorum satirina cevirebilirsiniz.

### 4. Uygulamayi Calistirin

```bash
python app.py
```

Uygulama baslatildiginda veritabani otomatik olarak olusturulur.

Tarayicinizda `http://127.0.0.1:5000` adresine gidin.

---

## Proje Yapisi

```
taskify/
├── app.py                 # Ana Flask uygulamasi
├── config.py              # Yapilandirma ayarlari
├── models.py              # Veritabani modelleri (User, Task, Group)
├── requirements.txt       # Python bagimliliklari
│
├── core/                  # Dusuk seviyeli NLP modulleri
│   ├── predictor.py       # Kategori/oncelik tahmin motoru
│   ├── stats_ai.py        # AI yorum uretici
│   └── README.md          # Core dokumantasyonu
│
├── services/              # Servis katmani
│   ├── nlp_service.py     # NLP servis arayuzu
│   ├── stats_service.py   # Istatistik servisi
│   └── README.md          # Services dokumantasyonu
│
├── templates/             # Jinja2 sablonlari
│   ├── base.html          # Ana sablon
│   ├── home.html          # Ana sayfa
│   ├── tasks.html         # Gorev listesi
│   ├── add_task.html      # Gorev ekleme formu
│   ├── stats.html         # Istatistikler
│   ├── groups.html        # Grup yonetimi
│   ├── login.html         # Giris sayfasi
│   ├── register.html      # Kayit sayfasi
│   └── profile.html       # Profil sayfasi
│
└── static/                # Statik dosyalar (CSS, JS, resimler)
```

---

## Veritabani Yapisi

Uygulama SQLite veritabani kullanir. Asagida tablolar ve iliskileri aciklanmistir:

### ER Diyagrami

```
┌─────────────────────────────────────────────────────────────────┐
│                           USERS                                  │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ Integer      │ Birincil anahtar             │
│ username          │ String(80)   │ Benzersiz kullanici adi      │
│ email             │ String(120)  │ Benzersiz e-posta            │
│ password_hash     │ String(256)  │ Sifreli parola               │
│ role              │ String(20)   │ 'admin' veya 'user'          │
│ created_at        │ DateTime     │ Kayit tarihi                 │
│ preferred_language│ String(5)    │ 'tr' veya 'en'               │
│ ai_features_enabled│ Boolean     │ AI ozellikleri acik/kapali   │
│ ai_comment_cache  │ Text         │ Onbelleklenmis AI yorumu     │
│ ai_comment_updated_at│ DateTime  │ Yorum guncelleme zamani      │
│ stats_hash        │ String(64)   │ Istatistik degisiklik kontrolu│
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   user.tasks    │  │user.created_tasks│ │user.administered_   │
│ (performer)     │  │   (creator)      │  │     groups          │
└────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                           TASKS                                  │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ Integer      │ Birincil anahtar             │
│ title             │ String(150)  │ Gorev basligi                │
│ description       │ Text         │ Detayli aciklama             │
│ deadline          │ DateTime     │ Son tarih                    │
│ created_at        │ DateTime     │ Olusturma tarihi             │
│ completed_at      │ DateTime     │ Tamamlanma tarihi            │
│ is_completed      │ Boolean      │ Tamamlandi mi?               │
│ category          │ String(50)   │ Work/Personal/Health/...     │
│ priority          │ Integer      │ 1=Yuksek, 2=Normal, 3=Dusuk  │
│ category_source   │ String(20)   │ 'manual'/'keyword'/'ai'      │
│ priority_source   │ String(20)   │ 'manual'/'keyword'/'ai'      │
│ deadline_source   │ String(20)   │ 'manual'/'parsed'            │
│ user_id (FK)      │ Integer      │ Gorevi yapacak kullanici     │
│ assigned_by_id(FK)│ Integer      │ Gorevi atayan kullanici      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                           GROUPS                                 │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ Integer      │ Birincil anahtar             │
│ name              │ String(100)  │ Grup adi                     │
│ description       │ Text         │ Grup aciklamasi              │
│ created_at        │ DateTime     │ Olusturma tarihi             │
│ admin_id (FK)     │ Integer      │ Grup yoneticisi              │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GROUP_MEMBERS                               │
│                  (Coka-Cok Iliski Tablosu)                       │
├─────────────────────────────────────────────────────────────────┤
│ group_id (PK, FK) │ Integer      │ Grup ID                      │
│ user_id (PK, FK)  │ Integer      │ Kullanici ID                 │
│ joined_at         │ DateTime     │ Katilim tarihi               │
└─────────────────────────────────────────────────────────────────┘
```

### Tablo Iliskileri

| Iliski | Tip | Aciklama |
|--------|-----|----------|
| User → Tasks | 1:N | Bir kullanicinin birden fazla gorevi olabilir (performer) |
| User → Tasks | 1:N | Bir kullanici birden fazla gorev olusturabilir (creator) |
| User → Groups | 1:N | Bir kullanici birden fazla grubun admini olabilir |
| User ↔ Groups | N:M | Kullanicilar birden fazla gruba uye olabilir (group_members) |
| Group → Users | N:M | Gruplar birden fazla uye icerebilir |

### Kategori Degerleri

| Kategori | Turkce | Aciklama |
|----------|--------|----------|
| Work | Is | Is ile ilgili gorevler |
| Personal | Kisisel | Kisisel isler |
| Health | Saglik | Saglik ile ilgili |
| Education | Egitim | Egitim/ogretim |
| Finance | Finans | Finansal islemler |
| General | Genel | Diger gorevler |

### Oncelik Degerleri

| Deger | Seviye | Anlam |
|-------|--------|-------|
| 1 | Yuksek | Acil, kritik gorevler |
| 2 | Normal | Standart gorevler |
| 3 | Dusuk | Ertelenebilir gorevler |

---

## NLP Analiz Modlari

### 1. Manuel Mod
Kullanici kategori ve onceligi kendisi secer.

### 2. Kural Tabanli Mod (Varsayilan)
Anahtar kelime eslestirmesi ile hizli analiz:
- "acil", "hemen" → Yuksek oncelik
- "toplanti", "rapor" → Is kategorisi
- "doktor", "hastane" → Saglik kategorisi

### 3. Gelismis NLP Mod
Zero-shot siniflandirma modeli (`distilbart-mnli`) kullanir:
- Anlamsal metin analizi
- Turkce/Ingilizce destek
- Ilk kullanim icin model indirmesi gerekir

---

## API Endpointleri

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/` | GET | Ana sayfa |
| `/tasks` | GET | Gorev listesi |
| `/tasks/add` | GET, POST | Gorev ekleme |
| `/tasks/<id>/complete` | POST | Gorevi tamamla |
| `/tasks/<id>/delete` | POST | Gorevi sil |
| `/stats` | GET | Istatistikler |
| `/groups` | GET | Grup listesi |
| `/groups/create` | GET, POST | Grup olustur |
| `/groups/<id>` | GET | Grup detayi |
| `/login` | GET, POST | Giris |
| `/register` | GET, POST | Kayit |
| `/logout` | GET | Cikis |
| `/profile` | GET, POST | Profil |
| `/set-language/<lang>` | GET | Dil degistir |

---

## Yapilandirma

`config.py` dosyasinda asagidaki ayarlar mevcuttur:

```python
# Veritabani
SQLALCHEMY_DATABASE_URI = 'sqlite:///taskify.db'

# AI Ozellikleri
AI_ENABLED = True              # AI ozelliklerini ac/kapat
AI_COMMENT_ENABLED = True      # AI yorum uretimini ac/kapat

# Dil Destegi
BABEL_DEFAULT_LOCALE = 'tr'
BABEL_SUPPORTED_LOCALES = ['tr', 'en']
```

---

## Gelistirme

### Testleri Calistirma

```bash
pip install pytest pytest-flask
pytest
```

### Kod Formatlama

```bash
pip install black flake8
black .
flake8 .
```

---


## Katkida Bulunma

1. Fork yapin
2. Feature branch olusturun (`git checkout -b feature/yeni-ozellik`)
3. Degisikliklerinizi commit edin (`git commit -m 'Yeni ozellik eklendi'`)
4. Branch'i push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request acin

# Taskify - Uygulama Akış Dokümantasyonu

Bu belge, Taskify akıllı görev yönetim uygulamasının tüm işleyişini detaylı şekilde açıklamaktadır.

---

## 📑 İçindekiler

1. [Genel Mimari](#-genel-mimari)
2. [Kullanıcı Akışları](#-kullanıcı-akışları)
3. [NLP Analiz Akışı](#-nlp-analiz-akışı)
4. [Görev Yönetimi Akışı](#-görev-yönetimi-akışı)
5. [Grup Yönetimi Akışı](#-grup-yönetimi-akışı)
6. [İstatistik ve AI Yorum Akışı](#-i̇statistik-ve-ai-yorum-akışı)
7. [Veritabanı İlişkileri](#-veritabanı-i̇lişkileri)
8. [API Endpoint Akışları](#-api-endpoint-akışları)

---

## 🏗️ Genel Mimari

```mermaid
flowchart TB
    subgraph Frontend["🎨 Frontend Layer"]
        Templates["Jinja2 Templates"]
        Static["Static Files<br>(CSS/JS)"]
    end
    
    subgraph App["🚀 Application Layer"]
        Flask["Flask App<br>(app.py)"]
        Routes["Route Handlers"]
        ContextProc["Context Processors"]
    end
    
    subgraph Services["⚙️ Service Layer"]
        NLPSvc["NLP Service<br>(nlp_service.py)"]
        StatsSvc["Stats Service<br>(stats_service.py)"]
    end
    
    subgraph Core["🧠 Core Layer"]
        Predictor["Predictor<br>(predictor.py)"]
        StatsAI["Stats AI<br>(stats_ai.py)"]
    end
    
    subgraph Data["💾 Data Layer"]
        Models["SQLAlchemy Models<br>(models.py)"]
        SQLite["SQLite Database"]
    end
    
    subgraph External["🌐 External Dependencies"]
        Transformers["HuggingFace<br>Transformers"]
        DateParser["DateParser"]
        Translator["Google Translator"]
    end
    
    Frontend --> App
    App --> Services
    Services --> Core
    Core --> External
    App --> Data
    Data --> SQLite
```

### Katman Açıklamaları

| Katman | Dosyalar | Sorumluluk |
|--------|----------|------------|
| **Frontend** | `templates/`, `static/` | HTML şablonları, CSS stilleri, JavaScript |
| **Application** | `app.py`, `config.py` | Flask routing, request handling, session yönetimi |
| **Service** | `services/nlp_service.py`, `services/stats_service.py` | İş mantığı, AI toggle kontrolü |
| **Core** | `core/predictor.py`, `core/stats_ai.py` | NLP algoritmaları, AI modelleri |
| **Data** | `models.py`, `instance/taskify.db` | Veritabanı modelleri ve ilişkileri |

---

## 👤 Kullanıcı Akışları

### Kayıt Akışı

```mermaid
sequenceDiagram
    participant U as Kullanıcı
    participant B as Tarayıcı
    participant F as Flask App
    participant DB as Veritabanı
    
    U->>B: /register sayfasına git
    B->>F: GET /register
    F->>B: register.html formu
    
    U->>B: Form doldur (username, email, password)
    B->>F: POST /register
    
    F->>F: Şifre eşleşme kontrolü
    F->>DB: Username kontrolü
    F->>DB: Email kontrolü
    
    alt Validasyon Başarılı
        F->>F: set_password() ile hash oluştur
        F->>DB: Yeni User kaydet
        F->>B: Redirect → /login + Flash mesaj
    else Validasyon Başarısız
        F->>B: Redirect → /register + Hata mesajı
    end
```

**Kayıt Süreci Detayları:**

1. **Form Validasyonu**
   - Şifre ve onay kontrolü
   - Kullanıcı adı benzersizlik kontrolü
   - E-posta benzersizlik kontrolü

2. **Güvenlik**
   - `werkzeug.security.generate_password_hash()` ile şifre hashleme
   - PBKDF2-SHA256 algoritması

3. **Varsayılan Ayarlar**
   - `role`: 'user'
   - `preferred_language`: Mevcut dil tercihi
   - `ai_features_enabled`: True

---

### Giriş Akışı

```mermaid
sequenceDiagram
    participant U as Kullanıcı
    participant F as Flask App
    participant LM as Login Manager
    participant DB as Veritabanı
    
    U->>F: POST /login (username, password)
    F->>DB: User.query.filter_by(username)
    
    alt Kullanıcı Bulundu
        F->>F: check_password() ile doğrula
        alt Şifre Doğru
            F->>LM: login_user(user)
            LM->>F: Session token oluştur
            F->>U: Redirect → /tasks
        else Şifre Yanlış
            F->>U: Flash hata mesajı
        end
    else Kullanıcı Bulunamadı
        F->>U: Flash hata mesajı
    end
```

**Oturum Yönetimi:**

- Flask-Login extension ile session yönetimi
- `@login_required` decorator ile koruma
- Otomatik yönlendirme (next parameter)

---

## 🧠 NLP Analiz Akışı

### Akış Diyagramı

```mermaid
flowchart TD
    Start["📝 Görev Metni Girişi"]
    Mode{"Analiz Modu?"}
    
    Manual["MANUEL MOD<br>Kullanıcı seçimi"]
    Rule["KURAL TABANLI MOD<br>Keyword eşleştirme"]
    AI["GELİŞMİŞ AI MOD<br>Zero-shot sınıflandırma"]
    
    KW1["detect_category_keywords()"]
    KW2["calculate_priority_keywords()"]
    
    AIClass["detect_category_ai()"]
    Translate["Metni İngilizce'ye çevir"]
    ZeroShot["HuggingFace Zero-Shot<br>distilbart-mnli-12-1"]
    
    DateExtract{"Tarih Çıkarma?"}
    DateParser["dateparser.search_dates()"]
    SimpleDate["extract_date_simple()"]
    
    Result["📊 Analiz Sonucu<br>category, priority, deadline"]
    
    Start --> Mode
    
    Mode -->|manual| Manual
    Mode -->|rule| Rule
    Mode -->|ai| AI
    
    Manual --> Result
    
    Rule --> KW1
    KW1 --> KW2
    KW2 --> DateExtract
    
    AI --> KW1
    KW1 -->|Bulunamadı| AIClass
    AIClass --> Translate
    Translate --> ZeroShot
    ZeroShot --> KW2
    
    DateExtract -->|AI Aktif| DateParser
    DateExtract -->|AI Pasif| SimpleDate
    DateParser --> Result
    SimpleDate --> Result
```

### Analiz Modları Detayı

#### 1. Manuel Mod
```
Kullanıcı tüm değerleri kendisi seçer
├── Kategori: Dropdown'dan seçim
├── Öncelik: 1-2-3 seçimi
└── Deadline: Tarih picker
```

#### 2. Kural Tabanlı Mod (Varsayılan)

**Kategori Tespiti:**

| Kategori | Türkçe Anahtar Kelimeler | İngilizce Anahtar Kelimeler |
|----------|--------------------------|----------------------------|
| **Work** | toplantı, rapor, sunum, proje, ofis, kod | meeting, report, project, code, deadline |
| **Personal** | alışveriş, ev, aile, arkadaş, tatil | shopping, home, family, friend, vacation |
| **Health** | doktor, hastane, ilaç, egzersiz, spor | doctor, hospital, medicine, gym, exercise |
| **Education** | ders, sınav, ödev, okul, kurs, kitap | lesson, exam, homework, school, course |
| **Finance** | fatura, ödeme, banka, vergi, maaş | bill, payment, bank, tax, salary |

**Öncelik Hesaplama:**

```python
# Yüksek Öncelik Kelimeleri (pozitif puan)
'acil': 50, 'hemen': 40, 'kritik': 50, 'bugün': 45
'urgent': 50, 'critical': 50, 'asap': 45, 'important': 30

# Düşük Öncelik Kelimeleri (negatif puan)
'belki': -20, 'sonra': -15, 'acele yok': -25
'maybe': -20, 'later': -15, 'no rush': -25

# Deadline Aciliyeti
gecikmiş: +70, bugün: +60, yarın: +45, 3 gün içinde: +30

# Sonuç
puan >= 40 → Yüksek (1)
puan >= 15 → Normal (2)
puan < 15  → Düşük (3)
```

#### 3. Gelişmiş AI Mod

```mermaid
flowchart LR
    Text["Görev Metni<br>(TR/EN)"]
    Trans["GoogleTranslator<br>auto → en"]
    Model["distilbart-mnli-12-1<br>Zero-Shot Classification"]
    Labels["Candidate Labels:<br>Work, School, Home,<br>Health, Social, Shopping"]
    Map["Label Mapping:<br>School→Education<br>Home→Personal"]
    Result["Final Category"]
    
    Text --> Trans
    Trans --> Model
    Labels --> Model
    Model --> Map
    Map --> Result
```

**AI Model Detayları:**
- Model: `valhalla/distilbart-mnli-12-1`
- Yöntem: Zero-shot sınıflandırma
- Confidence Threshold: 0.4
- Çeviri: `deep_translator.GoogleTranslator`

---

### Tarih Çıkarma Akışı

```mermaid
flowchart TD
    Input["'Yarın toplantı var'"]
    Check{"dateparser<br>yüklü mü?"}
    
    Advanced["search_dates()<br>Gelişmiş Parser"]
    Simple["extract_date_simple()<br>Basit Parser"]
    
    TRKeywords["Türkçe:<br>bugün, yarın, haftaya,<br>pazartesi, salı..."]
    ENKeywords["İngilizce:<br>today, tomorrow,<br>next week, monday..."]
    
    Result["datetime objesi"]
    
    Input --> Check
    Check -->|Evet| Advanced
    Check -->|Hayır| Simple
    Simple --> TRKeywords
    Simple --> ENKeywords
    TRKeywords --> Result
    ENKeywords --> Result
    Advanced --> Result
```

---

## ✅ Görev Yönetimi Akışı

### Görev Ekleme Akışı

```mermaid
flowchart TD
    Start["🆕 /tasks/add"]
    Form["Görev Formu<br>title, description, deadline"]
    Mode{"analysis_mode?"}
    
    Manual["Manuel<br>Kullanıcı değerleri"]
    Rule["Kural Tabanlı<br>NLPService.analyze_task()"]
    AI["AI Analiz<br>use_ai=True"]
    
    Override{"Kullanıcı<br>override var mı?"}
    
    Assign{"Atama<br>Kontrolü"}
    Self["Kendine ata<br>user_id = current_user"]
    Other["Başkasına ata<br>Grup üyesi kontrolü"]
    
    Create["Task Oluştur"]
    Save["DB'ye Kaydet"]
    Redirect["→ /tasks"]
    
    Start --> Form
    Form --> Mode
    
    Mode -->|manual| Manual
    Mode -->|rule| Rule
    Mode -->|ai| AI
    
    Rule --> Override
    AI --> Override
    Manual --> Assign
    Override -->|Evet| Assign
    Override -->|Hayır| Assign
    
    Assign --> Self
    Assign --> Other
    
    Self --> Create
    Other --> Create
    
    Create --> Save
    Save --> Redirect
```

### Görev Durumu Değişikliği

```mermaid
stateDiagram-v2
    [*] --> Aktif: Görev Oluşturuldu
    
    Aktif --> Tamamlandı: toggle_task()
    Tamamlandı --> Aktif: toggle_task()
    
    Aktif --> Gecikmiş: deadline < now
    Gecikmiş --> Tamamlandı: toggle_task()
    
    Aktif --> [*]: delete_task()
    Tamamlandı --> [*]: delete_task()
    
    note right of Aktif
        is_completed = False
        completed_at = None
    end note
    
    note right of Tamamlandı
        is_completed = True
        completed_at = datetime.utcnow()
    end note
```

### Görev Listesi Sıralama

```python
# Aktif görevler sıralaması
active_tasks_sorted = sorted(
    active_tasks,
    key=lambda t: (
        t.priority,           # 1. Öncelik (1 > 2 > 3)
        t.deadline or max     # 2. Deadline (yakın olanlar önce)
    )
)
```

### Deadline Uyarıları

| Durum | Renk | İkon | Mesaj Anahtarı |
|-------|------|------|----------------|
| Gecikmiş | `danger` | ⚠️ exclamation-triangle | `deadline_overdue` |
| Bugün | `warning` | 🔥 fire | `deadline_today` |
| Yarın | `warning` | ⏰ clock-fill | `deadline_tomorrow` |
| 2-3 gün | `info` | 🕐 clock | `deadline_soon` |
| Bu hafta | `secondary` | 📅 calendar-week | `deadline_this_week` |

---

## 👥 Grup Yönetimi Akışı

### Grup İlişkileri

```mermaid
erDiagram
    USER ||--o{ GROUP : "admin olarak yönetir"
    USER }o--o{ GROUP : "üye olarak katılır"
    USER ||--o{ TASK : "gerçekleştirir"
    USER ||--o{ TASK : "atar"
    
    USER {
        int id PK
        string username
        string role
    }
    
    GROUP {
        int id PK
        string name
        int admin_id FK
    }
    
    TASK {
        int id PK
        string title
        int user_id FK
        int assigned_by_id FK
    }
```

### Görev Atama Akışı

```mermaid
sequenceDiagram
    participant Admin as Grup Admini
    participant App as Flask App
    participant DB as Veritabanı
    participant Member as Grup Üyesi
    
    Admin->>App: /tasks/add (assign_to=member_id)
    
    App->>DB: Admin'in gruplarını getir
    App->>DB: Valid üye ID'lerini kontrol et
    
    alt Geçerli Üye
        App->>DB: Task oluştur<br>user_id=member_id<br>assigned_by_id=admin_id
        App->>Admin: Başarı mesajı
        
        Note over DB,Member: Görev üyenin listesinde görünür
    else Geçersiz Üye
        App->>DB: Task oluştur<br>user_id=admin_id
        App->>Admin: Kendine atandı
    end
```

---

## 📊 İstatistik ve AI Yorum Akışı

### İstatistik Hesaplama Pipeline

```mermaid
flowchart TD
    Start["/stats endpoint"]
    
    subgraph Stats["StatsService.get_user_stats()"]
        GetTasks["Tüm görevleri getir"]
        Calc["Hesaplamalar"]
        
        Rate["Tamamlama Oranı<br>completed/total × 100"]
        Focus["Odak Skoru<br>4 - avg_priority"]
        Categories["Kategori Analizi<br>Counter()"]
        AvgTime["Ort. Tamamlama Süresi"]
        Streak["Streak Hesaplama"]
    end
    
    subgraph Badge["get_performance_badge()"]
        BadgeCalc["Tamamlama oranına göre rozet"]
        Badges["Başlangıç < Bronz < Gümüş < Altın < Platin"]
    end
    
    subgraph AI["get_ai_comment()"]
        CacheCheck{"Önbellek<br>geçerli mi?"}
        Hash["Stats hash hesapla"]
        Generate["Yorum üret"]
        Save["Önbelleğe kaydet"]
    end
    
    Start --> Stats
    GetTasks --> Calc
    Calc --> Rate & Focus & Categories & AvgTime & Streak
    
    Stats --> Badge
    Badge --> BadgeCalc --> Badges
    
    Stats --> AI
    AI --> CacheCheck
    CacheCheck -->|Evet| Return["Önbellekten"]
    CacheCheck -->|Hayır| Hash
    Hash --> Generate
    Generate --> Save
```

### AI Yorum Üretimi

```mermaid
flowchart TD
    Input["Kullanıcı İstatistikleri"]
    
    Check{"AI Model<br>yüklü mü?"}
    
    subgraph AIGen["AI Yorum Üretici"]
        Model["flan-t5-small"]
        Prompt["Context: User has X%<br>completion rate..."]
        Gen["Text Generation"]
        Clean["Tekrar eden cümleleri temizle"]
        Trans["Türkçe'ye çevir"]
    end
    
    subgraph Template["Şablon Tabanlı"]
        RateCheck{"Tamamlama<br>oranı?"}
        NoTask["Henüz görev eklenmemiş..."]
        Low["Tamamlama oranınız düşük..."]
        Medium["İyi gidiyorsunuz..."]
        High["Mükemmel performans!"]
        Perfect["Olağanüstü!"]
    end
    
    Input --> Check
    Check -->|Evet| AIGen
    Check -->|Hayır| Template
    
    AIGen --> Model --> Prompt --> Gen --> Clean --> Trans
    
    Template --> RateCheck
    RateCheck -->|0| NoTask
    RateCheck -->|<30%| Low
    RateCheck -->|<70%| Medium
    RateCheck -->|<100%| High
    RateCheck -->|100%| Perfect
```

### Önbellekleme Stratejisi

```python
# Cache kontrol akışı
current_hash = md5(f"{total}_{completed}_{rate}")

if user.ai_comment_cache and user.stats_hash == current_hash:
    return user.ai_comment_cache  # Önbellekten

# Yeni yorum üret
comment = generate_comment(stats)

# Önbelleğe kaydet
user.ai_comment_cache = comment
user.stats_hash = current_hash
user.ai_comment_updated_at = datetime.utcnow()
db.session.commit()
```

---

## 💾 Veritabanı İlişkileri

### ER Diyagramı

```mermaid
erDiagram
    USERS ||--o{ TASKS : "performs"
    USERS ||--o{ TASKS : "assigns"
    USERS ||--o{ GROUPS : "administers"
    USERS }o--o{ GROUPS : "member of"
    
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role "admin|user"
        datetime created_at
        string preferred_language "tr|en"
        boolean ai_features_enabled
        text ai_comment_cache
        datetime ai_comment_updated_at
        string stats_hash
    }
    
    TASKS {
        int id PK
        string title
        text description
        datetime deadline
        datetime created_at
        datetime completed_at
        boolean is_completed
        string category "Work|Personal|Health|Education|Finance|General"
        int priority "1=Yüksek, 2=Normal, 3=Düşük"
        string category_source "manual|keyword|ai"
        string priority_source "manual|keyword|ai"
        string deadline_source "manual|parsed"
        int user_id FK
        int assigned_by_id FK
    }
    
    GROUPS {
        int id PK
        string name
        text description
        datetime created_at
        int admin_id FK
    }
    
    GROUP_MEMBERS {
        int group_id PK_FK
        int user_id PK_FK
        datetime joined_at
    }
```

### İlişki Özeti

| İlişki | Tip | Açıklama |
|--------|-----|----------|
| User → Tasks (performer) | 1:N | `user.tasks` - Kullanıcının yapacağı görevler |
| User → Tasks (creator) | 1:N | `user.created_tasks` - Kullanıcının atadığı görevler |
| User → Groups (admin) | 1:N | `user.administered_groups` - Yönettiği gruplar |
| User ↔ Groups (member) | N:M | `group_members` tablosu ile |

---

## 🔌 API Endpoint Akışları

### Gerçek Zamanlı Analiz API

```mermaid
sequenceDiagram
    participant UI as JavaScript
    participant API as /api/analyze
    participant NLP as NLPService
    participant AI as AI Model
    
    UI->>API: POST { text, description }
    
    API->>NLP: analyze_task(text, desc, use_ai)
    
    alt AI Aktif
        NLP->>AI: Zero-shot sınıflandırma
        AI->>NLP: {category, confidence}
    else AI Pasif
        NLP->>NLP: Keyword eşleştirme
    end
    
    NLP->>API: {category, priority, deadline}
    
    API->>API: Lokalize labels ekle
    API->>UI: JSON Response
    
    Note over UI: Form alanlarını güncelle
```

**Request:**
```json
POST /api/analyze
{
    "text": "Acil toplantı yarın",
    "description": "Müşteri ile görüşme"
}
```

**Response:**
```json
{
    "category": "Work",
    "category_display": "İş",
    "category_source": "keyword",
    "priority": 1,
    "priority_display": "Yüksek",
    "priority_source": "keyword",
    "deadline": "2025-01-22",
    "deadline_formatted": "2025-01-22",
    "deadline_source": "simple_parser"
}
```

### Tüm API Endpoints

| Endpoint | Method | Açıklama | Auth |
|----------|--------|----------|------|
| `/api/analyze` | POST | Gerçek zamanlı görev analizi | ✅ |
| `/api/stats` | GET | Kullanıcı istatistikleri | ✅ |
| `/api/nlp-status` | GET | NLP servis durumu | ✅ |

---

## 🌍 Dil Desteği Akışı

```mermaid
flowchart TD
    Request["HTTP Request"]
    
    Check1{"Session'da<br>dil var mı?"}
    Check2{"Kullanıcı<br>giriş yapmış mı?"}
    Check3{"Kullanıcı<br>tercihi var mı?"}
    
    Session["session['language']"]
    UserPref["user.preferred_language"]
    Default["Varsayılan: 'tr'"]
    
    Result["get_locale() sonucu"]
    Babel["Flask-Babel çeviriler"]
    
    Request --> Check1
    Check1 -->|Evet| Session
    Check1 -->|Hayır| Check2
    Check2 -->|Evet| Check3
    Check2 -->|Hayır| Default
    Check3 -->|Evet| UserPref
    Check3 -->|Hayır| Default
    
    Session --> Result
    UserPref --> Result
    Default --> Result
    
    Result --> Babel
```

### Dil Değiştirme

```
GET /set-language/<language>
├── Session güncelle
├── Kullanıcı tercihi güncelle (giriş yapmışsa)
└── Önceki sayfaya yönlendir
```

---

## 🔧 Yapılandırma Akışı

```mermaid
flowchart LR
    Env["Environment<br>Variables"]
    Config["config.py"]
    
    subgraph Configs["Configuration Classes"]
        Base["Config<br>(Base)"]
        Dev["DevelopmentConfig"]
        Prod["ProductionConfig"]
        Test["TestingConfig"]
    end
    
    App["Flask App"]
    
    Env --> Config
    Config --> Configs
    Configs --> App
    
    Base --> Dev & Prod & Test
```

### Önemli Yapılandırma Ayarları

| Ayar | Varsayılan | Açıklama |
|------|------------|----------|
| `AI_ENABLED` | True | Tüm AI özelliklerini aç/kapat |
| `AI_CATEGORY_ENABLED` | True | Kategori tahminini aç/kapat |
| `AI_PRIORITY_ENABLED` | True | Öncelik tahminini aç/kapat |
| `AI_COMMENT_ENABLED` | True | AI yorum üretimini aç/kapat |
| `AI_DATE_PARSER_ENABLED` | True | Gelişmiş tarih ayrıştırıcı |
| `AI_CONFIDENCE_THRESHOLD` | 0.4 | Minimum AI güven skoru |
| `BABEL_DEFAULT_LOCALE` | 'tr' | Varsayılan dil |
| `BABEL_SUPPORTED_LOCALES` | ['tr', 'en'] | Desteklenen diller |

---

## 📝 Özet

Taskify, modern bir görev yönetimi uygulamasıdır ve şu temel akışları içerir:

1. **Kullanıcı Akışı**: Kayıt → Giriş → Profil Yönetimi
2. **Görev Akışı**: Oluştur → (NLP Analizi) → Listele → Tamamla/Sil
3. **Grup Akışı**: Grup Oluştur → Üye Ekle → Görev Ata
4. **İstatistik Akışı**: Veri Topla → Hesapla → AI Yorum → Rozet Ver
5. **API Akışı**: Gerçek zamanlı analiz için AJAX desteği

Uygulama, hibrit NLP yaklaşımı (keyword + AI) ile akıllı görev kategorizasyonu ve önceliklendirme sağlar, çoklu dil desteği sunar ve performans rozetleri ile kullanıcı motivasyonunu artırır.

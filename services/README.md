# Services Modulu

Bu dizin, Taskify uygulamasinin servis katmanini (service layer) icerir. Servisler, `core/` modulleri ile `app.py` arasinda bir koprovu gorevi gorur. Tum is mantigi ve veri islemleri bu katmanda yurutulur.

## Dosya Yapisi

```
services/
├── README.md           # Bu dosya
├── nlp_service.py      # NLP servis katmani
└── stats_service.py    # Istatistik servis katmani
```

---

## Neden Servis Katmani?

```
┌──────────────────────────────────────────────────────────────┐
│                        app.py (Routes)                       │
│  - HTTP isteklerini karsilar                                 │
│  - Form verilerini alir                                      │
│  - Template render eder                                      │
└──────────────────────────────┬───────────────────────────────┘
                               │ Servis metodlarini cagirir
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      services/ (Servisler)                   │
│  - Is mantigi                                                │
│  - Config yonetimi                                           │
│  - Caching                                                   │
│  - Hata yonetimi                                             │
└──────────────────────────────┬───────────────────────────────┘
                               │ Core fonksiyonlari cagirir
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        core/ (Cekirdek)                      │
│  - Dusuk seviyeli algoritmalar                               │
│  - AI model yonetimi                                         │
│  - Veri isleme                                               │
└──────────────────────────────────────────────────────────────┘
```

**Avantajlari:**
- `app.py` temiz ve okunakli kalir
- Is mantigi tek bir yerde toplanir
- Birim testleri daha kolay yazilir
- Bagimlilik yonetimi (dependency injection) kolaylasir

---

## nlp_service.py - NLP Servis Katmani

[core/predictor.py](../core/README.md#predictorpy---nlp-tahmin-motoru) modulunu sarmalayan yuksek seviyeli servis.

### NLPService Sinifi

Tum metodlar `@staticmethod` olarak tanimlanmistir. Ornek olusturmaya gerek yoktur.

```python
from services.nlp_service import NLPService

# Dogrudan cagri
result = NLPService.analyze_task("Acil toplanti")
```

---

### Metodlar

#### `analyze_task(title: str, description: str = "", use_ai: bool = None) -> dict`

Gorev metnini analiz eder ve tahminleri dondurur.

**Parametreler:**

| Parametre | Tip | Varsayilan | Aciklama |
|-----------|-----|------------|----------|
| `title` | str | (zorunlu) | Gorev basligi |
| `description` | str | "" | Gorev aciklamasi |
| `use_ai` | bool | None | AI kullanimi (None = config'den al) |

**Donus Degeri:**
```python
{
    'category': 'Work',           # Tahmin edilen kategori
    'priority': 1,                # Oncelik (1=Yuksek, 2=Normal, 3=Dusuk)
    'deadline': datetime(...),    # Cikarilan tarih (varsa)
    'category_source': 'keyword', # Kaynak: 'keyword', 'ai', 'default'
    'priority_source': 'keyword', # Kaynak: 'keyword'
    'deadline_source': 'simple_parser'  # Kaynak: 'ai_parser', 'simple_parser', 'none'
}
```

**Calisma Mantigi:**

```
1. use_ai parametresi kontrol edilir
   ├─ use_ai = True  → analyze_task_ai() cagirilir
   ├─ use_ai = False → analyze_task_keywords() cagirilir
   └─ use_ai = None  → Config'den AI_ENABLED ve AI_CATEGORY_ENABLED kontrol edilir

2. extract_deadline() ile tarih cikarilir
   ├─ AI_DATE_PARSER_ENABLED = True → dateparser kullanilir
   └─ AI_DATE_PARSER_ENABLED = False → basit parser kullanilir

3. Sonuclar birlestirilerek dondurulur
```

**Ornek Kullanim:**
```python
# Kural tabanli analiz
result = NLPService.analyze_task(
    "Yarin acil fatura odeme",
    use_ai=False
)
# → {'category': 'Finance', 'priority': 1, ...}

# AI tabanli analiz
result = NLPService.analyze_task(
    "Prepare the quarterly report",
    use_ai=True
)
# → {'category': 'Work', 'priority': 2, 'category_source': 'ai', ...}
```

---

#### `extract_deadline(text: str, use_ai: bool = None) -> tuple[datetime | None, str]`

Metinden tarih bilgisi cikarir.

**Donus Degeri:**
```python
(datetime_object, source_string)
# Ornekler:
(datetime(2024, 1, 22), 'ai_parser')      # dateparser ile bulundu
(datetime(2024, 1, 22), 'simple_parser')  # basit parser ile bulundu
(None, 'none')                            # tarih bulunamadi
```

**Calisma Mantigi:**
```
1. AI_DATE_PARSER_ENABLED = True ise:
   └─ extract_date_from_text() (dateparser) dene
      └─ Basariliysa → (tarih, 'ai_parser') dondur

2. Hala tarih bulunamadiysa:
   └─ extract_date_simple() (kelime eslestirme) dene
      └─ Basariliysa → (tarih, 'simple_parser') dondur

3. Hicbiri basarisizsa → (None, 'none')
```

---

#### `get_task_alert(deadline) -> dict | None`

Deadline icin UI uyari bilgisi dondurur.

```python
>>> NLPService.get_task_alert(datetime(2024, 1, 22))
{
    'msg_key': 'deadline_tomorrow',
    'color': 'warning',
    'icon': 'clock-fill',
    'days': 1
}
```

> **Not:** Dogrudan [core/predictor.py#get_deadline_alert](../core/README.md#get_deadline_alertdeadline--dict--none) fonksiyonunu cagirir.

---

#### `get_category_display(category: str, language: str = 'tr') -> str`

Kategori isminin yerellestirilmis halini dondurur.

```python
>>> NLPService.get_category_display('Work', 'tr')
'Is'

>>> NLPService.get_category_display('Health', 'en')
'Health'
```

**Desteklenen Kategoriler:**

| Dahili Isim | Turkce | Ingilizce |
|-------------|--------|-----------|
| Work | Is | Work |
| Personal | Kisisel | Personal |
| Health | Saglik | Health |
| Education | Egitim | Education |
| Finance | Finans | Finance |
| General | Genel | General |

---

#### `get_priority_display(priority: int, language: str = 'tr') -> str`

Oncelik degerinin yerellestirilmis halini dondurur.

```python
>>> NLPService.get_priority_display(1, 'tr')
'Yuksek'

>>> NLPService.get_priority_display(3, 'en')
'Low'
```

**Oncelik Degerleri:**

| Deger | Turkce | Ingilizce |
|-------|--------|-----------|
| 1 | Yuksek | High |
| 2 | Normal | Normal |
| 3 | Dusuk | Low |

---

#### `get_status() -> dict`

NLP servisinin durum bilgisini dondurur.

```python
>>> NLPService.get_status()
{
    'dateparser': True,              # dateparser paketi kurulu mu
    'translator': True,              # deep_translator paketi kurulu mu
    'transformers': False,           # transformers paketi kurulu mu
    'ai_classifier': False,          # AI model yuklendi mi
    'ai_enabled_config': True,       # Config: AI_ENABLED
    'ai_category_enabled': True,     # Config: AI_CATEGORY_ENABLED
    'ai_date_parser_enabled': True   # Config: AI_DATE_PARSER_ENABLED
}
```

---

#### `get_all_categories() -> list[str]`

Tum kategorilerin listesini dondurur.

```python
>>> NLPService.get_all_categories()
['Work', 'Personal', 'Health', 'Education', 'Finance', 'General']
```

---

#### `get_all_priorities() -> list[dict]`

Tum oncelik seviyelerini dondurur.

```python
>>> NLPService.get_all_priorities()
[
    {'value': 1, 'key': 'high'},
    {'value': 2, 'key': 'normal'},
    {'value': 3, 'key': 'low'}
]
```

---

## stats_service.py - Istatistik Servis Katmani

Kullanici istatistiklerini hesaplayan ve AI yorumlari ureten servis.

### StatsService Sinifi

```python
from services.stats_service import StatsService

stats = StatsService.get_user_stats(user_id=1)
```

---

### Metodlar

#### `get_user_stats(user_id: int) -> dict`

Kullanici icin kapsamli istatistikler hesaplar.

**Donus Degeri:**
```python
{
    'total_tasks': 25,                    # Toplam gorev sayisi
    'completed_tasks': 18,                # Tamamlanan gorev sayisi
    'active_tasks': 5,                    # Aktif gorev sayisi
    'overdue_tasks': 2,                   # Gecikmis gorev sayisi
    'completion_rate': 72.0,              # Tamamlama orani (%)
    'focus_score': 2.3,                   # Odak skoru (1-3, yuksek = iyi)
    'most_planned_category': 'Work',      # En cok planlanan kategori
    'most_completed_category': 'Work',    # En cok tamamlanan kategori
    'avg_completion_time': '2.5h',        # Ortalama tamamlama suresi
    'tasks_by_category': {                # Kategoriye gore dagilim
        'Work': 10, 'Personal': 8, ...
    },
    'tasks_by_priority': {                # Oncelik dagilimi
        'high': 5, 'normal': 15, 'low': 5
    },
    'weekly_completed': 7,                # Son 7 gunde tamamlanan
    'streak_days': 3                      # Ardisik gun serisi
}
```

**Hesaplama Detaylari:**

| Metrik | Formul |
|--------|--------|
| `completion_rate` | `(completed / total) * 100` |
| `focus_score` | `4 - avg(priority of completed tasks)` |
| `streak_days` | Bugunden geriye dogru ardisik tamamlama gunleri |
| `avg_completion_time` | `avg(completed_at - created_at)` |

---

#### `get_ai_comment(user_id: int, language: str = 'tr', use_ai: bool = None) -> str`

Kullanici icin kisisellestirilmis motivasyon yorumu uretir.

**Caching Mekanizmasi:**

```
1. Kullanicinin mevcut istatistiklerinin hash'i hesaplanir
   └─ Hash = md5(total_tasks + completed_tasks + completion_rate)

2. Cache kontrolu:
   ├─ user.stats_hash == current_hash → Cache gecerli, kayitli yorumu dondur
   └─ Hash farkliysa → Yeni yorum uret

3. Yorum uretimi:
   ├─ AI aktif ve kullanilabilir → generate_ai_comment()
   └─ Degilse → generate_template_comment()

4. Yeni yorum cache'lenir:
   └─ user.ai_comment_cache = yorum
   └─ user.stats_hash = current_hash
   └─ user.ai_comment_updated_at = now()
```

**Ornek:**
```python
>>> StatsService.get_ai_comment(user_id=1, language='tr')
"Harika gidiyorsunuz! %75 tamamlama oraniyla Is kategorisinde cok basarilisiniz."
```

---

#### `invalidate_ai_comment_cache(user_id: int)`

Kullanicinin AI yorum cache'ini gecersiz kilar.

```python
# Gorev tamamlandiginda cache'i temizle
StatsService.invalidate_ai_comment_cache(current_user.id)
```

> **Not:** Bu fonksiyon gorev eklendiginde/tamamlandiginda cagrilmalidir.

---

#### `get_performance_badge(user_id: int, language: str = 'tr') -> dict`

Kullanicinin performans rozetini dondurur.

```python
>>> StatsService.get_performance_badge(user_id=1, language='tr')
{
    'name': 'Altin',
    'color': 'warning',
    'icon': 'trophy'
}
```

> **Not:** [core/stats_ai.py#get_performance_badge](../core/README.md#get_performance_badgecompletion_rate-float-language-str--tr--dict) fonksiyonunu kullanir.

---

#### `get_category_breakdown(user_id: int) -> list[dict]`

Kategori bazli detayli istatistikleri dondurur (grafikler icin).

```python
>>> StatsService.get_category_breakdown(user_id=1)
[
    {
        'category': 'Work',
        'total': 10,
        'completed': 8,
        'completion_rate': 80.0
    },
    {
        'category': 'Personal',
        'total': 5,
        'completed': 3,
        'completion_rate': 60.0
    },
    ...
]
```

---

#### `get_weekly_progress(user_id: int, weeks: int = 4) -> list[dict]`

Haftalik ilerleme verilerini dondurur (grafikler icin).

```python
>>> StatsService.get_weekly_progress(user_id=1, weeks=4)
[
    {'week_start': '2024-01-01', 'week_label': 'W1', 'created': 5, 'completed': 3},
    {'week_start': '2024-01-08', 'week_label': 'W2', 'created': 8, 'completed': 6},
    {'week_start': '2024-01-15', 'week_label': 'W3', 'created': 4, 'completed': 7},
    {'week_start': '2024-01-22', 'week_label': 'W4', 'created': 3, 'completed': 2}
]
```

---

#### `get_upcoming_deadlines(user_id: int, days: int = 7) -> list[Task]`

Yaklasan deadline'lari olan gorevleri dondurur.

```python
>>> tasks = StatsService.get_upcoming_deadlines(user_id=1, days=7)
>>> for task in tasks:
...     print(f"{task.title}: {task.deadline}")
"Rapor teslimi: 2024-01-23"
"Fatura odeme: 2024-01-25"
```

---

#### `is_ai_available() -> bool`

AI ozelliklerinin kullanilabilir olup olmadigini kontrol eder.

```python
>>> StatsService.is_ai_available()
False  # transformers kurulu degil
```

---

## app.py ile Entegrasyon

### NLPService Kullanimi

```python
# app.py - add_task route

@app.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        analysis_mode = request.form.get('analysis_mode', 'rule')

        if analysis_mode == 'manual':
            # Manuel mod - NLP kullanilmaz
            category = request.form.get('category')
            priority = int(request.form.get('priority'))
        else:
            # Otomatik mod
            use_ai = (analysis_mode == 'ai')
            analysis = NLPService.analyze_task(
                title=request.form['title'],
                description=request.form.get('description', ''),
                use_ai=use_ai
            )
            category = analysis['category']
            priority = analysis['priority']
```

### StatsService Kullanimi

```python
# app.py - profile route

@app.route('/profile')
@login_required
def profile():
    stats = StatsService.get_user_stats(current_user.id)
    comment = StatsService.get_ai_comment(current_user.id)
    badge = StatsService.get_performance_badge(current_user.id)

    return render_template('profile.html',
        stats=stats,
        comment=comment,
        badge=badge
    )
```

---

## Akis Diagrami - Gorev Ekleme

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Kullanici Formu                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Baslik      │  │ Aciklama    │  │ Analiz Modu                 │ │
│  │ ─────────── │  │ ─────────── │  │ ○ Manuel                    │ │
│  │ Acil rapor  │  │ Q4 sonuclari│  │ ● Kural Tabanli             │ │
│  │             │  │             │  │ ○ Gelismis NLP              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │ POST /tasks/add
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           app.py                                    │
│                                                                     │
│  analysis_mode = request.form.get('analysis_mode')                  │
│  if analysis_mode == 'rule':                                        │
│      analysis = NLPService.analyze_task(title, desc, use_ai=False)  │
│                                                                     │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NLPService.analyze_task()                      │
│                                                                     │
│  1. use_ai=False → analyze_task_keywords() cagir                    │
│  2. extract_deadline() ile tarih cikar                              │
│  3. Sonuclari birlesir ve dondur                                    │
│                                                                     │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   core/predictor.py                                 │
│                                                                     │
│  analyze_task_keywords("Acil rapor Q4 sonuclari")                   │
│  ├─ detect_category_keywords() → "Work" (rapor kelimesi)            │
│  └─ calculate_priority_keywords() → 1 (acil kelimesi)               │
│                                                                     │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Sonuc                                       │
│  {                                                                  │
│      'category': 'Work',                                            │
│      'priority': 1,                                                 │
│      'deadline': None,                                              │
│      'category_source': 'keyword',                                  │
│      'priority_source': 'keyword'                                   │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Iliskili Moduller

- **[core/predictor.py](../core/README.md#predictorpy---nlp-tahmin-motoru)** - NLP algoritmalari
- **[core/stats_ai.py](../core/README.md#stats_aipy---ai-yorum-uretici)** - AI yorum uretici
- **[models.py](../models.py)** - Veritabani modelleri
- **[config.py](../config.py)** - Uygulama konfigurasyonu

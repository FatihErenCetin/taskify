# Core Modulu

Bu dizin, Taskify uygulamasinin temel NLP ve AI islevlerini iceren dusuk seviyeli (low-level) modulleri barindirir. Bu moduller dogrudan kullanilmaz; bunun yerine `services/` katmani uzerinden erisim saglanir.

## Dosya Yapisi

```
core/
├── README.md          # Bu dosya
├── predictor.py       # NLP tahmin motoru
└── stats_ai.py        # AI yorum uretici
```

---

## predictor.py - NLP Tahmin Motoru

Gorev metinlerini analiz ederek kategori, oncelik ve tarih cikarimi yapan hibrit NLP motorudur.

### Bagimliliklari

| Paket | Zorunlu mu? | Kullanim |
|-------|-------------|----------|
| `dateparser` | Hayir | Dogal dil tarih cikarimi |
| `deep_translator` | Hayir | Turkce → Ingilizce ceviri |
| `transformers` | Hayir | AI siniflandirma modeli |

> **Not:** Tum bagimliliklar opsiyoneldir. Kurulu degilse sistem otomatik olarak basit yontemlere gecer (graceful degradation).

### Sabitler ve Sozlukler

#### CATEGORY_KEYWORDS
Kural tabanli kategori tespiti icin anahtar kelime sozlugu.

```python
CATEGORY_KEYWORDS = {
    'Work': ['toplanti', 'rapor', 'meeting', 'project', ...],
    'Personal': ['alisveris', 'market', 'shopping', 'home', ...],
    'Health': ['doktor', 'hastane', 'doctor', 'gym', ...],
    'Education': ['ders', 'sinav', 'lesson', 'exam', ...],
    'Finance': ['fatura', 'odeme', 'bill', 'payment', ...],
}
```

Her kategori hem Turkce hem Ingilizce kelimeler icerir.

#### PRIORITY_KEYWORDS
Oncelik hesaplama icin puan tablosu.

```python
PRIORITY_KEYWORDS = {
    'high': {
        'acil': 50, 'hemen': 40, 'kritik': 50,      # Turkce
        'urgent': 50, 'critical': 50, 'asap': 45,   # Ingilizce
    },
    'low': {
        'belki': -20, 'sonra': -15,                  # Turkce
        'maybe': -20, 'later': -15,                  # Ingilizce
    }
}
```

### Fonksiyonlar

#### `_clean_text(text: str) -> str`
Metni normalize eder: kucuk harfe cevirir, noktalama isaretlerini kaldirir.

```python
>>> _clean_text("Acil TOPLANTI!")
"acil toplanti"
```

#### `_get_ai_classifier() -> pipeline | None`
AI siniflandirma modelini lazy-load eder. Model sadece ilk cagrildiginda yuklenir.

```python
# Kullanilan model: valhalla/distilbart-mnli-12-1
# Tip: Zero-shot classification
```

#### `_translate_to_english(text: str) -> str`
Metni Ingilizceye cevirir (AI modeli icin). `deep_translator` kurulu degilse orijinal metni dondurur.

---

### Kural Tabanli Analiz Fonksiyonlari

#### `detect_category_keywords(text: str) -> str | None`
Anahtar kelime eslestirmesi ile kategori tespit eder.

**Calisma Mantigi:**
1. Metin `_clean_text()` ile normalize edilir
2. Her kategori icin kelime listesi taranir
3. Ilk eslesen kategori dondurulur
4. Hicbir eslesme yoksa `None` dondurulur

```python
>>> detect_category_keywords("Yarin doktor randevusu")
"Health"

>>> detect_category_keywords("Bir seyler yap")
None
```

#### `calculate_priority_keywords(text: str, deadline: datetime = None) -> int`
Metin ve deadline bilgisine gore oncelik puani hesaplar.

**Puanlama Sistemi:**

| Kaynak | Puan Araligi |
|--------|--------------|
| Yuksek oncelik kelimeleri | +30 ile +50 |
| Dusuk oncelik kelimeleri | -15 ile -25 |
| Deadline gecmis | +70 |
| Deadline bugun | +60 |
| Deadline yarin | +45 |
| Deadline 3 gun icinde | +30 |
| Deadline 7 gun icinde | +15 |

**Sonuc Eslestirmesi:**

| Toplam Puan | Oncelik |
|-------------|---------|
| >= 40 | 1 (Yuksek) |
| >= 15 | 2 (Normal) |
| < 15 | 3 (Dusuk) |

```python
>>> calculate_priority_keywords("Acil toplanti!")
1  # Yuksek

>>> calculate_priority_keywords("Belki sonra yaparim")
3  # Dusuk
```

#### `analyze_task_keywords(text: str, deadline: datetime = None) -> dict`
Sadece kural tabanli analiz yapar (AI kullanmaz).

```python
>>> analyze_task_keywords("Acil fatura odeme")
{
    'category': 'Finance',
    'priority': 1,
    'category_source': 'keyword',
    'priority_source': 'keyword'
}
```

---

### AI Tabanli Analiz Fonksiyonlari

#### `detect_category_ai(text: str, confidence_threshold: float = 0.4) -> str | None`
Zero-shot classification modeli ile kategori tespit eder.

**Calisma Mantigi:**
1. Metin Ingilizceye cevrilir (`_translate_to_english`)
2. Model metni onceden tanimli etiketlere gore siniflandirir
3. En yuksek skorlu etiket alinir
4. Skor esik degerinin (`0.4`) altindaysa `None` dondurulur

**Model Etiketleri:**
```python
AI_CANDIDATE_LABELS = ['Work', 'School', 'Home', 'Health', 'Social', 'Shopping', 'Finance']
```

**Etiket Donusumu:**
```python
AI_LABELS_MAP = {
    'Work': 'Work',
    'School': 'Education',   # School → Education
    'Home': 'Personal',      # Home → Personal
    'Social': 'Personal',    # Social → Personal
    'Shopping': 'Personal',  # Shopping → Personal
    ...
}
```

#### `analyze_task_ai(text: str, deadline: datetime = None) -> dict`
Hibrit analiz yapar: Once keyword, sonra AI.

**Calisma Mantigi:**
```
1. detect_category_keywords() cagir
   └─ Eslesme varsa → kategori bul, source='keyword'
   └─ Eslesme yoksa → devam et

2. detect_category_ai() cagir
   └─ Confidence >= 0.4 → kategori bul, source='ai'
   └─ Confidence < 0.4 → devam et

3. Hicbiri basarisizsa → 'General', source='default'

4. calculate_priority_keywords() her zaman kullanilir
```

```python
>>> analyze_task_ai("Make a presentation for the client")
{
    'category': 'Work',
    'priority': 2,
    'category_source': 'ai',      # AI tarafindan belirlendi
    'priority_source': 'keyword'
}
```

---

### Tarih Cikarma Fonksiyonlari

#### `extract_date_from_text(text: str, prefer_future: bool = True) -> datetime | None`
`dateparser` kutuphanesi ile dogal dil tarih cikarimi yapar.

**Desteklenen Formatlar:**
- "yarin saat 3'te"
- "next Monday"
- "2 gun sonra"
- "15 Ocak 2024"

```python
>>> extract_date_from_text("Yarin toplanti var")
datetime(2024, 1, 22, 23, 59, 59)  # Bugün 21 Ocak ise
```

#### `extract_date_simple(text: str) -> datetime | None`
Basit kelime eslestirmesi ile tarih cikarimi (fallback).

**Desteklenen Kelimeler:**

| Kelime | Sonuc |
|--------|-------|
| "bugun" / "today" | Bugunun tarihi |
| "yarin" / "tomorrow" | Yarinin tarihi |
| "haftaya" / "next week" | 7 gun sonra |
| "pazartesi" / "monday" | Sonraki Pazartesi |
| ... | (tum gun isimleri) |

```python
>>> extract_date_simple("Cuma gunu teslim et")
datetime(2024, 1, 26, 23, 59, 59)  # Sonraki Cuma
```

---

### UI Yardimci Fonksiyonlari

#### `get_deadline_alert(deadline) -> dict | None`
Deadline icin UI uyari bilgisi uretir.

**Donus Degerleri:**

| Durum | msg_key | color | icon |
|-------|---------|-------|------|
| Gecmis | deadline_overdue | danger | exclamation-triangle-fill |
| Bugun | deadline_today | warning | fire |
| Yarin | deadline_tomorrow | warning | clock-fill |
| 2-3 gun | deadline_soon | info | clock |
| 4-7 gun | deadline_this_week | secondary | calendar-week |
| 7+ gun | None | - | - |

```python
>>> get_deadline_alert(datetime(2024, 1, 22))  # Yarin
{
    'msg_key': 'deadline_tomorrow',
    'color': 'warning',
    'icon': 'clock-fill',
    'days': 1
}
```

#### `get_nlp_status() -> dict`
NLP bilesenlerinin kullanilabilirlik durumunu dondurur.

```python
>>> get_nlp_status()
{
    'dateparser': True,
    'translator': True,
    'transformers': False,
    'ai_classifier': False
}
```

---

## stats_ai.py - AI Yorum Uretici

Kullanici istatistiklerine dayali kisisellestirilmis motivasyon yorumlari uretir.

### Bagimliliklari

| Paket | Kullanim |
|-------|----------|
| `transformers` | Metin uretimi (FLAN-T5) |
| `deep_translator` | Ingilizce → Turkce ceviri |

### Fonksiyonlar

#### `_get_comment_generator() -> pipeline | None`
FLAN-T5 modelini lazy-load eder.

```python
# Kullanilan model: google/flan-t5-small
# Tip: Text-to-text generation
```

#### `generate_ai_comment(stats: dict, language: str = 'tr') -> str`
AI ile kisisellestirilmis yorum uretir.

**Girdi (stats):**
```python
{
    'completion_rate': 75.0,
    'total_tasks': 20,
    'completed_tasks': 15,
    'most_completed_category': 'Work'
}
```

**Calisma Mantigi:**
1. Istatistiklerden prompt olusturulur
2. FLAN-T5 modeli ile yorum uretilir
3. Tekrar eden cumleler temizlenir
4. Turkce istenmisse ceviri yapilir

```python
>>> generate_ai_comment(stats, 'tr')
"Harika bir ilerleme! Is gorevlerinde cok basarilisin."
```

#### `generate_template_comment(stats: dict, language: str = 'tr') -> str`
Sablon tabanli yorum uretir (AI kullanilamiyorsa fallback).

**Performans Seviyeleri:**

| Tamamlama Orani | Sablon |
|-----------------|--------|
| Gorev yok | "Henuz gorev eklenmemis..." |
| < 30% | "Tamamlama oraniniz %X. Daha kucuk gorevlerle baslamayi deneyin!" |
| 30-70% | "Iyi gidiyorsunuz! %X tamamlama oraniyla..." |
| 70-100% | "Mukemmel performans! %X tamamlama oraniyla..." |
| 100% | "Olaganustu! Tum gorevlerinizi tamamladiniz..." |

#### `get_performance_badge(completion_rate: float, language: str = 'tr') -> dict`
Tamamlama oranina gore rozet bilgisi dondurur.

| Oran | Rozet | Renk | Ikon |
|------|-------|------|------|
| < 20% | Baslangic | secondary | seedling |
| 20-40% | Bronz | warning | medal |
| 40-60% | Gumus | info | award |
| 60-80% | Altin | warning | trophy |
| >= 80% | Platin | primary | gem |

#### `is_ai_available() -> bool`
AI yorum uretiminin kullanilabilir olup olmadigini kontrol eder.

---

## Akis Diagrami

```
                    ┌─────────────────────┐
                    │   NLPService.       │
                    │   analyze_task()    │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              │ use_ai parametresine gore     │
              └───────────────┬───────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ use_ai = False  │  │ use_ai = True   │  │ AI unavailable  │
│                 │  │                 │  │                 │
│ analyze_task_   │  │ analyze_task_   │  │ analyze_task_   │
│ keywords()      │  │ ai()            │  │ keywords()      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │           ┌────────┴────────┐           │
         │           │                 │           │
         │           ▼                 ▼           │
         │  ┌─────────────┐   ┌─────────────┐     │
         │  │ keyword     │   │ AI          │     │
         │  │ detection   │   │ detection   │     │
         │  └──────┬──────┘   └──────┬──────┘     │
         │         │                 │            │
         │         └────────┬────────┘            │
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Sonuc:          │
                   │ - category      │
                   │ - priority      │
                   │ - source info   │
                   └─────────────────┘
```

---

## Iliskili Moduller

- **[services/nlp_service.py](../services/README.md#nlpservice)** - Bu modulu sarmalayan servis katmani
- **[services/stats_service.py](../services/README.md#statsservice)** - stats_ai.py'yi kullanan istatistik servisi

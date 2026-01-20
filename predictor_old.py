import string
import datetime
from dateparser.search import search_dates 
from deep_translator import GoogleTranslator 
from transformers import pipeline 

# --- CONFIGURATION & CONSTANTS ---

# Rule-based keywords for fast categorization.
# If we find one of these words, we skip the AI model to save resources.
CATEGORY_KEYWORDS = {
    "İş": ["toplantı", "sunum", "rapor", "mail", "kod", "yazılım", "bug", "müşteri", "analiz", "proje", "ofis", "deploy"],
    "Okul": ["sınav", "ders", "ödev", "vize", "final", "tez", "makale", "araştırma", "kütüphane", "hoca", "kampüs"],
    "Ev": ["market", "fatura", "kira", "temizlik", "yemek", "alışveriş", "tamir", "su", "elektrik", "bulaşık", "kedi"],
    "Sağlık": ["doktor", "ilaç", "hastane", "randevu", "diş", "spor", "diyet", "göz", "kontrol", "yürüyüş"],
    "Sosyal": ["sinema", "tiyatro", "konser", "buluşma", "kahve", "arkadaş", "doğum günü", "tatil"]
}

# Keywords to calculate task urgency.
PRIORITY_KEYWORDS = {"acil": 50, "önemli": 40, "kritik": 40, "hemen": 30, "yetişmeli": 30, "yarın": 20}

# Mapping English labels (from the AI model) to Turkish categories.
LABELS_MAP = {"Work": "İş", "School": "Okul", "Home": "Ev", "Health": "Sağlık", "Social": "Sosyal", "Shopping": "Ev"}
CANDIDATE_LABELS = list(LABELS_MAP.keys())

# Load the AI Model (Zero-Shot Classification).
# Wrapped in try-except to prevent the app from crashing if the model fails to load.
try:
    # Using a distilled model for speed/performance balance
    classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")
    AI_AVAILABLE = True
except:
    # Fallback to rule-based only if AI fails
    AI_AVAILABLE = False

# --- HELPER FUNCTIONS ---

def clean_text(text):
    """
    Basic preprocessing: lowercase and remove punctuation.
    """
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

def extract_date(text):
    """
    Extracts date entities from the text using 'dateparser'.
    Prioritizes future dates (e.g., 'Monday' means 'Next Monday').
    """
    try:
        results = search_dates(text, languages=['tr'], settings={'PREFER_DATES_FROM': 'future'})
        if results: return results[0][1] # Return the first found date
    except: return None
    return None

def get_category_hybrid(text):
    """
    Hybrid approach: Checks keywords first, then uses AI if needed.
    """
    text_clean = clean_text(text)
    
    # Step 1: Check for keywords (Fast & Cheap)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(key in text_clean for key in keywords): return category
    
    # Step 2: Use AI Model (Slower but Smarter)
    if AI_AVAILABLE:
        try:
            # Model works better with English, so we translate first
            translated = GoogleTranslator(source='auto', target='en').translate(text)
            result = classifier(translated, CANDIDATE_LABELS)
            
            # Only accept the result if confidence score is high enough (>0.4)
            if result['scores'][0] > 0.4: return LABELS_MAP[result['labels'][0]]
        except: pass
        
    return "Genel" # Default fallback category

def calculate_priority(text, deadline_date):
    """
    Calculates a priority score based on urgent words and time remaining.
    """
    score = 0
    text_clean = clean_text(text)
    
    # Add points for urgent words
    for word, points in PRIORITY_KEYWORDS.items():
        if word in text_clean: score += points
        
    # Add points if the deadline is close
    if deadline_date:
        days_left = (deadline_date - datetime.datetime.now()).days
        if days_left < 1: score += 60   # Critical (Less than 24h)
        elif days_left < 3: score += 40 # High urgency
        elif days_left < 7: score += 20 # Medium urgency
    
    # Map score to label
    if score >= 60: return "Yüksek"
    elif score >= 30: return "Orta"
    else: return "Düşük"

# --- BACKEND INTERFACE FUNCTIONS ---

def analyze_task(text):
    """
    Main entry point for the Backend (app.py).
    Takes the raw text and returns structured data (Category, Priority, Deadline).
    """
    detected_date = extract_date(text)
    category = get_category_hybrid(text)
    priority = calculate_priority(text, detected_date)
    
    return {
        "category": category,
        "priority": priority,
        "deadline": detected_date
    }

def get_deadline_alert(deadline_date):
    """
    Helper for the Frontend/HTML.
    Returns bootstrap color codes and messages based on remaining time.
    """
    if not deadline_date: return None
    
    # Ensure deadline is a datetime object
    if isinstance(deadline_date, str):
        try: deadline_date = datetime.datetime.strptime(deadline_date, '%Y-%m-%d %H:%M:%S.%f')
        except: return None

    days = (deadline_date - datetime.datetime.now()).days
    
    if days < 0: return {"msg": "Süre Doldu!", "color": "danger", "icon": "exclamation-triangle"}
    elif days == 0: return {"msg": "Bugün Son Gün!", "color": "warning", "icon": "fire"}
    elif days < 3: return {"msg": f"{days} gün kaldı", "color": "info", "icon": "clock"}
    return None
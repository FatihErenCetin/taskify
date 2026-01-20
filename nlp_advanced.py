from transformers import pipeline
from deep_translator import GoogleTranslator # <--- YENİ EKLEME
import datetime

print("AI Modeli (ve Çevirmen) Hazırlanıyor...")

# Modelimiz (Zaten inmişti, tekrar inmez)
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# ETİKETLER (İngilizce tutuyoruz çünkü çeviriyle soracağız)
LABELS_MAP = {
    "Work": "İş",
    "School": "Okul",
    "Home": "Ev",
    "Health": "Sağlık",
    "Social": "Sosyal",
    "Urgent": "Acil"
}

CANDIDATE_LABELS = list(LABELS_MAP.keys())

def get_advanced_category(text):
    try:
        # 1. HİLE BURADA: Metni önce İngilizceye çeviriyoruz!
        # Model Türkçede zorlanıyor ama İngilizcede profesör.
        english_text = GoogleTranslator(source='auto', target='en').translate(text)
        print(f"TR: {text} -> EN: {english_text}") # Terminalde çeviriyi gör
        
        # 2. İngilizce metni modele sor
        result = classifier(english_text, CANDIDATE_LABELS)
        
        top_label = result['labels'][0]
        confidence = result['scores'][0]
        
        print(f"AI Analizi: '{top_label}' (%{confidence*100:.1f} güven)")
        
        return LABELS_MAP[top_label]
        
    except Exception as e:
        print(f"Hata (Fallback): {e}")
        return "Genel"

def get_ai_priority(text, deadline_obj):
    score = 0
    
    # Tarih Hesabı (Aynı kalıyor)
    if deadline_obj:
        days_left = (deadline_obj - datetime.datetime.now()).days
        if days_left < 1: score += 50
        elif days_left < 3: score += 30
    
    # AI Aciliyet Analizi (Bunu da İngilizce yapalım, daha hassas olsun)
    try:
        english_text = GoogleTranslator(source='auto', target='en').translate(text)
        urgency_result = classifier(english_text, ["Urgent", "Normal"])
        
        if urgency_result['labels'][0] == "Urgent" and urgency_result['scores'][0] > 0.6:
            print("AI Panik Sezdi! (+40 Puan)")
            score += 40
            
    except:
        pass # Çeviri hatası olursa puan ekleme, devam et.
        
    return min(score, 100)

# --- TEST ALANI ---
if __name__ == "__main__":
    test_sentences = [
        "Yarın hastaneye gidip doktora görüneceğim.", # Artık bunu bilecek!
        "Patronla toplantı set etmem lazım",
        "Akşama makarna yapacağım",
    ]
    
    for sent in test_sentences:
        print(f"\nTest Ediliyor: {sent}")
        cat = get_advanced_category(sent)
        print(f"Sonuç Kategori: {cat}")
from datetime import datetime

# 1. BİLGİ BANKASI (Sözlükler)
CATEGORY_KEYWORDS = {
    "İş": ["toplantı", "sunum", "rapor", "mail", "kod", "yazılım", "bug", "müşteri", "analiz", "proje", "ofis"],
    "Okul": ["sınav", "ders", "ödev", "vize", "final", "tez", "makale", "araştırma", "kütüphane", "hoca"],
    "Ev": ["market", "fatura", "kira", "temizlik", "yemek", "alışveriş", "tamir", "su", "elektrik", "bulaşık"],
    "Sağlık": ["doktor", "ilaç", "hastane", "randevu", "diş", "spor", "diyet", "göz", "kontrol"]
}

PRIORITY_KEYWORDS = {
    "acil": 50,
    "önemli": 40,
    "kritik": 40,
    "hemen": 30,
    "yetişmeli": 30,
    "yarın": 20,
    "son": 20
}

# 2. FONKSİYON: Kategoriyi Bul
def get_task_category(text):
    text = text.lower()
    best_category = "Genel" # Hiçbir şey bulamazsa bunu dönecek
    max_count = 0
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        match_count = 0
        for word in keywords:
            if word in text:
                match_count += 1
        
        # Eğer bu kategoriden daha fazla kelime bulduysak, yeni lider bu
        if match_count > max_count:
            max_count = match_count
            best_category = category
            
    return best_category

# 3. FONKSİYON: Öncelik Puanı Hesapla (0-100 arası)
def calculate_priority_score(text, deadline_obj):
    text = text.lower()
    score = 0
    
    # A) Kelimelerden gelen puan
    for word, points in PRIORITY_KEYWORDS.items():
        if word in text:
            score += points

    # B) Tarihten gelen puan (Zaman daraldıkça puan artar)
    if deadline_obj:
        # Şu an ile son tarih arasındaki fark
        remaining = deadline_obj - datetime.now()
        days_left = remaining.days
        
        if days_left < 1:   # 1 günden az kaldıysa (Çok Acil)
            score += 50
        elif days_left < 3: # 3 günden az kaldıysa (Orta Acil)
            score += 30
        elif days_left < 7: # 1 haftadan az kaldıysa
            score += 10
            
    # Puanı 100 ile sınırla (100'ü geçmesin)
    return min(score, 100)

# --- Test Alanı ---
# Bu dosyayı tek başına çalıştırırsan aşağıdaki test çalışır.
if __name__ == "__main__":
    ornek_metin = "Yarın sabah acil proje toplantısı var"
    ornek_tarih = datetime.now() # Şimdiki zamanı bitiş tarihi gibi varsaydık
    
    kat = get_task_category(ornek_metin)
    puan = calculate_priority_score(ornek_metin, ornek_tarih)
    
    print(f"Metin: {ornek_metin}")
    print(f"Tahmin Edilen Kategori: {kat}")
    print(f"Hesaplanan Öncelik Puanı: {puan}")
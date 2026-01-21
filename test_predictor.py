from predictor import analyze_task, get_deadline_alert
import datetime

# Test edilecek örnek cümleler
test_senaryolari = [
    "Yarın sabah acil proje toplantısı var",         # 1. Full Paket (Tarih + Kategori + Öncelik)
    "Marketten süt, yumurta ve deterjan al",         # 2. Sadece Kategori (Tarih yok)
    "İstatistik ödevini 2 gün sonra teslim et",      # 3. Tarihe dayalı öncelik testi
    "Diş doktoruna randevu almam lazım",             # 4. Sağlık kategorisi
    "Server connection error fix",                   # 5. İngilizce / AI testi
    "Arkadaşlarla haftasonu sinemaya git"            # 6. Sosyal aktivite
]

print("\n" + "="*50)
print("🚀 TASKIFY AI MODÜLÜ - SİSTEM TESTİ")
print("="*50)

for i, metin in enumerate(test_senaryolari, 1):
    print(f"\n🔹 SENARYO {i}: '{metin}'")
    print("-" * 40)

    # 1. Fonksiyonu Çağır (Backend simülasyonu)
    try:
        sonuc = analyze_task(metin)
    except Exception as e:
        print(f"❌ HATA: Analiz yapılamadı! ({e})")
        continue

    # 2. Sonuçları Yazdır
    print(f"   📂 Kategori:  {sonuc['category']}")
    print(f"   🔥 Öncelik:   {sonuc['priority']}")

    # 3. Tarih ve Uyarı Kontrolü
    if sonuc['deadline']:
        # Tarihi okunabilir formata çevir
        tarih_str = sonuc['deadline'].strftime('%d-%m-%Y %H:%M')
        print(f"   📅 Tarih:     {tarih_str}")
        
        # Frontend uyarısını test et
        uyari = get_deadline_alert(sonuc['deadline'])
        if uyari:
            print(f"   🔔 Bildirim:  [{uyari['color'].upper()}] {uyari['msg']}") 
        else:
            print("   🔕 Bildirim:  Gerek yok (Süre uzun)")
    else:
        print("   📅 Tarih:     Tespit Edilemedi (Normal)")

print("\n" + "="*50)
print("✅ TEST TAMAMLANDI.\n")
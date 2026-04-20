import requests
import time
import json
import os
from datetime import datetime

# --- AYARLAR ---
TELEGRAM_TOKEN = "8154362550:AAGVasRA_XzbNVRvUhhw08IhDoY4P2emCLE"
CHAT_ID = "7229573083"
KONTROL_ARALIGI = 120  # saniye (2 dakikada bir kontrol)

# Takip edilecek haber türleri (KAP'taki başlıklara göre)
TAKIP_EDILEN_TURLER = [
    "Kamuyu Aydınlatma Platformu Duyurusu",
    "Pay Alım Satım Bildirimi"
]

GORULMUS_HABERLER_DOSYASI = "gorulmus_haberler.json"
KAP_API_URL = "https://www.kap.org.tr/tr/api/disclosures"

# --- YARDIMCI FONKSİYONLAR ---

def gorulmus_haberleri_yukle():
    if os.path.exists(GORULMUS_HABERLER_DOSYASI):
        with open(GORULMUS_HABERLER_DOSYASI, "r") as f:
            return set(json.load(f))
    return set()

def gorulmus_haberleri_kaydet(haberler):
    # Sadece son 1000 haberi tut (dosya şişmesin)
    liste = list(haberler)[-1000:]
    with open(GORULMUS_HABERLER_DOSYASI, "w") as f:
        json.dump(liste, f)

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    veri = {
        "chat_id": CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML"
    }
    try:
        yanit = requests.post(url, data=veri, timeout=10)
        yanit.raise_for_status()
    except Exception as e:
        print(f"Telegram mesaj hatası: {e}")

def kap_haberlerini_cek():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"
    }
    try:
        yanit = requests.get(KAP_API_URL, headers=headers, timeout=15)
        yanit.raise_for_status()
        return yanit.json()
    except Exception as e:
        print(f"KAP veri çekme hatası: {e}")
        return []

def haber_turu_eslesiyor(haber_turu):
    if not haber_turu:
        return False
    for tur in TAKIP_EDILEN_TURLER:
        if tur.lower() in haber_turu.lower():
            return True
    return False

def haberleri_isle(haberler, gorulmus):
    yeni_bildirimler = []
    for haber in haberler:
        haber_id = str(haber.get("disclosureIndex") or haber.get("id") or "")
        if not haber_id or haber_id in gorulmus:
            continue

        haber_turu = haber.get("disclosureType") or haber.get("subject") or ""
        if haber_turu_eslesiyor(haber_turu):
            sirket = haber.get("companyName") or haber.get("title") or "Bilinmeyen Şirket"
            tarih = haber.get("publishDate") or haber.get("date") or ""
            url = f"https://www.kap.org.tr/tr/Bildirim/{haber_id}"

            mesaj = (
                f"📢 <b>KAP BİLDİRİMİ</b>\n\n"
                f"🏢 <b>Şirket:</b> {sirket}\n"
                f"📋 <b>Tür:</b> {haber_turu}\n"
                f"🕐 <b>Tarih:</b> {tarih}\n"
                f"🔗 <a href='{url}'>Bildirimi Görüntüle</a>"
            )
            yeni_bildirimler.append((haber_id, mesaj))

    return yeni_bildirimler

# --- ANA DÖNGÜ ---

def main():
    print("KAP Bot başlatıldı ✅")
    telegram_mesaj_gonder("✅ <b>KAP Bot aktif!</b>\n\nTakip edilen türler:\n• Kamuyu Aydınlatma Platformu Duyurusu\n• Pay Alım Satım Bildirimi")

    gorulmus = gorulmus_haberleri_yukle()

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] KAP kontrol ediliyor...")
            haberler = kap_haberlerini_cek()

            if haberler:
                yeniler = haberleri_isle(haberler, gorulmus)
                for haber_id, mesaj in yeniler:
                    telegram_mesaj_gonder(mesaj)
                    gorulmus.add(haber_id)
                    print(f"Yeni bildirim gönderildi: {haber_id}")
                gorulmus_haberleri_kaydet(gorulmus)

        except Exception as e:
            print(f"Genel hata: {e}")

        time.sleep(KONTROL_ARALIGI)

if __name__ == "__main__":
    main()

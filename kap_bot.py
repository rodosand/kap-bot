import requests
import time
import json
import os
from datetime import datetime

# --- AYARLAR ---
TELEGRAM_TOKEN = "8154362550:AAGVasRA_XzbNVRvUhhw08IhDoY4P2emCLE"
CHAT_ID = "7229573083"
KONTROL_ARALIGI = 60  # saniye

# Takip edilecek haber türleri
TAKIP_EDILEN_TURLER = [
    "Kamuyu Aydınlatma Platformu Duyurusu",
    "Pay Alım Satım Bildirimi"
]

GORULMUS_DOSYA = "gorulmus.json"
KAP_API = "https://www.kap.org.tr/tr/api/disclosures"

def gorulmus_yukle():
    if os.path.exists(GORULMUS_DOSYA):
        with open(GORULMUS_DOSYA, "r") as f:
            return set(json.load(f))
    return set()

def gorulmus_kaydet(haberler):
    liste = list(haberler)[-2000:]
    with open(GORULMUS_DOSYA, "w") as f:
        json.dump(liste, f)

def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": mesaj,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def kap_cek(after_index=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"
    }
    url = KAP_API
    if after_index:
        url += f"?afterDisclosureIndex={after_index}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"KAP çekme hatası: {e}")
        return []

def tur_eslesiyor(baslik):
    if not baslik:
        return False
    for tur in TAKIP_EDILEN_TURLER:
        if tur.lower() in baslik.lower():
            return True
    return False

def main():
    print("KAP Bot başlatıldı ✅")
    telegram_gonder("✅ <b>KAP Bot aktif!</b>\n\nTakip edilen türler:\n• Kamuyu Aydınlatma Platformu Duyurusu\n• Pay Alım Satım Bildirimi")

    gorulmus = gorulmus_yukle()
    max_index = 0

    # İlk çekişte mevcut haberleri kaydet ama bildirim gönderme
    print("İlk veri çekiliyor...")
    ilk_veri = kap_cek()
    if ilk_veri:
        for haber in ilk_veri:
            basic = haber.get("basic", haber)
            haber_id = str(basic.get("disclosureIndex", ""))
            if haber_id:
                gorulmus.add(haber_id)
                idx = basic.get("disclosureIndex", 0)
                if idx > max_index:
                    max_index = idx
        gorulmus_kaydet(gorulmus)
        print(f"İlk veri alındı. Son index: {max_index}, {len(ilk_veri)} haber yüklendi.")

    while True:
        try:
            time.sleep(KONTROL_ARALIGI)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Kontrol ediliyor... (max_index={max_index})")

            yeni_veriler = kap_cek(after_index=max_index if max_index > 0 else None)

            if not yeni_veriler:
                continue

            yeni_max = max_index
            for haber in yeni_veriler:
                basic = haber.get("basic", haber)
                haber_id = str(basic.get("disclosureIndex", ""))

                if not haber_id or haber_id in gorulmus:
                    continue

                gorulmus.add(haber_id)
                idx = basic.get("disclosureIndex", 0)
                if idx > yeni_max:
                    yeni_max = idx

                baslik = basic.get("title", "")
                if tur_eslesiyor(baslik):
                    sirket = basic.get("companyName", "Bilinmeyen")
                    hisse = basic.get("stockCodes", "") or basic.get("relatedStocks", "")
                    tarih = basic.get("publishDate", "") or basic.get("disclosureDate", "")
                    link = f"https://www.kap.org.tr/tr/Bildirim/{haber_id}"

                    mesaj = (
                        f"📢 <b>KAP BİLDİRİMİ</b>\n\n"
                        f"🏢 <b>Şirket:</b> {sirket}\n"
                    )
                    if hisse:
                        mesaj += f"📈 <b>Hisse:</b> {hisse}\n"
                    mesaj += (
                        f"📋 <b>Tür:</b> {baslik}\n"
                        f"🕐 <b>Tarih:</b> {tarih}\n"
                        f"🔗 <a href='{link}'>Bildirimi Görüntüle</a>"
                    )
                    telegram_gonder(mesaj)
                    print(f"✅ Bildirim gönderildi: {sirket} - {baslik}")

            if yeni_max > max_index:
                max_index = yeni_max
                gorulmus_kaydet(gorulmus)

        except Exception as e:
            print(f"Genel hata: {e}")

if __name__ == "__main__":
    main()

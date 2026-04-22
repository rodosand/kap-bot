import requests
import time
import json
import os
import xml.etree.ElementTree as ET
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

# KAP RSS feed linkleri
RSS_LINKLER = [
    "https://www.kap.org.tr/rss/bildirimler.rss",
    "https://www.kap.org.tr/rss/bildirimler-ozet.rss",
]

def gorulmus_yukle():
    if os.path.exists(GORULMUS_DOSYA):
        with open(GORULMUS_DOSYA, "r") as f:
            return set(json.load(f))
    return set()

def gorulmus_kaydet(haberler):
    liste = list(haberler)[-3000:]
    with open(GORULMUS_DOSYA, "w") as f:
        json.dump(liste, f)

def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": mesaj,
            "parse_mode": "HTML"
        }, timeout=10)
        print(f"Telegram yanıt: {r.status_code}")
    except Exception as e:
        print(f"Telegram hatası: {e}")

def rss_cek(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"RSS çekme hatası ({url}): {e}")
        return None

def rss_isle(xml_text):
    haberler = []
    try:
        root = ET.fromstring(xml_text)
        ns = ""
        channel = root.find("channel")
        if channel is None:
            channel = root

        for item in channel.findall("item"):
            baslik = item.findtext("title", "")
            link = item.findtext("link", "")
            aciklama = item.findtext("description", "")
            tarih = item.findtext("pubDate", "")
            guid = item.findtext("guid", link)

            haberler.append({
                "id": guid,
                "baslik": baslik,
                "link": link,
                "aciklama": aciklama,
                "tarih": tarih
            })
    except Exception as e:
        print(f"RSS parse hatası: {e}")
    return haberler

def tur_eslesiyor(baslik, aciklama):
    metin = (baslik + " " + aciklama).lower()
    for tur in TAKIP_EDILEN_TURLER:
        if tur.lower() in metin:
            return True
    return False

def main():
    print("KAP Bot başlatıldı ✅")
    telegram_gonder("✅ <b>KAP Bot aktif! (RSS modu)</b>\n\nTakip edilen türler:\n• Kamuyu Aydınlatma Platformu Duyurusu\n• Pay Alım Satım Bildirimi")

    gorulmus = gorulmus_yukle()

    # İlk çekişte mevcut haberleri kaydet, bildirim gönderme
    print("İlk RSS verisi yükleniyor...")
    for rss_url in RSS_LINKLER:
        xml_text = rss_cek(rss_url)
        if xml_text:
            haberler = rss_isle(xml_text)
            for h in haberler:
                gorulmus.add(h["id"])
            print(f"  {rss_url} → {len(haberler)} haber yüklendi")
    gorulmus_kaydet(gorulmus)
    print(f"Toplam {len(gorulmus)} haber kaydedildi, izlemeye başlanıyor...")

    while True:
        try:
            time.sleep(KONTROL_ARALIGI)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] RSS kontrol ediliyor...")

            for rss_url in RSS_LINKLER:
                xml_text = rss_cek(rss_url)
                if not xml_text:
                    continue

                haberler = rss_isle(xml_text)
                yeni_sayac = 0

                for h in haberler:
                    if h["id"] in gorulmus:
                        continue

                    gorulmus.add(h["id"])
                    yeni_sayac += 1

                    if tur_eslesiyor(h["baslik"], h["aciklama"]):
                        mesaj = (
                            f"📢 <b>KAP BİLDİRİMİ</b>\n\n"
                            f"📋 <b>{h['baslik']}</b>\n"
                        )
                        if h["aciklama"]:
                            mesaj += f"📝 {h['aciklama'][:200]}\n"
                        if h["tarih"]:
                            mesaj += f"🕐 {h['tarih']}\n"
                        if h["link"]:
                            mesaj += f"🔗 <a href='{h['link']}'>Bildirimi Görüntüle</a>"

                        telegram_gonder(mesaj)
                        print(f"✅ Bildirim gönderildi: {h['baslik'][:80]}")

                if yeni_sayac > 0:
                    gorulmus_kaydet(gorulmus)
                    print(f"  {yeni_sayac} yeni haber bulundu")

        except Exception as e:
            print(f"Genel hata: {e}")

if __name__ == "__main__":
    main()

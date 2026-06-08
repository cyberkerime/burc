import os
from flask import Flask, render_template, request
from datetime import datetime
import psycopg2

app = Flask(__name__)

# [STATEFUL DETAYI]: Render'dan alacağımız harici veritabanı URL'si env değişkeninden okunacak
DB_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DB_URL:
        return None
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

# Veritabanında tablo yoksa otomatik oluşturur
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS burc_gecmisi (
                        id SERIAL PRIMARY KEY,
                        isim VARCHAR(100),
                        dogum_tarihi DATE,
                        dogum_saati TIME,
                        burc VARCHAR(50),
                        yukselen VARCHAR(50),
                        kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Tablo oluşturma hatası: {e}")

# Geçici hafıza (Eğer adım 4'teki DB bağlanmazsa uygulamanın çökmemesi için geçici yedek)
MEMORY_HISTORY = []

# --- STATELESS KISIM ---
# Bu fonksiyonlar sadece girdiye (giriş parametrelerine) bağımlıdır. 
# Dışarıda bir durum saklamazlar, aynı girdiye her zaman aynı çıktıyı verirler.
def calculate_zodiac(day, month):
    if (month == 3 and day >= 21) or (month == 4 and day <= 19): return "Koç"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20): return "Boğa"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20): return "İkizler"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22): return "Yengeç"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22): return "Aslan"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22): return "Başak"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22): return "Terazi"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21): return "Akrep"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21): return "Yay"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19): return "Oğlak"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18): return "Kova"
    else: return "Balık"

def calculate_ascendant(hour):
    # Eğitim amaçlı basitleştirilmiş yükselen burç algoritması
    if 6 <= hour < 8: return "Koç"
    elif 8 <= hour < 10: return "Boğa"
    elif 10 <= hour < 12: return "İkizler"
    elif 12 <= hour < 14: return "Yengeç"
    elif 14 <= hour < 16: return "Aslan"
    elif 16 <= hour < 18: return "Başak"
    elif 18 <= hour < 20: return "Terazi"
    elif 20 <= hour < 22: return "Akrep"
    elif 22 <= hour < 24: return "Yay"
    elif 0 <= hour < 2: return "Oğlak"
    elif 2 <= hour < 4: return "Kova"
    else: return "Balık"

# --- ANA ROTAMIZ ---
@app.route('/', methods=['GET', 'POST'])
def index():
    init_db() # Tablonun varlığından emin oluyoruz
    son_sonuc = None

    if request.method == 'POST':
        isim = request.form.get('isim', 'Anonim')
        tarih_str = request.form.get('dogum_tarihi')
        saat_str = request.form.get('dogum_saati')

        if tarih_str and saat_str:
            dogum_tarihi = datetime.strptime(tarih_str, '%Y-%m-%d').date()
            dogum_saati = datetime.strptime(saat_str, '%H:%M').time()

            # Stateless Hesaplama tetikleniyor
            burc = calculate_zodiac(dogum_tarihi.day, dogum_tarihi.month)
            yukselen = calculate_ascendant(dogum_saati.hour)
            son_sonuc = {'isim': isim, 'burc': burc, 'yukselen': yukselen}

            # [STATEFUL KISIM]: Üretilen sonucu kalıcı veritabanına yazıyoruz
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO burc_gecmisi (isim, dogum_tarihi, dogum_saati, burc, yukselen) VALUES (%s, %s, %s, %s, %s)",
                            (isim, dogum_tarihi, dogum_saati, burc, yukselen)
                        )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Veri kaydetme hatası: {e}")
            else:
                # Veritabanı yoksa geçici belleğe ekle (Konteyner silinince bu veri uçar -> Klasik Stateless Davranışı)
                MEMORY_HISTORY.append({
                    'isim': isim, 'burc': burc, 'yukselen': yukselen,
                    'kayit_tarihi': datetime.now().strftime('%Y-%m-%d %H:%M')
                })

    # Geçmiş kayıtları çekip arayüze gönderiyoruz
    gecmis_listesi = []
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT isim, burc, yukselen, kayit_tarihi FROM burc_gecmisi ORDER BY id DESC")
                rows = cur.fetchall()
            conn.close()
            gecmis_listesi = [{'isim': r[0], 'burc': r[1], 'yukselen': r[2], 'kayit_tarihi': str(r[3])} for r in rows]
        except Exception as e:
            print(f"Veri çekme hatası: {e}")
    else:
        gecmis_listesi = MEMORY_HISTORY

    return render_template('index.html', son_sonuc=son_sonuc, gecmis=gecmis_listesi)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

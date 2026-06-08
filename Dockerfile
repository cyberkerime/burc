# Hafif ve kararlı bir Python imajı seçiyoruz
FROM python:3.11-slim

# Konteyner içindeki çalışma dizinimizi belirliyoruz
WORKDIR /app

# Bağımlılıkları kopyalayıp yüklüyoruz (Cache mekanizmasından yararlanmak için önce bu adım)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projenin kalan tüm dosyalarını konteyner içine aktarıyoruz
COPY . .

# Flask uygulamamızın dış dünyaya açılacağı port
EXPOSE 5000

# Uygulamayı production seviyesinde bir WSGI sunucusu olan Gunicorn ile başlatıyoruz
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

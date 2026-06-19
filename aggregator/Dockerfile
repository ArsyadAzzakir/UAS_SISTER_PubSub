# Menggunakan base image Python yang ringan
FROM python:3.11-slim

# Mencegah Python menulis file .pyc dan memastikan output log langsung muncul
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Menentukan direktori kerja di dalam container
WORKDIR /app

# Meng-copy file requirements dan menginstalnya
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Meng-copy seluruh kode aplikasi ke dalam container
COPY . .

# Menjalankan aplikasi menggunakan uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
# Sử dụng bản Python nhẹ tối ưu cho kiến trúc ARM64 của OCI
FROM python:3.11-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết cho SQLite và tính toán hình học (nếu có)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy file dependency và tiến hành cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY src/ ./src/
COPY data/ ./data/

# Biến môi trường mặc định phục vụ Production
ENV PYTHONUNBUFFERED=1

# Lệnh khởi chạy ứng dụng (Mặc định chạy file main)
CMD ["python", "src/main.py"]

FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV STORAGE_URL=https://storage.yandexcloud.net \
    input_redis_channel=video_processor_request \
    output_redis_channel=video_processor_response
    
CMD ["python", "run.py"]
FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip==24.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV VOICE_CHANGER_REQUEST_CHANNEL=voice_change_request \
    VOICE_CHANGER_RESPONSE_CHANNEL=voice_change_response \
    DATA_STORAGE=https://storage.yandexcloud.net \
    audio_data_temp=tmp/audio \
    video_data_temp=tmp/video \
    video_processor_response_channel=video_processor_response \
    SYNC_SO_API_URL=https://api.sync.so/v2/generate \
    VALIDATE_NAME_SPAM_THRESHOLD=5 \
    VALIDATE_NAME_TIME_WINDOW=10 \
    video_processor_request_channel=video_processor_request

EXPOSE 5000

CMD ["python", "run.py"]
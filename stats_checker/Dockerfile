FROM python:3.9-slim
WORKDIR /app

RUN python3 -m pip install --upgrade pip==24.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .


CMD ["python", "run.py"]
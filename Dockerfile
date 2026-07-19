FROM python:3.14-slim

# Asia/Taipei timestamps in logs and messages
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Taipei

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY domain/ domain/
COPY infrastructure/ infrastructure/
COPY models/ models/
COPY services/ services/

# Runtime files (config.yaml, state.json, crop.jpg, log/) live on the /data
# volume; app/main.py bootstraps its own code path, so CWD holds only state.
WORKDIR /data
CMD ["python", "/app/app/main.py", "--env", "PROD"]

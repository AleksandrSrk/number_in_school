FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Keep python output unbuffered for logs in docker
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Browsers are already present in the base image, but keep this explicit
RUN python -m playwright install chromium

COPY bot_monitor.py ./bot_monitor.py
COPY telegram_debug.py ./telegram_debug.py
COPY monitor.py ./monitor.py
COPY login.py ./login.py

CMD ["python", "-u", "bot_monitor.py"]


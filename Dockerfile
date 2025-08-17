# Dockerfile (copy exactly)
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Minimal tools to add key and fetch packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gnupg2 dirmngr wget curl ca-certificates apt-transport-https gnupg && \
    rm -rf /var/lib/apt/lists/*

# 2) Add Google signing key and repo (secure using gpg --dearmor)
RUN set -eux; \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list

# 3) Install Chrome + runtime libs needed for headless usage
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      google-chrome-stable \
      fonts-liberation \
      libnss3 \
      libx11-xcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxrandr2 \
      libasound2 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libgbm1 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libgtk-3-0 \
      libxss1 \
      xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 4) Copy requirements and install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# 5) Copy app code
COPY . /app

# 6) Copy start script and make executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables
ENV CHROME_PATH=/usr/bin/google-chrome
ENV DEBUGGING_PORT=9222
ENV USER_DATA_DIR=/tmp/ChromeDebugProfile
ENV PORT=10000

# Expose port (Render expects container to listen)
EXPOSE 10000

# Use start.sh to start Chrome (background) and then Gunicorn
CMD ["/app/start.sh"]

# Dockerfile (COPY THIS EXACTLY)
FROM python:3.13-slim

# Avoid any interactive prompts during apt operations
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 1) Install minimal tools to fetch keys and packages
#    - gnupg, curl/wget, ca-certificates are required so we can import Google's signing key robustly
#    - we don't install lots of extras yet to keep build logs clear
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gnupg2 \
      dirmngr \
      wget \
      curl \
      ca-certificates \
      apt-transport-https && \
    rm -rf /var/lib/apt/lists/*

# 2) Add Google signing key (secure method) and the Chrome apt source using signed-by
#    We use gpg --dearmor to create a keyring file and reference it in sources.list.d
RUN set -eux; \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list

# 3) Install Chrome and required libs for headless usage
#    Add Chrome dependencies (GTK etc.) commonly required; keep --no-install-recommends to reduce size
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
      xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# 4) Copy requirements and install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# 5) Copy application code
COPY . /app

# 6) Set env vars (optional but handy)
ENV CHROME_PATH=/usr/bin/google-chrome
ENV DEBUGGING_PORT=9222
ENV USER_DATA_DIR=/tmp/ChromeDebugProfile

# Expose port that Gunicorn will bind to (match your CMD)
EXPOSE 10000

# 7) Start the app using Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]

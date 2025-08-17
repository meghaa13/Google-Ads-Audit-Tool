# Use official Python image
FROM python:3.13-slim

# Install dependencies for Chrome
RUN apt-get update && \
    apt-get install -y wget gnupg curl unzip xdg-utils --no-install-recommends

# Add Google Chrome repository and signing key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome stable
RUN apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends

# Set environment variables for Chrome subprocess
ENV CHROME_PATH=/usr/bin/google-chrome
ENV DEBUGGING_PORT=9222
ENV USER_DATA_DIR=/tmp/ChromeDebugProfile

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for your app if needed (Flask default 5000)
EXPOSE 5000

# Start your app with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]

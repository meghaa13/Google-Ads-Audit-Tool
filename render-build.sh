#!/bin/bash

# Create a folder to store Chromium
mkdir -p .render/chrome

# Download a stable precompiled Chromium for Linux (ungoogled)
curl -L https://github.com/ungoogled-software/ungoogled-chromium/releases/download/114.0.5735.133-1/ungoogled-chromium_114.0.5735.133-1_amd64.deb -o .render/chrome/chromium.deb || { echo "Download failed"; exit 1; }

# Extract Chromium to .render/chrome/
dpkg -x .render/chrome/chromium.deb .render/chrome/ || { echo "Extraction failed"; exit 1; }

# Remove .deb file after extraction
rm .render/chrome/chromium.deb

# Install Python dependencies
pip install -r requirements.txt || { echo "pip install failed"; exit 1; }

echo "✅ Build completed successfully"

#!/bin/bash

# === Update Linux package lists in Render environment ===
apt-get update -y

# === Install Chromium (headless, no GUI needed) ===
apt-get install -y chromium

# === Verify Chromium installation ===
chromium --version || { echo "❌ Chromium install failed"; exit 1; }

# === Install Python dependencies from requirements.txt ===
pip install --upgrade pip
pip install -r requirements.txt || { echo "❌ pip install failed"; exit 1; }

echo "✅ Build completed successfully"

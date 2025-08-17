#!/bin/bash

# Create a folder to store Chromium
mkdir -p .render/chrome

# Download a precompiled Chromium
curl -L https://github.com/Eloston/ungoogled-chromium/releases/download/114.0.5735.133-1/ungoogled-chromium_114.0.5735.133-1_amd64.deb -o .render/chrome/chromium.deb

# Extract Chromium
dpkg -x .render/chrome/chromium.deb .render/chrome/

# Remove .deb file
rm .render/chrome/chromium.deb

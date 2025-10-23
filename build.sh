#!/bin/bash
set -e

apt-get update
apt-get install -y ffmpeg
rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt

echo "✅ Build completed successfully!"

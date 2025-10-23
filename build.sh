#!/bin/bash
set -e

echo "🔧 Starting build process..."

# Install system dependencies
echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y ffmpeg
rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "✅ Build completed successfully!"

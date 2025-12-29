#!/bin/bash
echo "🚀 Starting Music Bot..."

# Check yt-dlp
if command -v yt-dlp &> /dev/null; then
    echo "✅ yt-dlp: $(yt-dlp --version)"
else
    echo "❌ yt-dlp not found!"
fi

# Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg installed"
else
    echo "❌ FFmpeg not found!"
fi

# Create directories
mkdir -p /app/downloads /app/data
echo "✅ Directories ready"

# Initialize database
python -c "from core.database import init_db; init_db()" 2>&1
echo "✅ Database ready"

# Start bot
echo "🤖 Starting bot..."
python -u main.py
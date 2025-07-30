#!/bin/bash

echo "🚀 Starting Books Management API Setup..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies."
    exit 1
fi

# Start the server
echo "🚀 Starting the API server..."
echo "📚 Documentation will be available at: http://localhost:8000/docs"
echo "🔑 API Key for protected routes: your-secret-api-key-12345"
echo "💡 Use 'Authorization: Bearer your-secret-api-key-12345' for write operations"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py 
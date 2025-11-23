#!/bin/bash

# 🚀 Quick Start Script for E-Commerce Research Agent Backend

echo "================================================"
echo "🛍️  E-Commerce Research Agent - Quick Start"
echo "================================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend/ directory"
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "   ✅ .env file created (using defaults)"
else
    echo "✅ .env file already exists"
fi
echo ""

# Make run.sh executable
chmod +x run.sh
echo "✅ Made run.sh executable"
echo ""

echo "================================================"
echo "✨ Setup Complete!"
echo "================================================"
echo ""
echo "🚀 To start the server, run:"
echo "   ./run.sh"
echo ""
echo "📚 Then visit:"
echo "   • API Docs:  http://localhost:8000/docs"
echo "   • ReDoc:     http://localhost:8000/redoc"
echo "   • Health:    http://localhost:8000/health"
echo ""
echo "🧪 To test the API, run:"
echo "   python test_api.py"
echo ""
echo "================================================"

#!/bin/bash

# PDF Summarization Tool Setup Script
# This script helps you set up the project quickly

echo "🚀 PDF Summarization Tool - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "✓ Found: $python_version"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ Pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ All dependencies installed"
echo ""

# Create files directory
echo "📁 Creating files directory..."
mkdir -p files
echo "✓ Files directory created"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created - please edit with your credentials"
else
    echo "ℹ️  .env file already exists"
fi
echo ""

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys and Supabase credentials"
echo "2. Run the setup_supabase.sql in your Supabase SQL Editor"
echo "3. Start the app with: streamlit run app.py"
echo ""
echo "🎉 Happy summarizing!"

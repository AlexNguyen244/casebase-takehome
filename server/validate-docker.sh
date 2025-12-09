#!/bin/bash

# CaseBase API Docker Validation Script
# This script validates the Docker setup

set -e

echo "=================================="
echo "CaseBase API Docker Validation"
echo "=================================="
echo ""

# Check if Docker is installed
echo "1. Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "   Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker is installed: $(docker --version)"
echo ""

# Check if Docker daemon is running
echo "2. Checking Docker daemon..."
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "   Start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi
echo "✓ Docker daemon is running"
echo ""

# Check if docker-compose is installed
echo "3. Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  Docker Compose is not installed (optional)"
    echo "   Install from: https://docs.docker.com/compose/install/"
else
    echo "✓ Docker Compose is installed: $(docker-compose --version)"
fi
echo ""

# Check if .env file exists
echo "4. Checking .env file..."
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo "   Create .env file: cp .env.example .env"
    echo "   Then edit .env and add your API keys"
    exit 1
fi
echo "✓ .env file exists"
echo ""

# Check if Dockerfile exists
echo "5. Checking Dockerfile..."
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile not found"
    exit 1
fi
echo "✓ Dockerfile exists"
echo ""

# Check if docker-compose.yml exists
echo "6. Checking docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found"
    exit 1
fi
echo "✓ docker-compose.yml exists"
echo ""

# Check required environment variables in .env
echo "7. Checking required environment variables..."
required_vars=(
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "S3_BUCKET_NAME"
    "OPENAI_API_KEY"
    "PINECONE_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=your_" .env || grep -q "^${var}=$" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing or incomplete environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "   Edit .env and add the missing values"
    exit 1
fi
echo "✓ All required environment variables are set"
echo ""

# Try to build the Docker image
echo "8. Testing Docker build..."
echo "   (This may take a few minutes on first run...)"
if docker build -t casebase-api-validation-test . > /dev/null 2>&1; then
    echo "✓ Docker build successful"
    # Clean up test image
    docker rmi casebase-api-validation-test > /dev/null 2>&1
else
    echo "❌ Docker build failed"
    echo "   Run 'docker build -t casebase-api .' to see detailed errors"
    exit 1
fi
echo ""

echo "=================================="
echo "✅ All validation checks passed!"
echo "=================================="
echo ""
echo "You can now run:"
echo "  docker-compose up -d     # Start the API"
echo "  docker-compose logs -f   # View logs"
echo "  docker-compose down      # Stop the API"
echo ""

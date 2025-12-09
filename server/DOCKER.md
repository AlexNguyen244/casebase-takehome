# Docker Setup Guide

This guide explains how to run the CaseBase API server using Docker.

## Prerequisites

- Docker installed on your system ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed ([Install Docker Compose](https://docs.docker.com/compose/install/))

## Quick Start

### 1. Set Up Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys and configuration:
- AWS credentials
- OpenAI API key
- Pinecone API key
- SendGrid API key (optional)

### 2. Build and Run with Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The API will be available at `http://localhost:8000`

### 3. Build and Run with Docker (Without Compose)

```bash
# Build the image
docker build -t casebase-api .

# Run the container
docker run -d \
  --name casebase-api \
  -p 8000:8000 \
  --env-file .env \
  casebase-api

# View logs
docker logs -f casebase-api

# Stop and remove container
docker stop casebase-api
docker rm casebase-api
```

## Available Endpoints

Once running, you can access:

- **API Root**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development Mode

For development with hot-reload, the docker-compose.yml mounts your local code:

```bash
# Start in development mode
docker-compose up

# Code changes will be reflected automatically
# (May require container restart for some changes)
```

## Production Deployment

For production, remove the volume mount in `docker-compose.yml`:

```yaml
# Comment out or remove this line:
# volumes:
#   - .:/app
```

Then rebuild and deploy:

```bash
docker-compose up -d --build
```

## Troubleshooting

### Check Container Status
```bash
docker ps
docker-compose ps
```

### View Logs
```bash
docker-compose logs -f api
```

### Restart Container
```bash
docker-compose restart
```

### Rebuild Image
```bash
docker-compose up -d --build
```

### Enter Container Shell
```bash
docker-compose exec api bash
```

### Remove Everything and Start Fresh
```bash
docker-compose down
docker-compose up -d --build
```

## Environment Variables

All configuration is done via environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `AWS_REGION` | AWS region | Yes |
| `S3_BUCKET_NAME` | S3 bucket name | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `PINECONE_API_KEY` | Pinecone API key | Yes |
| `PINECONE_INDEX_NAME` | Pinecone index name | Yes |
| `SENDGRID_API_KEY` | SendGrid API key | No |
| `ALLOWED_ORIGINS` | CORS allowed origins | Yes |

## Health Checks

The container includes automatic health checks:
- Runs every 30 seconds
- Checks `/health` endpoint
- Container marked unhealthy after 3 failed checks

Check health status:
```bash
docker ps
# Look for "healthy" in STATUS column
```

## Resource Management

### View Resource Usage
```bash
docker stats casebase-api
```

### Set Resource Limits (docker-compose.yml)
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Cleaning Up

### Remove Containers and Images
```bash
# Stop and remove containers
docker-compose down

# Remove images
docker rmi casebase-api

# Remove all unused images, containers, networks
docker system prune -a
```

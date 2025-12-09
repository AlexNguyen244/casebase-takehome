# CaseBase Server - Quick Start Guide

## 🚀 Quick Start (Docker - Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Start the server
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Test it's working
curl http://localhost:8000/health
```

Server running at: **http://localhost:8000**

## 📋 What You Need

### Required API Keys
- **AWS**: Access Key ID + Secret Access Key
- **OpenAI**: API Key
- **Pinecone**: API Key
- **SendGrid**: API Key (optional, for email features)

### Get API Keys
- AWS: https://console.aws.amazon.com/iam/
- OpenAI: https://platform.openai.com/api-keys
- Pinecone: https://app.pinecone.io/
- SendGrid: https://app.sendgrid.com/settings/api_keys

## 🎯 Common Operations

### Upload a PDF
```bash
curl -X POST http://localhost:8000/api/pdfs/upload \
  -F "file=@resume.pdf"
```

### Chat with Documents
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What experience does Alex have with AWS?"
  }'
```

### Create PDF from Documents
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a PDF comparing Alex and Kiran'\''s experience"
  }'
```

### Email a PDF
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a PDF on Alex'\''s AWS experience and email to alex@example.com"
  }'
```

### Send Documents via Email
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send all documents about Alex to alex@example.com"
  }'
```

## 🔍 Useful Endpoints

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **List PDFs**: http://localhost:8000/api/pdfs

## 🛠️ Development Commands

```bash
# Start server
docker-compose up -d

# View logs (follow)
docker-compose logs -f

# Restart server
docker-compose restart

# Stop server
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Enter container shell
docker-compose exec api bash

# Run validation
./validate-docker.sh
```

## 📚 Documentation

- **README.md** - Full documentation and features
- **DOCKER.md** - Docker setup and troubleshooting
- **RAG_README.md** - RAG system architecture and details
- **QUICKSTART.md** - This file

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs api

# Verify .env file
cat .env

# Check Docker is running
docker ps
```

### API returns errors
```bash
# Check all environment variables are set
docker-compose exec api env | grep -E "AWS|OPENAI|PINECONE"

# Verify Pinecone index exists
# Check at: https://app.pinecone.io/
```

### Email not sending
- Verify `SENDGRID_API_KEY` is set in `.env`
- Check SendGrid account is verified
- View logs for error details

## 💡 Tips

1. **First Upload**: Upload at least one PDF before chatting
2. **Email Features**: Optional - app works without SendGrid
3. **Development**: Code changes auto-reload with volume mount
4. **Production**: Remove volume mount in docker-compose.yml
5. **Logs**: Use `docker-compose logs -f` to debug issues

## 🎓 Example Workflow

```bash
# 1. Upload some documents
curl -X POST http://localhost:8000/api/pdfs/upload -F "file=@resume1.pdf"
curl -X POST http://localhost:8000/api/pdfs/upload -F "file=@resume2.pdf"

# 2. Chat with them
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare the two resumes"}'

# 3. Create a PDF report
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a PDF comparing both candidates"}'

# 4. Email the report
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Email that PDF to hiring@company.com"}'
```

## 🔗 Next Steps

- Read **README.md** for complete feature list
- Check **RAG_README.md** for RAG pipeline details
- View API docs at http://localhost:8000/docs
- Build a frontend using the REST API

## 📞 Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review **DOCKER.md** troubleshooting section
3. Verify all API keys are valid
4. Check Pinecone index is created

---

**Ready to go!** 🎉 Start uploading documents and chatting with them.

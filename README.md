# CaseBase AI Platform

A production-ready full-stack application for intelligent document management featuring RAG (Retrieval-Augmented Generation), AI-powered chat, automatic PDF generation, and email integration.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Backend
cd server
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d

# Frontend
cd client
npm install
npm start
```

**Backend**: http://localhost:8000 | **Frontend**: http://localhost:3000

### Manual Setup

See detailed setup instructions in:
- `server/README.md` - Backend setup
- `server/QUICKSTART.md` - Fastest backend setup
- `client/README.md` - Frontend setup

## 📁 Project Structure

```
casebase-takehome/
├── client/                          # React Frontend
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.png
│   ├── src/
│   │   ├── components/
│   │   │   ├── PDFUploader.js      # PDF upload with drag-drop
│   │   │   ├── PDFViewer.js        # Document list & viewer
│   │   │   └── Chatbot.js          # AI chatbot interface
│   │   ├── App.js                  # Main application
│   │   ├── index.js                # Entry point
│   │   └── index.css               # Tailwind styles
│   ├── package.json
│   ├── tailwind.config.js
│   └── README.md
│
├── server/                          # FastAPI Backend
│   ├── main.py                     # API endpoints & orchestration
│   ├── config.py                   # Configuration settings
│   │
│   ├── Services/
│   │   ├── s3_service.py           # AWS S3 storage
│   │   ├── pdf_parser.py           # PDF text extraction
│   │   ├── chunking_service.py     # Document chunking
│   │   ├── embedding_service.py    # OpenAI embeddings
│   │   ├── pinecone_service.py     # Vector database
│   │   ├── rag_service.py          # RAG pipeline
│   │   ├── chat_service.py         # AI chat with intent detection
│   │   ├── pdf_generator.py        # PDF creation
│   │   └── email_service.py        # SendGrid integration
│   │
│   ├── Docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── .dockerignore
│   │   └── validate-docker.sh
│   │
│   ├── Documentation/
│   │   ├── README.md               # Complete backend docs
│   │   ├── QUICKSTART.md           # Quick reference
│   │   ├── RAG_README.md           # RAG architecture
│   │   └── DOCKER.md               # Docker guide
│   │
│   └── requirements.txt
│
├── INTEGRATION.md                   # Frontend-Backend integration
└── README.md                        # This file
```

## ✨ Features

### Frontend (React)
- **PDF Upload**: Drag-and-drop or click to upload multiple PDFs
- **Document Management**: View, search, and manage documents
- **PDF Viewer**: In-browser PDF viewing with proxy streaming
- **AI Chatbot (Casey)**: Natural language chat with documents
- **Real-time Updates**: Loading states and progress indicators
- **Responsive Design**: Built with Tailwind CSS
- **Modern UI**: Clean, intuitive interface

### Backend (FastAPI)

#### Core Features
- **RAG Pipeline**: Automatic document processing with vector embeddings
- **AI Chat**: GPT-4o-mini powered conversational interface
- **Smart PDF Generation**: Create PDFs from chat or document content
- **Email Integration**: Send PDFs and documents via SendGrid
- **Vector Search**: Semantic search with Pinecone
- **Source Attribution**: AI tracks and cites source documents

#### Advanced Capabilities
- **Multi-Intent Detection**: Automatically handles chat, PDF creation, email, and bulk send requests
- **Bulk PDF Sending**: Send multiple generated PDFs at once (all, last N, or specific PDFs)
- **Email Memory**: Remembers email addresses across conversation for seamless sending
- **AI Document Filtering**: Intelligently filters relevant documents
- **Markdown Support**: Full markdown rendering in generated PDFs
- **Source Inclusion**: PDFs list source documents at the end
- **Docker Support**: Production-ready containerization
- **Health Checks**: Automated monitoring and validation

## 🛠️ Tech Stack

### Frontend
- **React** 18.2
- **Tailwind CSS** 3.3
- **Lucide React** (icons)
- **Axios** (HTTP client)

### Backend
- **Framework**: FastAPI 0.115+
- **AI/ML**: OpenAI GPT-4o-mini, Langchain, Transformers
- **Vector DB**: Pinecone
- **Storage**: AWS S3 (Boto3)
- **Email**: SendGrid
- **PDF**: PDFPlumber, ReportLab
- **Runtime**: Python 3.11+, Uvicorn
- **Container**: Docker & Docker Compose

## 📋 Prerequisites

- **Node.js 14+** and npm
- **Python 3.11+** (or Docker)
- **AWS Account** with S3 access
- **OpenAI API Key**
- **Pinecone Account**
- **SendGrid API Key** (optional, for email features)

## ⚡ Quick Start

### Option 1: Docker (Recommended)

```bash
# Backend
cd server
cp .env.example .env
# Edit .env with your API keys (AWS, OpenAI, Pinecone, SendGrid)
docker-compose up -d

# Frontend
cd ../client
npm install
npm start
```

### Option 2: Manual Setup

**Backend:**
```bash
cd server
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

**Frontend:**
```bash
cd client
npm install
npm start
```

**Endpoints:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📡 API Endpoints

### Document Management
- `POST /api/pdfs/upload` - Upload PDF (auto-processes through RAG)
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `GET /api/pdfs` - List all PDFs
- `DELETE /api/pdfs/{s3_key}` - Delete PDF (removes from S3 and Pinecone)
- `GET /api/pdfs/view/{s3_key}` - Stream PDF for viewing

### AI & RAG
- `POST /api/rag/query` - Query documents with semantic search
- `POST /api/chat` - AI chat with multi-intent detection
  - Normal chat queries
  - PDF creation requests
  - Email sending requests
  - Document sending requests
  - Bulk PDF sending (all, last N, or specific PDFs)

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 💬 Example Usage

### Chat with Documents
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What experience does Alex have with AWS?"}'
```

### Create PDF from Documents
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a PDF comparing the two resumes"}'
```

### Email PDF
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a PDF on Alex and email to user@example.com"}'
```

### Send Existing Documents
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Send all documents about Alex to user@example.com"}'
```

### Bulk Send Generated PDFs
```bash
# Send all generated PDFs from the conversation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Send all PDFs to user@example.com"}'

# Send last 3 generated PDFs
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Email me the last 3 PDFs", "conversation_history": [...]}'

# Send last PDF only
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Send the last PDF to user@example.com"}'
```

## 🎨 Frontend Components

### PDFUploader
- Drag-and-drop file upload
- Multiple PDF file support
- Loading states with visual feedback
- Upload progress indicators

### PDFViewer
- Document list with metadata
- In-browser PDF viewing
- Delete functionality
- Search and filter capabilities

### Chatbot (Casey)
- Natural language interface
- Chat with your documents
- Automatic PDF creation detection
- Email integration with memory
- Bulk PDF sending (all, last N, specific)
- Conversation history tracking
- Typing indicators

## ⚙️ Configuration

### Backend Environment Variables

Create `server/.env` with:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=casebase-documents
PINECONE_DIMENSION=1536
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# SendGrid Configuration (Optional)
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@casebase.com

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend
No additional configuration needed. Connects to backend at `http://localhost:8000`.

## 🔄 How It Works

### RAG Pipeline
1. Upload PDF → Stored in S3
2. PDF text extracted using PDFPlumber
3. Text chunked semantically (400 tokens/chunk)
4. Chunks embedded using OpenAI
5. Vectors stored in Pinecone
6. Query converted to embedding
7. Semantic search finds relevant chunks
8. AI generates response with sources

### AI Chat Flow
1. User sends message
2. AI detects intent (chat/PDF creation/email/send docs/bulk PDF send)
3. For bulk send: Tracks generated PDFs from conversation history
4. Retrieves relevant document chunks (for queries)
5. Generates response using GPT-4o-mini
6. Tracks source documents used
7. Executes action (reply/create PDF/send email/bulk send PDFs)

## 🌐 Production Deployment

Deploy to production in ~30 minutes:

### Quick Deploy
```bash
# 1. Deploy backend to Render (use Render Dashboard + set env vars)
# 2. Deploy frontend to GitHub Pages
cd client
npm run deploy
```

**See deployment guides:**
- **DEPLOYMENT-QUICKSTART.md** - One-page quick reference
- **DEPLOYMENT.md** - Complete step-by-step guide

**Live URLs after deployment:**
- Frontend: `https://<username>.github.io/casebase-takehome`
- Backend: `https://your-app.onrender.com`

## 🚀 Local Development

### Running Both Services

**Option 1: Docker**
```bash
cd server && docker-compose up -d
cd ../client && npm start
```

**Option 2: Manual**
```bash
# Terminal 1 - Backend
cd server
python main.py

# Terminal 2 - Frontend
cd client
npm start
```

## 📚 Documentation

- **Root README** - This file (overview)
- **DEPLOYMENT.md** - Complete deployment guide (GitHub Pages + Render)
- **DEPLOYMENT-QUICKSTART.md** - Quick deployment reference
- **server/README.md** - Complete backend documentation
- **server/QUICKSTART.md** - Quick backend setup
- **server/RAG_README.md** - RAG architecture details
- **server/DOCKER.md** - Docker deployment guide
- **client/README.md** - Frontend documentation
- **INTEGRATION.md** - Integration notes

## 🔒 Security Considerations

1. **Never commit `.env` files** - Keep credentials secure
2. **Use IAM roles** in production instead of access keys
3. **Configure S3 bucket policies** to restrict access
4. **Enable S3 encryption** for stored files
5. **Implement authentication** before production deployment
6. **Validate file uploads** - File type and size limits
7. **Rate limiting** - Protect API endpoints
8. **CORS configuration** - Restrict allowed origins

## 🎯 Future Enhancements

- User authentication and authorization (JWT)
- Multi-user support with isolated data
- Document versioning and history
- Advanced analytics and usage tracking
- Real-time collaboration features
- Multi-language support
- Streaming chat responses
- Advanced file type support
- Background job processing
- Caching layer for performance

## 📄 License

Private - CaseBase Platform

## 💬 Support

For detailed documentation:
- Backend: See `server/README.md` and `server/QUICKSTART.md`
- Frontend: See `client/README.md`
- Integration: See `INTEGRATION.md`
- Docker: See `server/DOCKER.md`
- RAG System: See `server/RAG_README.md`

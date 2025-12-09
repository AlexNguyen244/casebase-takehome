# CaseBase AI Platform

A production-ready full-stack application for intelligent document management featuring RAG (Retrieval-Augmented Generation), AI-powered chat with priority-based intent detection, automatic PDF generation, and seamless email integration.

## 🎯 What's New in v2.0

- **Priority-Based Intent Detection**: Revolutionary smart routing system that correctly handles ambiguous pronouns like "those" and "them"
  - Prioritizes bulk PDF sending when recent PDFs exist in conversation
  - Requires explicit "source" keyword to send source documents (original files)
  - Context-aware analysis prevents incorrect intent triggering
  - Seamless multi-step conversations with email memory
- **Enhanced Source Document Handling**: Clear separation between generated PDFs and original source files
- **Improved Conversation Tracking**: Better tracking of generated PDFs and email addresses across conversation
- **Comprehensive Documentation**: New detailed [Intent Detection Guide](server/INTENT_DETECTION.md) with examples and architecture diagrams

## ✨ Features

### Frontend (React)
- **PDF Upload**: Drag-and-drop or click to upload multiple PDFs with visual feedback
- **Document Management**: View, search, delete, and manage documents with metadata
- **PDF Viewer**: In-browser PDF viewing with proxy streaming from S3
- **AI Chatbot (Casey)**: Natural language chat interface with multi-intent detection
- **Real-time Updates**: Loading states, progress indicators, and typing animations
- **Responsive Design**: Clean, intuitive UI built with Tailwind CSS
- **Modern UX**: Professional interface with seamless user experience

### Backend (FastAPI)

#### Core Features
- **PDF Document Management**: Upload, store, and manage PDF documents in AWS S3
- **RAG Pipeline**: Automatic document processing, chunking (400 tokens), and vector embeddings
- **AI Chat Assistant**: Chat with your documents using OpenAI GPT-4o-mini
- **Intelligent PDF Generation**: Create professional PDFs from chat history or document content
- **Email Integration**: Send generated PDFs and source documents via SendGrid
- **Vector Search**: Semantic search powered by Pinecone vector database
- **Source Attribution**: AI identifies and cites source documents used in responses

#### Advanced Capabilities (v2.0)
- **Priority-Based Intent Detection**: Smart routing system with context analysis
  - Handles ambiguous pronouns correctly ("send those" → generated PDFs vs sources vs search)
  - Prevents incorrect intent triggering in complex multi-step conversations
  - Context-aware decision making based on conversation history
- **Multi-Intent Detection**: Automatically detects and routes:
  - Normal chat queries
  - PDF creation requests (from history or documents)
  - Email sending requests with address memory
  - Document sending requests with AI filtering
  - Bulk PDF sending (all, last N, or last one)
  - Source document sending (original files used to generate PDFs)
- **Conversation Intelligence**:
  - Tracks all generated PDFs from conversation history
  - Remembers email addresses for seamless multi-step interactions
  - AI-powered document filtering by relevance
  - Source document attribution with metadata storage
- **Professional PDF Generation**:
  - Full markdown support (headers, lists, code blocks, tables)
  - Source document references listed at end
  - Multiple styles for different use cases
- **Production Ready**:
  - Docker support with health checks
  - CORS configuration for frontend integration
  - Asynchronous processing for performance
  - Comprehensive error handling

## 🚀 Quick Start

### Prerequisites

- **Node.js 14+** and npm
- **Python 3.11+** (or Docker)
- **AWS Account** with S3 access
- **OpenAI API Key**
- **Pinecone Account**
- **SendGrid API Key** (optional, for email features)

### Option 1: Docker Setup (Recommended)

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

**Endpoints:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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
│   ├── main.py                     # Application entry point & router registration
│   ├── models.py                   # Pydantic models for API validation
│   ├── config.py                   # Configuration and environment settings
│   │
│   ├── routes/                     # API route definitions (modular structure)
│   │   ├── health.py               # Health check endpoints
│   │   ├── pdfs.py                 # PDF management endpoints
│   │   └── chat.py                 # Chat & RAG endpoints with multi-intent detection
│   │
│   ├── utils/                      # Utility functions
│   │   └── helpers.py              # Helper functions:
│   │                               # - extract_most_recent_email_from_history()
│   │                               # - extract_generated_pdfs_from_history()
│   │                               # - get_source_documents_for_pdf()
│   │
│   ├── Services/
│   │   ├── s3_service.py           # AWS S3 document storage
│   │   ├── pdf_parser.py           # PDF text extraction
│   │   ├── chunking_service.py     # Document chunking for RAG
│   │   ├── embedding_service.py    # OpenAI embeddings generation
│   │   ├── pinecone_service.py     # Pinecone vector database
│   │   ├── rag_service.py          # RAG pipeline orchestration
│   │   ├── chat_service.py         # AI chat with 5 intent detection methods:
│   │   │                           # - detect_email_intent()
│   │   │                           # - detect_pdf_creation_intent()
│   │   │                           # - detect_send_documents_intent()
│   │   │                           # - detect_bulk_pdf_send_intent()
│   │   │                           # - detect_send_source_docs_intent()
│   │   ├── pdf_generator.py        # PDF creation with ReportLab
│   │   └── email_service.py        # SendGrid email integration
│   │
│   ├── Docker/
│   │   ├── Dockerfile              # Container definition
│   │   ├── docker-compose.yml      # Docker Compose orchestration
│   │   ├── .dockerignore           # Docker build exclusions
│   │   └── validate-docker.sh      # Docker validation script
│   │
│   ├── Documentation/
│   │   ├── README.md               # Backend-specific details
│   │   ├── QUICKSTART.md           # Quick reference guide
│   │   ├── DOCKER.md               # Docker setup guide
│   │   ├── RAG_README.md           # RAG architecture documentation
│   │   └── INTENT_DETECTION.md     # Intent detection & priority system (v2.0)
│   │
│   ├── Configuration/
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── .env.example            # Environment variables template
│   │   └── .env                    # Your local config (git-ignored)
│   │
│   └── __pycache__/                # Python cache (git-ignored)
│
├── INTEGRATION.md                   # Frontend-Backend integration guide
├── DEPLOYMENT.md                    # Complete deployment guide
├── DEPLOYMENT-QUICKSTART.md         # Quick deployment reference
└── README.md                        # This file (project overview)
```

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
- **Runtime**: Python 3.11+, Uvicorn (ASGI server)
- **Container**: Docker & Docker Compose

## 📡 API Endpoints

### Document Management
- `POST /api/pdfs/upload` - Upload PDF (auto-processes through RAG pipeline)
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `GET /api/pdfs` - List all PDFs with metadata
- `DELETE /api/pdfs/{s3_key}` - Delete PDF (removes from S3 and Pinecone)
- `GET /api/pdfs/view/{s3_key}` - Stream PDF for in-browser viewing
- `GET /api/pdfs/{s3_key}/download-url` - Get proxy URL for PDF

### AI & RAG
- `POST /api/rag/query` - Query documents with semantic search
- `POST /api/chat` - AI chat with priority-based multi-intent detection
  - Normal chat queries with source citations
  - PDF creation requests (from history or document content)
  - Email sending requests with address memory
  - Document sending requests with AI filtering
  - Bulk PDF sending (all, last N, or last one)
  - Source document sending (original files)

### Health & Status
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 💬 Example Usage

### Upload and Chat
```bash
# Upload a PDF (triggers RAG processing)
curl -X POST "http://localhost:8000/api/pdfs/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"

# Chat with documents
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What experience does Alex have with AWS?"}'
```

### PDF Generation
```bash
# Create PDF from documents
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a PDF comparing Alex and Kiran'"'"'s experience"}'

# Email PDF
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a PDF on Alex'"'"'s fit for CaseBase and email to alex@example.com"}'
```

### Document Sending
```bash
# Send existing documents via email
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Send all documents relating to Alex to alex@example.com"}'
```

### Bulk PDF Sending (NEW v2.0)
```bash
# Send all generated PDFs from conversation
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send all PDFs to alex@example.com",
    "conversation_history": [...]
  }'

# Send last 3 generated PDFs
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Email me the last 3 PDFs",
    "conversation_history": [...]
  }'

# Send only the last PDF
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send the last PDF to alex@example.com",
    "conversation_history": [...]
  }'
```

### Source Document Sending (NEW v2.0)
```bash
# Send original source documents used to create PDFs
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send me the sources for those PDFs to alex@example.com",
    "conversation_history": [...]
  }'
```

## 🔄 How It Works

### RAG Pipeline
1. **Document Upload**: PDF uploaded via API endpoint
2. **Storage**: File stored in AWS S3 with metadata
3. **Extraction**: Text extracted using PDFPlumber
4. **Chunking**: Document split into 400-token semantic chunks (Langchain)
5. **Embedding**: Chunks converted to 1536-dim vector embeddings (OpenAI)
6. **Indexing**: Vectors stored in Pinecone with metadata (file name, page, text)
7. **Query**: User queries converted to embeddings
8. **Search**: Semantic search finds top-k relevant chunks by cosine similarity
9. **Response**: AI generates response using retrieved context

### AI Chat Flow (v2.0 with Priority System)

1. **Context Analysis** (NEW):
   - Check for recently generated PDFs in conversation history
   - Detect sending keywords ("send", "email", "those", "them", etc.)
   - Detect source keywords ("source", "sources", "original documents")

2. **Priority-Based Intent Detection**:
   - **HIGHEST PRIORITY**: Bulk PDF send
     - When: Recent PDFs exist + send keywords + NO source keywords
     - Example: "Send those to my email" → Sends generated PDFs
   - **MEDIUM PRIORITY**: Send existing documents
     - When: Bulk send doesn't trigger
     - Example: "Send documents about healthcare" → Searches vector DB
   - **LOWEST PRIORITY**: Send source documents
     - When: User explicitly mentions "source"
     - Example: "Send me the sources" → Sends original files
   - Also detects: Normal chat queries, PDF creation, email addresses

3. **PDF Tracking** (for bulk send):
   - Extract all generated PDF S3 keys from conversation history
   - Parse selection criteria (all, last N, last one)
   - Select appropriate PDFs based on user request

4. **Query Processing** (for chat/documents):
   - Extract topic/query from user message
   - Generate embeddings from query text
   - Retrieve top-k relevant document chunks from Pinecone

5. **AI Response Generation**:
   - Build context from retrieved chunks
   - Generate AI response using GPT-4o-mini
   - Track which source documents were actually used (not just retrieved)

6. **Action Execution**:
   - For chat: Return AI response with source citations
   - For PDF: Generate professional PDF with source attribution
   - For email: Send PDF via SendGrid with remembered address
   - For documents: AI filter relevant docs and email selected ones
   - For bulk send: Download selected PDFs from S3 and email all at once
   - For source docs: Retrieve PDF metadata, download original sources, email them

### Priority System Example Scenarios

**Scenario 1: Sending Generated PDFs**
```
User: "Create PDF for Alex's skills"
Bot: [Creates PDF 1]

User: "Create PDF for Casebase role"
Bot: [Creates PDF 2]

User: "Send those to my email"
System:
  ✓ has_recent_pdfs = True (2 PDFs found)
  ✓ user_wants_to_send = True ("send" detected)
  ✗ user_wants_sources = False (no "source" keyword)
  → Checks bulk_send_intent FIRST
  → Sends the 2 generated PDFs ✅
```

**Scenario 2: Sending Source Documents**
```
User: "Create PDF for Alex's skills"
Bot: [Creates PDF using AlexNguyen-Resume.pdf as source]

User: "Send me the sources for that"
System:
  ✓ has_recent_pdfs = True
  ✓ user_wants_to_send = True
  ✓ user_wants_sources = True ("sources" detected)
  → SKIPS bulk_send priority check
  → Checks send_source_docs_intent
  → Retrieves PDF metadata
  → Sends AlexNguyen-Resume.pdf ✅
```

**For detailed intent detection documentation**, see [server/INTENT_DETECTION.md](server/INTENT_DETECTION.md)

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

### Frontend Configuration

The frontend connects to the backend at `http://localhost:8000` by default.

To change the backend URL, edit `client/src/App.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### AWS S3 Setup

Create an S3 bucket:
```bash
aws s3 mb s3://casebase-pdfs --region us-east-1
```

Required IAM permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::casebase-pdfs",
                "arn:aws:s3:::casebase-pdfs/*"
            ]
        }
    ]
}
```

## 🌐 Production Deployment

Deploy to production in ~30 minutes using the deployment guides:

### Quick Deploy
```bash
# 1. Deploy backend to Render (use Render Dashboard + set env vars)
# 2. Deploy frontend to GitHub Pages
cd client
npm run deploy
```

**See deployment guides:**
- **[DEPLOYMENT-QUICKSTART.md](DEPLOYMENT-QUICKSTART.md)** - One-page quick reference
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete step-by-step guide with screenshots

**Live URLs after deployment:**
- Frontend: `https://<username>.github.io/casebase-takehome`
- Backend: `https://your-app.onrender.com`

## 🚀 Local Development

### Running Both Services

**Option 1: Docker (Recommended)**
```bash
# Terminal 1 - Backend
cd server
docker-compose up -d
docker-compose logs -f

# Terminal 2 - Frontend
cd client
npm start
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

### Development Tips

- **Hot Reload**: Both services support hot reload for development
- **API Docs**: Visit http://localhost:8000/docs for interactive API testing
- **Logs**: Check backend terminal for RAG processing and intent detection logs
- **CORS**: Ensure `ALLOWED_ORIGINS` includes `http://localhost:3000`

## 🎨 Frontend Components

### PDFUploader (`client/src/components/PDFUploader.js`)
- Drag-and-drop file upload interface
- Multiple PDF file support
- Loading states with visual feedback
- Upload progress indicators
- Error handling with user-friendly messages

### PDFViewer (`client/src/components/PDFViewer.js`)
- Document list with metadata (name, size, upload date)
- In-browser PDF viewing via proxy
- Delete functionality with confirmation
- Search and filter capabilities
- Responsive grid layout

### Chatbot (`client/src/components/Chatbot.js`)
- Natural language chat interface
- Conversation history with scrolling
- Typing indicators for AI responses
- Multi-intent detection support (transparent to user)
- Email integration with address memory
- Bulk PDF sending (all, last N, specific)
- Source document sending
- Markdown rendering in messages

## 🔒 Security Considerations

1. **Never commit `.env` files** - Keep AWS credentials and API keys secure
2. **Use IAM roles** in production instead of access keys
3. **Configure S3 bucket policies** to restrict access
4. **Enable S3 encryption** for stored files (AES-256)
5. **Use presigned URLs** with short expiration times for file access
6. **Implement authentication** before deploying to production (JWT recommended)
7. **Validate file uploads** - Enforce file type and size limits
8. **Rate limiting** - Protect API endpoints from abuse
9. **CORS configuration** - Restrict allowed origins to known domains
10. **Input sanitization** - Validate and sanitize all user inputs

## 🐛 Troubleshooting

### Common Issues

**CORS Errors**
- Verify `ALLOWED_ORIGINS` in `server/.env` includes your frontend URL
- Check backend logs for CORS middleware messages

**Upload Failures**
- Verify S3 credentials are correct
- Ensure S3 bucket exists and is accessible
- Check file size limits (default: 10MB)

**Chat Not Working**
- Verify OpenAI API key is valid and has credits
- Check Pinecone index exists and is accessible
- Ensure at least one document is uploaded and processed

**PDF Generation Fails**
- Check ReportLab installation: `pip install reportlab`
- Verify source documents exist in S3
- Review backend logs for specific errors

**Email Not Sending**
- Verify SendGrid API key is valid
- Check SendGrid account is verified (domain/sender verification)
- Review backend logs for SendGrid API errors
- Check spam folder for delivered emails

**Intent Detection Issues**
- Enable debug logging to see which intent is triggered
- Check conversation history is being passed correctly
- Verify recent PDFs exist in conversation for bulk send
- See [INTENT_DETECTION.md](server/INTENT_DETECTION.md) for troubleshooting guide

## 📚 Complete Documentation

### Core Documentation
- **This File** - Project overview and quick start
- **[INTEGRATION.md](INTEGRATION.md)** - Frontend-Backend integration guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide (GitHub Pages + Render)
- **[DEPLOYMENT-QUICKSTART.md](DEPLOYMENT-QUICKSTART.md)** - Quick deployment reference

### Backend Documentation
- **[server/README.md](server/README.md)** - Complete backend documentation
- **[server/QUICKSTART.md](server/QUICKSTART.md)** - Quick backend setup
- **[server/RAG_README.md](server/RAG_README.md)** - RAG architecture and pipeline details
- **[server/DOCKER.md](server/DOCKER.md)** - Docker deployment guide
- **[server/INTENT_DETECTION.md](server/INTENT_DETECTION.md)** - Intent detection system & priority logic (v2.0)

### Frontend Documentation
- **[client/README.md](client/README.md)** - Frontend documentation and component details

## 🎯 Future Enhancements

### Planned Features
- User authentication and authorization (JWT tokens)
- Multi-user support with isolated data per organization
- Document versioning and edit history
- Advanced analytics and usage tracking dashboard
- Real-time collaboration features (WebSockets)
- Multi-language support for international users
- Streaming chat responses for better UX
- Advanced file type support (Word, Excel, PowerPoint)
- Background job processing with Celery/Redis
- Caching layer for improved performance
- Advanced search with filters and facets
- Document annotations and highlights
- Export conversations to various formats
- Integration with popular productivity tools (Slack, Teams, etc.)

### Technical Improvements
- Machine learning for faster intent classification
- Intent confidence scores for better decision making
- Multi-intent support (handle multiple intents in one message)
- User preference learning and personalization
- A/B testing framework for features
- Advanced monitoring and observability (Datadog, New Relic)
- Auto-scaling for high-traffic scenarios
- Database migration from file-based to PostgreSQL
- GraphQL API option alongside REST

## 📄 License

Private - CaseBase Platform

## 💬 Support

For questions, issues, or contributions:
- Check the relevant documentation in the list above
- Review troubleshooting section for common issues
- Examine backend logs for detailed error messages
- Test with Swagger UI at http://localhost:8000/docs

## 🙏 Acknowledgments

Built with:
- OpenAI for powerful AI models
- Pinecone for vector database
- AWS for reliable cloud storage
- SendGrid for email delivery
- FastAPI for modern Python web framework
- React for intuitive frontend
- Tailwind CSS for beautiful styling
- And many other amazing open-source libraries

---

**Version**: 2.0
**Last Updated**: December 2025
**Status**: Production Ready

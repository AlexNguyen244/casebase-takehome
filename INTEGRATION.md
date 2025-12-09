# Frontend-Backend Integration Guide

This document outlines the complete integration between the React frontend and FastAPI backend, including all features and communication patterns.

## 🏗️ Architecture Overview

### Backend (FastAPI - Port 8000)
- **RAG Pipeline**: Automatic PDF processing with vector embeddings
- **AI Chat Service**: GPT-4o-mini powered chat with intent detection
- **Vector Database**: Pinecone for semantic search
- **Storage**: AWS S3 for PDF documents
- **Email Service**: SendGrid integration
- **PDF Generation**: ReportLab for creating professional PDFs

### Frontend (React - Port 3000)
- **PDF Management**: Upload, view, and delete documents
- **AI Chatbot**: Natural language interface (Casey)
- **Real-time Updates**: Loading states and progress indicators
- **Responsive UI**: Tailwind CSS with modern design

## 🔌 Integration Points

### 1. PDF Upload & Processing

**Frontend (App.js)**
```javascript
const handlePDFUpload = async (files) => {
  const formData = new FormData();
  formData.append('file', files[0]);

  await axios.post(`${API_BASE_URL}/api/pdfs/upload`, formData);
  // Auto-triggers RAG processing on backend
  fetchPDFs(); // Refresh list
};
```

**Backend Flow:**
1. Receives PDF file
2. Stores in S3
3. Extracts text with PDFPlumber
4. Chunks text semantically
5. Generates embeddings (OpenAI)
6. Stores in Pinecone
7. Returns success response

**Response:**
```json
{
  "message": "PDF uploaded and processed successfully",
  "s3_data": { ... },
  "rag_data": {
    "total_chunks": 45,
    "upserted_count": 45
  }
}
```

### 2. AI Chat Integration

**Frontend (Chatbot.js)**
```javascript
const sendMessage = async (message) => {
  const response = await axios.post(`${API_BASE_URL}/api/chat`, {
    message,
    conversation_history: messages,
    top_k: 5
  });

  // Handle different response types:
  // - Normal chat
  // - PDF creation
  // - Email confirmation
};
```

**Backend Intelligence:**
- Detects user intent automatically
- Routes to appropriate handler:
  - **Chat**: Returns AI response with sources
  - **PDF Creation**: Generates and returns PDF
  - **Email**: Creates and sends PDF via email
  - **Send Docs**: Filters and emails documents

### 3. PDF Viewing

**Frontend (PDFViewer.js)**
```javascript
const viewPDF = (s3_key) => {
  // Opens PDF in new tab using proxy endpoint
  window.open(`${API_BASE_URL}/api/pdfs/view/${s3_key}`, '_blank');
};
```

**Backend:**
- Proxies PDF from S3
- Streams content to browser
- Handles authentication/authorization

### 4. Document Deletion

**Frontend**
```javascript
const handleDeletePDF = async (s3_key) => {
  await axios.delete(`${API_BASE_URL}/api/pdfs/${s3_key}`);
  fetchPDFs(); // Refresh list
};
```

**Backend:**
- Deletes from S3
- Removes vectors from Pinecone
- Returns confirmation

## ✨ Features Implemented

### Frontend Features
✅ **PDF Upload**
- Drag-and-drop interface
- Multiple file upload support
- Loading states with visual feedback
- Progress indicators
- Error handling

✅ **PDF Management**
- List all uploaded documents
- View PDFs in browser
- Delete functionality
- Metadata display (name, size, date)

✅ **AI Chatbot (Casey)**
- Natural language interface
- Conversation history
- Typing indicators
- Context-aware responses
- Multi-intent detection support

### Backend Features
✅ **RAG Pipeline**
- Automatic PDF text extraction
- Semantic chunking (400 tokens/chunk)
- Vector embedding generation
- Pinecone storage
- Efficient semantic search

✅ **AI Chat**
- Multi-intent detection
- Source attribution
- PDF creation from documents
- Email integration
- Document filtering

✅ **PDF Generation**
- Professional formatting
- Markdown support
- Source document listing
- Multiple styles (chat history, document content)

✅ **Email Service**
- SendGrid integration
- PDF attachments
- Multiple document sending
- Custom templates

## 🔄 Data Flow Examples

### Upload Flow
```
User → PDFUploader → FormData → POST /api/pdfs/upload
  ↓
Backend receives → S3 upload → PDF parsing → Text chunking
  ↓
Embedding generation → Pinecone upsert → Response
  ↓
Frontend refreshes PDF list
```

### Chat Flow
```
User message → Chatbot → POST /api/chat
  ↓
Backend intent detection → Route to handler
  ↓
If chat: RAG retrieval → AI response → Frontend displays
If PDF: Generate PDF → Return download link → Frontend opens
If email: Generate PDF → Send email → Frontend confirms
If send docs: Filter docs → Send email → Frontend confirms
```

### Delete Flow
```
User clicks delete → DELETE /api/pdfs/{s3_key}
  ↓
Backend deletes from S3 → Deletes from Pinecone → Response
  ↓
Frontend removes from list
```

## 🧪 Testing

### Start Services

**Option 1: Docker**
```bash
# Backend
cd server
docker-compose up -d

# Frontend
cd ../client
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

### Test Scenarios

**1. Upload PDF**
- Drag PDF to upload area
- See loading indicator
- Verify PDF appears in list
- Check backend logs for RAG processing

**2. Chat with Documents**
- Type: "What does the document say about X?"
- Verify AI response includes source citations
- Check conversation history is maintained

**3. Create PDF**
- Type: "Create a PDF comparing the documents"
- Verify PDF download link appears
- Open PDF and verify content + sources listed

**4. Email PDF**
- Type: "Create a PDF and email to user@example.com"
- Verify success message
- Check email inbox for PDF

**5. Send Documents**
- Type: "Send all documents about Alex to user@example.com"
- Verify only relevant documents sent
- Check email for attachments

## 📡 API Endpoints Reference

### Document Management
- `GET /api/pdfs` - List all PDFs
- `POST /api/pdfs/upload` - Upload single PDF (triggers RAG)
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `DELETE /api/pdfs/{s3_key}` - Delete PDF (S3 + Pinecone)
- `GET /api/pdfs/view/{s3_key}` - Stream PDF for viewing

### AI & RAG
- `POST /api/rag/query` - Semantic search query
- `POST /api/chat` - AI chat with multi-intent detection

### Health & Status
- `GET /` - API root
- `GET /health` - Health check

## 🔧 Configuration

### Frontend Configuration
**File**: `client/src/App.js`
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### Backend Configuration
**File**: `server/.env`
```env
# Required
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...

# Optional
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=...

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

## 🐛 Troubleshooting

### CORS Errors
- Verify `ALLOWED_ORIGINS` in `server/.env`
- Check backend logs for CORS middleware

### Upload Failures
- Check S3 credentials
- Verify S3 bucket exists
- Check file size limits

### Chat Not Working
- Verify OpenAI API key
- Check Pinecone index exists
- Ensure documents are uploaded first

### PDF Generation Fails
- Check ReportLab installation
- Verify source documents exist in S3

### Email Not Sending
- Verify SendGrid API key
- Check SendGrid account verified
- Review backend logs for errors

## 🚀 Next Steps

- **Authentication**: Add JWT tokens for user management
- **Rate Limiting**: Implement API rate limits
- **File Validation**: Add virus scanning and size limits
- **Streaming**: Implement real-time chat streaming
- **Analytics**: Track usage and performance metrics
- **Caching**: Add Redis for improved performance
- **WebSockets**: Real-time updates for document processing
- **Multi-tenancy**: Support multiple organizations

## 📚 Related Documentation

- **Backend**: `server/README.md` - Complete backend docs
- **Frontend**: `client/README.md` - Frontend documentation
- **RAG System**: `server/RAG_README.md` - RAG architecture
- **Docker**: `server/DOCKER.md` - Deployment guide
- **Quick Start**: `server/QUICKSTART.md` - Fast setup

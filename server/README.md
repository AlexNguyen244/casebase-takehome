# CaseBase Server

FastAPI server for the CaseBase AI platform with intelligent document management, RAG (Retrieval Augmented Generation), and AI-powered chat capabilities.

## Features

### Core Features
- **PDF Document Management**: Upload, store, and manage PDF documents in AWS S3
- **RAG Pipeline**: Automatic document processing, chunking, and vector embeddings
- **AI Chat Assistant**: Chat with your documents using OpenAI GPT models
- **Intelligent PDF Generation**: Create professional PDFs from chat history or document content
- **Email Integration**: Send generated PDFs and source documents via email
- **Vector Search**: Semantic search powered by Pinecone vector database
- **Source Attribution**: AI identifies and cites source documents used in responses

### Advanced Capabilities
- **AI-Powered Document Filtering**: Intelligently filters relevant documents for queries
- **Multi-Intent Detection**: Automatically detects PDF creation, email, document send, and bulk PDF send requests
- **Bulk PDF Sending**: Send multiple generated PDFs at once (all, last N, or last one)
- **Email Memory**: Remembers email addresses across conversation for seamless interactions
- **PDF Tracking**: Tracks all generated PDFs from conversation history
- **Source Document Inclusion**: Generated PDFs include source document references
- **Markdown Support**: Full markdown formatting in generated PDFs
- **CORS Enabled**: Ready for React frontend integration
- **Docker Support**: Production-ready containerization

## Tech Stack

- **Framework**: FastAPI 0.115+
- **AI/ML**: OpenAI GPT-4o-mini, Langchain, Transformers
- **Vector Database**: Pinecone
- **Storage**: AWS S3 (Boto3)
- **Email**: SendGrid
- **PDF Processing**: PDFPlumber, ReportLab
- **Runtime**: Python 3.11+, Uvicorn (ASGI server)
- **Containerization**: Docker & Docker Compose

## Prerequisites

- **Python 3.11+** (or Docker for containerized deployment)
- **AWS Account** with S3 access
- **OpenAI API Key** for AI chat and embeddings
- **Pinecone Account** for vector database
- **SendGrid API Key** (optional, for email features)
- **Docker** (optional, for containerized deployment)

## Setup

Choose one of the following setup methods:

### Option 1: Docker Setup (Recommended)

The easiest way to run the server is using Docker:

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env and add your API keys

# 2. Build and start the container
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Stop the container
docker-compose down
```

The API will be available at `http://localhost:8000`

For detailed Docker setup instructions, see [DOCKER.md](DOCKER.md)

### Option 2: Manual Setup

#### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

Create a `.env` file in the `server` directory:

```bash
cp .env.example .env
```

Edit `.env` with your API keys and configuration:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=casebase-documents
PINECONE_DIMENSION=1536
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# SendGrid Configuration (Optional)
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@casebase.com

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000
```

#### 3. Create S3 Bucket

Create an S3 bucket in your AWS account:

```bash
aws s3 mb s3://casebase-pdfs --region us-east-1
```

Or use the AWS Console to create a bucket named `casebase-pdfs`.

#### 4. Configure S3 Bucket CORS (Optional)

If you want to access files directly from the browser, configure CORS on your S3 bucket:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["http://localhost:3000"],
        "ExposeHeaders": []
    }
]
```

#### 5. Run the Server

```bash
# From the server directory
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check

- `GET /` - Root endpoint
- `GET /health` - Health check

### PDF Management

- `POST /api/pdfs/upload` - Upload a single PDF (automatically processes through RAG pipeline)
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `GET /api/pdfs` - List all PDFs
- `DELETE /api/pdfs/{s3_key}` - Delete a PDF (removes from S3 and Pinecone)
- `GET /api/pdfs/{s3_key}/download-url` - Get proxy URL for viewing PDF
- `GET /api/pdfs/view/{s3_key}` - Stream PDF directly from S3

### AI & RAG

- `POST /api/rag/query` - Query documents using semantic search
- `POST /api/chat` - Chat with documents using AI assistant
  - Supports natural language queries
  - Automatically detects PDF creation requests
  - Detects email sending requests
  - Detects document sending requests
  - Detects bulk PDF sending requests (all, last N, specific)
  - Tracks generated PDFs from conversation history
  - Returns AI-generated responses with source citations

### PDF Generation

- `POST /api/generate-pdf` - Generate PDF from prompt/response or chat history

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example Usage

### Upload a PDF (Auto-processes through RAG)

```bash
curl -X POST "http://localhost:8000/api/pdfs/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"
```

Response includes both S3 upload confirmation and RAG processing results.

### Chat with Documents

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What experience does Alex have with AWS?",
    "conversation_history": [],
    "top_k": 5
  }'
```

The AI will:
- Search relevant documents
- Generate a response based on document content
- Include source citations

### Request PDF Creation via Chat

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a PDF comparing Alex and Kiran'\''s experience"
  }'
```

Returns a PDF with the analysis and source documents listed.

### Request PDF via Email

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a PDF on Alex'\''s fit for CaseBase and email to alex@example.com"
  }'
```

Automatically creates and emails the PDF with source attribution.

### Send Existing Documents via Email

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send me all documents relating to Alex to alex@example.com"
  }'
```

AI filters and sends only relevant documents.

### Bulk Send Generated PDFs

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

# Send only the last generated PDF
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send the last PDF to alex@example.com",
    "conversation_history": [...]
  }'
```

The system tracks all generated PDFs in the conversation and intelligently selects which ones to send.

### Query RAG System

```bash
curl -X POST "http://localhost:8000/api/rag/query?query=AWS+experience&top_k=5"
```

Returns relevant document chunks with similarity scores.

### List All PDFs

```bash
curl -X GET "http://localhost:8000/api/pdfs"
```

### Delete a PDF

```bash
curl -X DELETE "http://localhost:8000/api/pdfs/pdfs/20231208_120000_document.pdf"
```

Removes from both S3 and Pinecone vector database.

## Project Structure

```
server/
├── main.py                  # FastAPI application and API endpoints
│                            # Includes helper functions:
│                            # - extract_most_recent_email_from_history()
│                            # - extract_generated_pdfs_from_history()
├── config.py                # Configuration and environment settings
│
├── Services/
│   ├── s3_service.py        # AWS S3 document storage
│   ├── pdf_parser.py        # PDF text extraction
│   ├── chunking_service.py  # Document chunking for RAG
│   ├── embedding_service.py # OpenAI embeddings generation
│   ├── pinecone_service.py  # Pinecone vector database
│   ├── rag_service.py       # RAG pipeline orchestration
│   ├── chat_service.py      # AI chat with intent detection
│                            # - detect_email_intent()
│                            # - detect_pdf_creation_intent()
│                            # - detect_send_documents_intent()
│                            # - detect_bulk_pdf_send_intent()
│   ├── pdf_generator.py     # PDF creation with ReportLab
│   └── email_service.py     # SendGrid email integration
│
├── Docker/
│   ├── Dockerfile           # Container definition
│   ├── docker-compose.yml   # Docker Compose orchestration
│   ├── .dockerignore        # Docker build exclusions
│   └── validate-docker.sh   # Docker validation script
│
├── Documentation/
│   ├── README.md            # This file
│   ├── DOCKER.md            # Docker setup guide
│   └── RAG_README.md        # RAG system documentation
│
├── Configuration/
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment variables template
│   └── .env                 # Your local config (git-ignored)
│
└── __pycache__/             # Python cache (git-ignored)
```

## AWS IAM Permissions

Your AWS user/role needs the following S3 permissions:

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

## Security Considerations

1. **Never commit `.env` file** - Keep AWS credentials secure
2. **Use IAM roles** in production instead of access keys
3. **Configure S3 bucket policies** to restrict access
4. **Enable S3 encryption** for stored files
5. **Use presigned URLs** with short expiration times
6. **Implement authentication** before deploying to production

## Connecting to Frontend

Update your React frontend to use these endpoints:

```javascript
// Example: Upload PDF
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/pdfs/upload', {
  method: 'POST',
  body: formData,
});
```

## Error Handling

The API returns structured error responses:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid file type, etc.)
- `500` - Internal Server Error

## How It Works

### RAG Pipeline

1. **Document Upload**: PDF uploaded to endpoint
2. **Storage**: File stored in AWS S3
3. **Extraction**: Text extracted using PDFPlumber
4. **Chunking**: Document split into semantic chunks (Langchain)
5. **Embedding**: Chunks converted to vector embeddings (OpenAI)
6. **Indexing**: Vectors stored in Pinecone with metadata
7. **Query**: User queries converted to embeddings
8. **Search**: Semantic search finds relevant chunks
9. **Response**: AI generates response using retrieved context

### AI Chat Flow

1. **Intent Detection**: AI analyzes user message for:
   - Normal chat query
   - PDF creation request
   - Email sending request
   - Document sending request
   - Bulk PDF send request (all, last N, or last one)

2. **PDF Tracking** (for bulk send):
   - Extract all generated PDF S3 keys from conversation history
   - Parse selection criteria (all, last N, specific)
   - Select appropriate PDFs based on user request

3. **Query Processing** (for chat/documents):
   - Extract topic/query from user message
   - Generate embeddings
   - Retrieve relevant document chunks

4. **AI Response Generation**:
   - Build context from retrieved chunks
   - Generate AI response using GPT-4o-mini
   - Track which sources were actually used

5. **Action Execution**:
   - For chat: Return AI response with sources
   - For PDF: Generate PDF with source attribution
   - For email: Send PDF via SendGrid
   - For documents: Filter relevant docs and email
   - For bulk send: Download selected PDFs from S3 and email all at once

## Architecture Highlights

- **Asynchronous Processing**: All services use async/await for performance
- **Intent-Based Routing**: Multi-classifier system for request handling (chat, PDF, email, bulk send)
- **Conversation Tracking**: Tracks generated PDFs across conversation for bulk operations
- **Email Memory**: Remembers email addresses for seamless multi-step interactions
- **Source Attribution**: AI explicitly tracks document usage
- **Smart Filtering**: AI-powered relevance filtering for document selection
- **Markdown Support**: Full markdown rendering in generated PDFs
- **Health Checks**: Automated container health monitoring
- **CORS Configuration**: Frontend-ready with configurable origins

## Future Enhancements

- User authentication (JWT tokens)
- Rate limiting and usage quotas
- Advanced file validation and virus scanning
- Multi-language support
- Streaming responses for real-time chat
- Batch document processing
- Document versioning
- Advanced analytics and usage tracking
- WebSocket support for real-time updates

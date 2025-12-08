# CaseBase

A full-stack application for the CaseBase Community Supervision Platform, featuring PDF document management with AWS S3 storage and an AI-powered chatbot assistant.

## Project Structure

```
CaseBase/
├── client/                    # React frontend
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.png
│   ├── src/
│   │   ├── components/
│   │   │   ├── PDFUploader.js    # PDF upload component
│   │   │   ├── PDFViewer.js       # Document list viewer
│   │   │   └── Chatbot.js         # AI chatbot interface
│   │   ├── App.js                 # Main application
│   │   ├── index.js               # Entry point
│   │   └── index.css              # Tailwind styles
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── server/                    # FastAPI backend
│   ├── main.py                # API endpoints
│   ├── s3_service.py          # AWS S3 integration
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example           # Environment template
│   └── README.md              # Backend documentation
│
└── README.md                  # This file
```

## Features

### Frontend (React)
- **PDF Upload**: Drag-and-drop or click to upload multiple PDF files
- **Document Management**: View all uploaded documents with metadata
- **Delete Functionality**: Remove documents from storage
- **AI Chatbot (Casey)**: Interactive chatbot interface
- **Responsive Design**: Built with Tailwind CSS

### Backend (FastAPI)
- **AWS S3 Integration**: Secure cloud storage for PDFs
- **RESTful API**: Complete CRUD operations for PDFs
- **File Validation**: Ensures only PDF files are uploaded
- **Presigned URLs**: Secure temporary download links
- **CORS Enabled**: Ready for frontend integration

## Tech Stack

### Frontend
- React 18.2
- Tailwind CSS 3.3
- Lucide React (icons)
- React Scripts 5.0

### Backend
- FastAPI 0.104.1
- Boto3 (AWS SDK)
- Python 3.8+
- Uvicorn (ASGI server)

## Quick Start

### Prerequisites
- Node.js 14+ and npm
- Python 3.8+
- AWS Account with S3 access

### 1. Frontend Setup

```bash
cd client
npm install
npm start
```

The React app will open at [http://localhost:3000](http://localhost:3000)

### 2. Backend Setup

```bash
cd server
pip install -r requirements.txt

# Configure AWS credentials
cp .env.example .env
# Edit .env with your AWS credentials

# Create S3 bucket
aws s3 mb s3://casebase-pdfs --region us-east-1

# Run the server
python main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

- `POST /api/pdfs/upload` - Upload single PDF
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `GET /api/pdfs` - List all PDFs
- `DELETE /api/pdfs/{s3_key}` - Delete a PDF
- `GET /api/pdfs/{s3_key}/download-url` - Get presigned download URL

## Component Overview

### PDFUploader
- Drag-and-drop file upload
- Multiple PDF file support
- Visual feedback and validation

### PDFViewer
- List of all uploaded documents
- File metadata display (name, size, upload time)
- Delete functionality with hover effects

### Chatbot
- Interactive chat interface
- Message history and typing indicator
- Context-aware responses
- Ready for backend integration

## Configuration

### Frontend
No configuration needed for basic setup. The app is configured to work with the backend at `http://localhost:8000`.

### Backend
Required environment variables in `server/.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=casebase-pdfs
ALLOWED_ORIGINS=http://localhost:3000
```

## Development

### Running Both Services

**Terminal 1 (Frontend):**
```bash
cd client
npm start
```

**Terminal 2 (Backend):**
```bash
cd server
python main.py
```

## Future Enhancements

- Connect chatbot to AI backend for document analysis
- PDF text extraction and indexing
- Vector search for semantic document queries
- User authentication (JWT)
- Real-time document processing status
- Background task processing
- Rate limiting and file size validation

## Security Considerations

1. Never commit `.env` file with credentials
2. Use IAM roles in production
3. Configure S3 bucket policies
4. Enable S3 encryption
5. Implement authentication before production deployment

## License

Private - CaseBase Platform

## Support

For issues or questions, please refer to the documentation in the respective `client/` and `server/` directories.

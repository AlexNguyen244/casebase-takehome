# CaseBase Backend

FastAPI backend for the CaseBase platform with AWS S3 integration for PDF document management.

## Features

- **PDF Upload**: Single and multiple file upload endpoints
- **AWS S3 Integration**: Secure storage of PDF documents in S3
- **CRUD Operations**: List, upload, and delete PDFs
- **Presigned URLs**: Generate temporary download links for PDFs
- **CORS Enabled**: Ready for React frontend integration
- **File Validation**: Ensures only PDF files are uploaded

## Tech Stack

- FastAPI 0.104.1
- Boto3 (AWS SDK)
- Python 3.8+
- Uvicorn (ASGI server)

## Prerequisites

- Python 3.8 or higher
- AWS Account with S3 access
- AWS credentials (Access Key ID and Secret Access Key)

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials:

```env
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=casebase-pdfs

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 3. Create S3 Bucket

Create an S3 bucket in your AWS account:

```bash
aws s3 mb s3://casebase-pdfs --region us-east-1
```

Or use the AWS Console to create a bucket named `casebase-pdfs`.

### 4. Configure S3 Bucket CORS (Optional)

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

### 5. Run the Server

```bash
# From the backend directory
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

- `POST /api/pdfs/upload` - Upload a single PDF
- `POST /api/pdfs/upload-multiple` - Upload multiple PDFs
- `GET /api/pdfs` - List all PDFs
- `DELETE /api/pdfs/{s3_key}` - Delete a PDF
- `GET /api/pdfs/{s3_key}/download-url` - Get presigned download URL

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example Usage

### Upload a PDF

```bash
curl -X POST "http://localhost:8000/api/pdfs/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### List All PDFs

```bash
curl -X GET "http://localhost:8000/api/pdfs"
```

### Delete a PDF

```bash
curl -X DELETE "http://localhost:8000/api/pdfs/pdfs/20231208_120000_document.pdf"
```

### Get Download URL

```bash
curl -X GET "http://localhost:8000/api/pdfs/pdfs/20231208_120000_document.pdf/download-url"
```

## Project Structure

```
backend/
├── main.py              # FastAPI application and endpoints
├── config.py            # Configuration and settings
├── s3_service.py        # AWS S3 service layer
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # This file
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

## Future Enhancements

- Add user authentication (JWT tokens)
- Implement PDF text extraction
- Add vector database integration for semantic search
- Rate limiting
- File size limits and validation
- Virus scanning
- Metadata indexing
- Background task processing with Celery

# Frontend-Backend Integration

## Changes Made

### Backend (Server)
- FastAPI server running on `http://localhost:8000`
- AWS S3 integration for PDF storage
- CORS enabled for React frontend
- Endpoints ready for PDF upload, list, and delete operations

### Frontend (Client)

#### App.js
- Added `API_BASE_URL` constant pointing to backend
- Implemented `fetchPDFs()` to load PDFs from backend on mount
- Updated `handlePDFUpload()` to send files to backend via FormData
- Updated `handleDeletePDF()` to call backend DELETE endpoint
- Added `isLoading` state to track upload progress
- All PDFs now stored in S3 instead of local state

#### PDFUploader.js
- Added `isLoading` prop to show upload progress
- Imported `Loader2` icon from lucide-react
- Shows spinning loader icon during upload
- Changes text to "Uploading to AWS S3..." during upload
- Disables file input and drag-drop during upload
- Opacity reduced and cursor changed to not-allowed during upload

#### PDFViewer.js
- Updated delete handler to use `s3_key` instead of `id`
- Compatible with backend S3 key format

## Features

### Loading States
✅ Spinning loader icon appears during upload
✅ Upload area shows "Uploading to AWS S3..." text
✅ Upload area disabled during upload (no multiple uploads)
✅ Loading stops automatically when upload completes
✅ Multiple files uploaded in parallel

### Backend Integration
✅ PDFs uploaded to AWS S3
✅ PDFs fetched from backend on page load
✅ Delete operations sync with backend
✅ File metadata stored (name, size, upload time)

## Testing

1. Start backend: `cd server && python3 main.py`
2. Start frontend: `cd client && npm start`
3. Upload a PDF - you should see:
   - Spinning loader icon
   - "Uploading to AWS S3..." text
   - Upload area disabled
   - PDF appears in list after upload completes

## API Endpoints Used

- `GET /api/pdfs` - Fetch all PDFs
- `POST /api/pdfs/upload` - Upload single PDF
- `DELETE /api/pdfs/{s3_key}` - Delete PDF

## Next Steps

- Configure AWS credentials in `server/.env`
- Create S3 bucket
- Test full upload flow with real AWS credentials

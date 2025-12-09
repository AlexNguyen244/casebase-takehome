import { useState, useEffect } from 'react';
import PDFViewer from './components/PDFViewer';
import Chatbot from './components/Chatbot';

// Use environment variable for API URL (falls back to localhost for development)
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [uploadedPDFs, setUploadedPDFs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch PDFs from backend on mount
  useEffect(() => {
    fetchPDFs();
  }, []);

  const fetchPDFs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdfs`);
      const data = await response.json();

      if (data.data) {
        const formattedPDFs = data.data.map(pdf => ({
          id: pdf.s3_key,
          name: pdf.file_name,
          size: pdf.file_size,
          uploadedAt: pdf.last_modified,
          s3_key: pdf.s3_key,
          s3_url: pdf.s3_url
        }));
        setUploadedPDFs(formattedPDFs);
      }
    } catch (error) {
      console.error('Error fetching PDFs:', error);
    }
  };

  const handlePDFUpload = async (files) => {
    setIsLoading(true);
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch(`${API_BASE_URL}/api/pdfs/upload`, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (response.ok && result.s3_data) {
          return {
            id: result.s3_data.s3_key,
            name: result.s3_data.file_name,
            size: result.s3_data.file_size,
            uploadedAt: result.s3_data.uploaded_at,
            s3_key: result.s3_data.s3_key,
            s3_url: result.s3_data.s3_url
          };
        } else {
          console.error('Upload failed:', result);
          return null;
        }
      } catch (error) {
        console.error('Error uploading file:', error);
        return null;
      }
    });

    const results = await Promise.all(uploadPromises);
    const successfulUploads = results.filter(pdf => pdf !== null);

    setUploadedPDFs([...uploadedPDFs, ...successfulUploads]);
    setIsLoading(false);
  };

  const handleDeletePDF = async (s3_key) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdfs/${s3_key}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setUploadedPDFs(uploadedPDFs.filter((pdf) => pdf.s3_key !== s3_key));
      } else {
        console.error('Delete failed');
      }
    } catch (error) {
      console.error('Error deleting PDF:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">CaseBase</h1>
          <p className="text-gray-600">Community Supervision Platform</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chatbot takes up 2 columns */}
          <div className="lg:col-span-2">
            <Chatbot uploadedPDFs={uploadedPDFs} />
          </div>

          {/* Document list takes up 1 column on the right */}
          <div className="lg:col-span-1">
            <PDFViewer
              pdfs={uploadedPDFs}
              onDelete={handleDeletePDF}
              onUpload={handlePDFUpload}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

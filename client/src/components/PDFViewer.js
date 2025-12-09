import React, { useRef } from 'react';
import { FileText, Trash2, Plus } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const PDFViewer = ({ pdfs, onDelete, onUpload, isLoading }) => {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files);
      e.target.value = '';
    }
  };

  const handlePdfClick = async (pdf) => {
    // Get presigned URL from backend and open in new tab
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdfs/${encodeURIComponent(pdf.s3_key)}/download-url`);
      const data = await response.json();

      if (response.ok && data.url) {
        window.open(data.url, '_blank');
      } else {
        console.error('Failed to get download URL:', data);
        alert('Unable to open PDF. The download link may have expired or the file may not be accessible.');
      }
    } catch (error) {
      console.error('Error opening PDF:', error);
      alert('Error opening PDF. Please try again later.');
    }
  };
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-[700px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">
          Documents ({pdfs.length})
        </h2>
        <button
          onClick={() => !isLoading && fileInputRef.current?.click()}
          disabled={isLoading}
          className="bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-all"
          title="Upload PDF documents"
        >
          <Plus className="w-5 h-5" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          onChange={handleFileChange}
          className="hidden"
          disabled={isLoading}
        />
      </div>

      {pdfs.length === 0 ? (
        <div className="text-center py-12 flex-1 flex flex-col items-center justify-center">
          <div className="bg-gray-100 rounded-full p-4 w-16 h-16 mb-4 flex items-center justify-center">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500">No documents yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Click the + button above to upload
          </p>
        </div>
      ) : (
        <div className="space-y-3 flex-1 overflow-y-auto">
          {pdfs.map((pdf) => (
            <div
              key={pdf.id}
              className="flex items-start justify-between p-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all group cursor-pointer"
              onClick={() => handlePdfClick(pdf)}
            >
              <div className="flex items-start space-x-3 flex-1 min-w-0">
                <div className="bg-red-100 rounded p-2 flex-shrink-0">
                  <FileText className="w-4 h-4 text-red-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-800 truncate" title={pdf.name}>
                    {pdf.name}
                  </p>
                  <div className="flex flex-col mt-1">
                    <span className="text-xs text-gray-500">
                      {formatFileSize(pdf.size)}
                    </span>
                    <span className="text-xs text-gray-400">
                      {formatDate(pdf.uploadedAt)}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(pdf.s3_key || pdf.id);
                }}
                className="ml-2 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-all opacity-0 group-hover:opacity-100"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PDFViewer;

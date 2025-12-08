import React from 'react';
import { FileText, Trash2 } from 'lucide-react';

const PDFViewer = ({ pdfs, onDelete }) => {
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
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">
        Uploaded Documents ({pdfs.length})
      </h2>

      {pdfs.length === 0 ? (
        <div className="text-center py-12">
          <div className="bg-gray-100 rounded-full p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500">No documents uploaded yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Upload PDFs to get started
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {pdfs.map((pdf) => (
            <div
              key={pdf.id}
              className="flex items-start justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start space-x-3 flex-1 min-w-0">
                <div className="bg-red-100 rounded p-2 flex-shrink-0">
                  <FileText className="w-5 h-5 text-red-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 truncate">
                    {pdf.name}
                  </p>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className="text-xs text-gray-500">
                      {formatFileSize(pdf.size)}
                    </span>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-xs text-gray-500">
                      {formatDate(pdf.uploadedAt)}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => onDelete(pdf.s3_key || pdf.id)}
                className="ml-3 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-all opacity-0 group-hover:opacity-100"
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

import { useRef } from 'react';
import { Upload, Loader2 } from 'lucide-react';

const PDFUploader = ({ onUpload, isLoading }) => {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files);
      e.target.value = '';
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const pdfFiles = Array.from(files).filter(
        file => file.type === 'application/pdf'
      );
      if (pdfFiles.length > 0) {
        onUpload(pdfFiles);
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Upload Documents</h2>

      <div
        className={`border-2 border-dashed border-blue-300 rounded-lg p-8 text-center transition-all ${
          isLoading
            ? 'cursor-not-allowed opacity-60'
            : 'cursor-pointer hover:border-blue-500 hover:bg-blue-50'
        }`}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
      >
        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="bg-blue-100 rounded-full p-4">
            {isLoading ? (
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            ) : (
              <Upload className="w-8 h-8 text-primary" />
            )}
          </div>
          <div>
            <p className="text-lg font-medium text-gray-700">
              {isLoading ? 'Uploading to AWS S3...' : 'Drop PDF files here or click to browse'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {isLoading ? 'Please wait while your files are being uploaded' : 'Support for multiple PDF files'}
            </p>
          </div>
        </div>

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
    </div>
  );
};

export default PDFUploader;

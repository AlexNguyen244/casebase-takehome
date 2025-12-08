# RAG System Documentation

## Overview

This RAG (Retrieval-Augmented Generation) system parses PDF documents, chunks them semantically, generates embeddings, and stores them in Pinecone for efficient vector search.

## Architecture

The system follows a multi-step pipeline:

### Step 1: PDF Parsing (`pdf_parser.py`)
- Uses `pdfplumber` to extract text from PDF files
- Extracts text page-by-page with metadata
- Returns full text content and page information

### Step 2: Semantic Chunking (`chunking_service.py`)
- Uses LangChain's `RecursiveCharacterTextSplitter` for structure-aware splitting
- Respects natural text boundaries (paragraphs, sentences, words)
- Token-based enforcement using GPT2 tokenizer

### Step 3: Token Limit Enforcement
- Target: 400 tokens per chunk (configurable)
- If chunk exceeds limit, splits by tokens with overlap (50 tokens default)
- Ensures no chunk exceeds the specified token limit

### Step 4: Embedding Generation (`embedding_service.py`)
- Uses OpenAI's `text-embedding-3-small` model
- Generates 1536-dimensional embeddings
- Batch processing for efficiency

### Step 5: Vector Storage (`pinecone_service.py`)
- Stores embeddings in Pinecone vector database
- Supports cosine similarity search
- Metadata includes file name, chunk ID, page number, and original text

## Services

### PDF Parser (`pdf_parser.py`)
```python
await pdf_parser.parse_pdf(file_content, file_name)
```

### Chunking Service (`chunking_service.py`)
```python
chunks = chunking_service.chunk_with_metadata(text, file_name, page_number)
```

**Configuration:**
- `target_tokens`: Maximum tokens per chunk (default: 400)
- `overlap_tokens`: Overlap between chunks (default: 50)

### Embedding Service (`embedding_service.py`)
```python
embedding_service = EmbeddingService(api_key=openai_key)
chunks_with_embeddings = await embedding_service.embed_chunks(chunks)
```

### Pinecone Service (`pinecone_service.py`)
```python
pinecone_service = PineconeService(
    api_key=pinecone_key,
    index_name="casebase-documents",
    dimension=1536
)
await pinecone_service.upsert_chunks(chunks, file_name)
```

### RAG Service (`rag_service.py`)
Orchestrates the complete pipeline:
```python
rag_service = RAGService(embedding_service, pinecone_service)
result = await rag_service.process_pdf(file_content, file_name)
```

## API Endpoints

### Upload PDF
```
POST /api/pdfs/upload
```
Uploads PDF to S3 and processes through RAG pipeline.

**Response:**
```json
{
  "message": "PDF uploaded and processed successfully",
  "s3_data": { ... },
  "rag_data": {
    "file_name": "document.pdf",
    "total_pages": 10,
    "total_chunks": 45,
    "max_tokens_per_chunk": 398,
    "upserted_count": 45
  }
}
```

### Query Documents
```
POST /api/rag/query?query=<your_question>&top_k=5&file_name=<optional>
```

**Parameters:**
- `query`: Natural language question
- `top_k`: Number of results (default: 5)
- `file_name`: Optional file filter

**Response:**
```json
{
  "message": "Query completed successfully",
  "data": {
    "query": "What is the main topic?",
    "results_count": 5,
    "results": [
      {
        "id": "document.pdf_0_abc123",
        "score": 0.85,
        "metadata": {
          "file_name": "document.pdf",
          "chunk_text": "...",
          "page_number": 1
        }
      }
    ]
  }
}
```

### Delete PDF
```
DELETE /api/pdfs/{s3_key}
```
Deletes PDF from S3 and removes vectors from Pinecone.

## Configuration

Add to `.env`:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=casebase-documents
PINECONE_DIMENSION=1536
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

## How It Works

### Upload Flow
1. User uploads PDF via `/api/pdfs/upload`
2. PDF saved to S3
3. PDF parsed using pdfplumber
4. Text chunked using RecursiveCharacterTextSplitter
5. Chunks validated against 400 token limit
6. Embeddings generated using OpenAI
7. Vectors stored in Pinecone with metadata

### Query Flow
1. User sends query via `/api/rag/query`
2. Query text converted to embedding
3. Pinecone performs cosine similarity search
4. Top-k most relevant chunks returned
5. Results include original text, file name, page number

## Chunking Strategy

Following the reference implementation in `chunk.py`:

1. **Phase 1: Semantic Splitting**
   - Uses RecursiveCharacterTextSplitter
   - Initial chunk_size: 2000 characters
   - Separators: `\n\n` → `\n` → `. ` → ` ` → ``
   - Preserves document structure

2. **Phase 2: Token Enforcement**
   - Count tokens using GPT2 tokenizer
   - If chunk ≤ 400 tokens: keep as-is
   - If chunk > 400 tokens: split by tokens with 50-token overlap

## Benefits

- **Semantic Chunking**: Respects natural text boundaries
- **Token Control**: Guarantees chunks fit within model limits
- **Efficient Search**: Vector embeddings enable semantic similarity
- **Metadata Rich**: Track source file and page numbers
- **Scalable**: Pinecone handles millions of vectors

## Testing

Example query flow:
```python
# Upload a PDF
response = await client.post("/api/pdfs/upload", files={"file": pdf_file})

# Query the document
results = await client.post("/api/rag/query?query=What are the key findings?&top_k=3")
```

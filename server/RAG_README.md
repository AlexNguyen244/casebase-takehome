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

## Chat Service (`chat_service.py`)

The Chat Service extends the RAG system with conversational AI capabilities.

### Features

1. **Chat with Documents**
   - Uses RAG to retrieve relevant context
   - Generates AI responses using OpenAI GPT-4o-mini
   - Tracks source documents used in responses

2. **Intent Detection**
   - PDF creation intent (conversation history or document content)
   - Email sending intent
   - Document sending intent

3. **Source Attribution**
   - AI explicitly reports which documents it used
   - Filters out irrelevant documents
   - Ensures accurate citation

### Usage

```python
# Chat with documents
result = await chat_service.chat_with_documents(
    message="What experience does Alex have with AWS?",
    conversation_history=[],
    top_k=5
)

# Detect PDF creation intent
intent = await chat_service.detect_pdf_creation_intent(
    "Create a PDF comparing the two resumes"
)
# Returns: {"is_pdf_request": True, "type": "vector_content"}

# Detect email intent
email_intent = await chat_service.detect_email_intent(
    "Email this to alex@example.com"
)
# Returns: {"wants_email": True, "email_address": "alex@example.com"}

# Detect send documents intent
send_intent = await chat_service.detect_send_documents_intent(
    "Send me all documents relating to Alex to alex@example.com"
)
# Returns: {"wants_send_docs": True, "email_address": "alex@example.com", "topic": "Alex"}
```

## PDF Generation (`pdf_generator.py`)

Generates professional PDFs using ReportLab.

### Features

- Markdown support (headers, lists, code blocks, tables)
- Source document attribution (listed at end of PDF)
- Professional styling with custom colors
- Automatic page breaks and spacing

### Usage

```python
# Generate PDF from prompt/response
pdf_bytes = pdf_generator.generate_from_prompt(
    prompt="What is Alex's AWS experience?",
    response="Alex has 3 years of experience...",
    source_documents=["AlexNguyen-Resume.pdf"]
)

# Generate PDF from chat history
pdf_bytes = pdf_generator.generate_from_chat_history(
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ],
    title="Conversation Summary"
)
```

## Email Service (`email_service.py`)

Sends PDFs and documents via SendGrid.

### Methods

```python
# Send single PDF
await email_service.send_pdf_email(
    to_email="user@example.com",
    subject="Your Report",
    pdf_bytes=pdf_bytes,
    pdf_filename="report.pdf"
)

# Send multiple documents
await email_service.send_documents_email(
    to_email="user@example.com",
    subject="Requested Documents",
    documents=[
        {"bytes": pdf1_bytes, "filename": "doc1.pdf"},
        {"bytes": pdf2_bytes, "filename": "doc2.pdf"}
    ]
)
```

## Advanced Features

### AI-Powered Document Filtering

When sending existing documents, the system uses AI to filter only relevant documents:

```python
# User request: "Send me all files relating to Alex to alex@example.com"
# System:
# 1. Retrieves chunks about "Alex" from vector DB
# 2. AI analyzes which documents are actually about Alex
# 3. Filters out documents that only mention Alex in passing
# 4. Sends only the relevant documents
```

### Source Attribution in PDFs

When generating PDFs from document content:

```python
# 1. Retrieve relevant chunks from vector DB
# 2. AI generates response using chunks
# 3. AI reports which source documents it actually used
# 4. PDF includes "Source Documents" section at the end
# 5. Only cited sources are listed (not all retrieved documents)
```

### Multi-Intent Chat Endpoint

The `/api/chat` endpoint automatically handles:

1. **Normal chat**: Returns AI response with sources
2. **PDF creation**: Generates PDF and returns download link
3. **Email PDF**: Creates and emails PDF to specified address
4. **Send documents**: Filters and emails existing documents

All through natural language requests!

## Testing

Example workflows:

```python
# Upload a PDF
response = await client.post("/api/pdfs/upload", files={"file": pdf_file})

# Query the document
results = await client.post("/api/rag/query?query=What are the key findings?&top_k=3")

# Chat with documents
chat_response = await client.post("/api/chat", json={
    "message": "What are the main points?",
    "conversation_history": []
})

# Request PDF creation via chat
pdf_response = await client.post("/api/chat", json={
    "message": "Create a PDF summarizing the key findings"
})

# Request PDF via email
email_response = await client.post("/api/chat", json={
    "message": "Create a PDF and email to user@example.com"
})

# Request existing documents
docs_response = await client.post("/api/chat", json={
    "message": "Send all documents about AWS to user@example.com"
})
```

## Performance Considerations

- All services use `async/await` for optimal performance
- Embedding generation is batched for efficiency
- Pinecone queries are fast (milliseconds)
- AI responses cached where appropriate
- Docker deployment for production scalability

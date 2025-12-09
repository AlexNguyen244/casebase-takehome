# Intent Detection System Documentation

## Overview

The CaseBase AI platform features a sophisticated multi-intent detection system that intelligently routes user requests to the appropriate handlers. The system uses OpenAI's GPT models to analyze natural language messages and determine user intent with high accuracy.

## Intent Detection Architecture

### Priority-Based Routing

The system implements a **priority-based intent detection** mechanism to ensure the most relevant intent is triggered when multiple intents could potentially match. This is crucial for handling ambiguous pronouns like "those", "them", or "these" in conversation.

### Intent Detection Flow

```
User Message
     |
     v
Email Intent Detection
     |
     v
Context Analysis (check for recent PDFs & keywords)
     |
     v
Priority Check:
     |
     ├─> If has_recent_pdfs AND user_wants_to_send AND NOT user_wants_sources
     |   └─> Bulk Send Intent Check (HIGH PRIORITY)
     |
     ├─> If NOT bulk_send triggered
     |   └─> Send Documents Intent Check
     |
     └─> If NOT (bulk_send triggered OR user_wants_sources)
         └─> Send Source Docs Intent Check
```

## Intent Types

### 1. Email Intent Detection (`detect_email_intent`)

**Purpose**: Detect if the user wants to email something and extract the email address.

**Location**: `chat_service.py:182-306`

**Features**:
- Remembers previously mentioned email addresses from conversation history
- Validates email format with regex
- Uses last 3 exchanges for context

**Returns**:
```python
{
    "wants_email": bool,
    "email_address": str or None
}
```

**Example Triggers**:
- "Email this to alex@example.com"
- "Send to me" (uses remembered email)
- "alex@gmail.com" (email only)

---

### 2. PDF Creation Intent Detection (`detect_pdf_creation_intent`)

**Purpose**: Determine if user wants to create a PDF and what type.

**Location**: `chat_service.py:308-398`

**PDF Types**:
- `"history"` - Create PDF from chat conversation history
- `"vector_content"` - Create PDF from document content in vector database
- `"chat"` - Normal conversation, not PDF creation

**Features**:
- Uses conversation context to resolve pronouns ("it", "that", "this")
- Distinguishes between creating new PDFs vs referencing existing ones

**Returns**:
```python
{
    "is_pdf_request": bool,
    "type": "history" | "vector_content" | "chat"
}
```

**Example Triggers**:
- "Create a PDF about AWS skills" → `vector_content`
- "Make a PDF of our conversation" → `history`
- "Generate a report on..." → `vector_content`

---

### 3. Send Documents Intent Detection (`detect_send_documents_intent`)

**Purpose**: Detect if user wants to send existing documents from the vector database.

**Location**: `chat_service.py:400-504`

**Features**:
- AI-powered document filtering by topic/subject
- Searches vector database for relevant documents
- Filters out documents that only mention topic in passing

**Returns**:
```python
{
    "wants_send_docs": bool,
    "email_address": str or None,
    "topic": str or None
}
```

**Example Triggers**:
- "Find documents and send to alex@email.com"
- "Send me all documents relating to Alex"
- "Email me files about healthcare"

**Priority**: Checked AFTER bulk_send_intent to avoid conflicting with generated PDFs

---

### 4. Bulk PDF Send Intent Detection (`detect_bulk_pdf_send_intent`) ⭐ NEW PRIORITY LOGIC

**Purpose**: Detect if user wants to send previously generated PDFs from the conversation.

**Location**: `chat_service.py:506-653`

**Selection Types**:
- `"all"` - Send all generated PDFs
- `"last_n"` - Send last N PDFs (e.g., "last 3 PDFs")
- `"last"` - Send just the last PDF

**Features**:
- Extracts all generated PDFs from conversation history
- Recognizes pronouns like "those", "them", "these" when referring to PDFs
- **PRIORITY HANDLING**: Checked FIRST when recent PDFs exist and user wants to send

**Returns**:
```python
{
    "wants_bulk_send": bool,
    "email_address": str or None,
    "selection_type": "all" | "last_n" | "last",
    "count": int or None
}
```

**Example Triggers**:
- "Send all the PDFs to alex@email.com" → `all`
- "Email me the last 3 PDFs" → `last_n`, count=3
- "Send those to my email" → `all` or `last` (context-dependent)
- "Email the last PDF to user@domain.org" → `last`

**NEW in v2.0**:
- Enhanced prompt with explicit pronoun handling
- Added "Send those to my email" examples
- Improved context awareness for recent PDFs

---

### 5. Send Source Docs Intent Detection (`detect_send_source_docs_intent`) ⭐ UPDATED

**Purpose**: Detect if user wants to send source documents that were used to generate PDFs.

**Location**: `chat_service.py:661-805`

**Scopes**:
- `"all"` - Sources from all generated PDFs
- `"last_pdf"` - Sources from last PDF only
- `"those"` - Sources from recently mentioned PDFs
- `"last_n_pdfs"` - Sources from last N PDFs

**Features**:
- Retrieves PDF metadata to get source document list
- **CRITICAL REQUIREMENT**: User MUST explicitly mention "source", "sources", "original documents", etc.
- Downloads original source files from S3
- **PRIORITY HANDLING**: Only checked if bulk_send didn't trigger AND user mentions "source"

**Returns**:
```python
{
    "wants_send_sources": bool,
    "email_address": str or None,
    "scope": str or None,
    "count": int or None
}
```

**Example Triggers**:
- "Send me the sources for those PDFs" → `those`
- "Email the source documents to alex@email.com" → `all`
- "Send me the original documents used to create that" → `last_pdf`

**NEW in v2.0**:
- **CRITICAL UPDATE**: Now requires explicit "source" keyword
- Will NOT trigger for "Send those" without "source" mention
- Prevents incorrect triggering when user wants generated PDFs

---

## Priority Logic Implementation

### Context-Based Prioritization (NEW in v2.0)

**Location**: `routes/chat.py:181-208`

The system now performs intelligent context analysis before intent detection:

```python
# Step 1: Check for recently generated PDFs
all_generated_pdfs = extract_generated_pdfs_from_history(history)
has_recent_pdfs = len(all_generated_pdfs) > 0

# Step 2: Detect sending keywords
send_keywords = ['send', 'email', 'those', 'them', 'these', 'the pdfs', 'the pdf']
user_wants_to_send = any(keyword in request.message.lower() for keyword in send_keywords)

# Step 3: Check for source document keywords
source_keywords = ['source', 'sources', 'source documents', 'original documents', 'source files']
user_wants_sources = any(keyword in request.message.lower() for keyword in source_keywords)

# Step 4: Priority check
if has_recent_pdfs and user_wants_to_send and not user_wants_sources:
    # Check bulk_send_intent FIRST
    bulk_send_intent = await chat_service.detect_bulk_pdf_send_intent(...)
```

### Priority Rules

1. **HIGHEST PRIORITY**: Bulk Send Intent
   - **When**: Recent PDFs exist AND user wants to send AND NO "source" keyword
   - **Why**: User saying "send those" most likely means the PDFs they just created
   - **Example**: After creating 2 PDFs, "Send those to my email" → Sends the 2 generated PDFs

2. **MEDIUM PRIORITY**: Send Documents Intent
   - **When**: Bulk send didn't trigger OR no recent PDFs
   - **Why**: User wants to search and send existing documents from vector DB
   - **Example**: "Send me documents about healthcare" → Searches vector DB

3. **LOW PRIORITY**: Send Source Docs Intent
   - **When**: Bulk send didn't trigger AND user mentions "source"
   - **Why**: User explicitly wants source documents, not generated PDFs
   - **Example**: "Send me the sources for those PDFs" → Sends original source files

### Skip Logic

**Send Docs Intent Skip** (`routes/chat.py:207-208`):
```python
if not skip_send_docs_check and (not bulk_send_intent or not bulk_send_intent.get("wants_bulk_send")):
    send_docs_intent = await chat_service.detect_send_documents_intent(...)
```

**Send Source Docs Intent Skip** (`routes/chat.py:505-506`):
```python
if not (bulk_send_intent and bulk_send_intent.get("wants_bulk_send")):
    send_source_docs_intent = await chat_service.detect_send_source_docs_intent(...)
```

## User Experience Scenarios

### Scenario 1: Sending Generated PDFs (NEW Behavior)

```
User: "Create PDF for Alex's skills"
Bot: [Creates PDF 1]

User: "Create PDF for Casebase role"
Bot: [Creates PDF 2]

User: "Send those to my email"
System Logic:
  ✓ has_recent_pdfs = True (2 PDFs found)
  ✓ user_wants_to_send = True ("send" detected)
  ✓ user_wants_sources = False (no "source" keyword)
  → Triggers bulk_send_intent FIRST
  → Sends the 2 generated PDFs ✅

Result: User receives the 2 generated PDFs they created
```

### Scenario 2: Sending Source Documents (NEW Behavior)

```
User: "Create PDF for Alex's skills"
Bot: [Creates PDF using AlexNguyen-Resume.pdf]

User: "Send me the sources for that"
System Logic:
  ✓ has_recent_pdfs = True (1 PDF found)
  ✓ user_wants_to_send = True ("send" detected)
  ✓ user_wants_sources = True ("sources" detected)
  → SKIPS bulk_send_intent priority check
  → Triggers send_source_docs_intent instead
  → Retrieves PDF metadata
  → Finds AlexNguyen-Resume.pdf in metadata
  → Sends the original resume ✅

Result: User receives the original source document
```

### Scenario 3: Sending Existing Documents

```
User: "Send me documents about healthcare to alex@email.com"
System Logic:
  ✗ has_recent_pdfs = False (no recent PDFs)
  ✓ user_wants_to_send = True ("send" detected)
  ✗ user_wants_sources = False (no "source" keyword)
  → SKIPS bulk_send_intent (no recent PDFs)
  → Triggers send_docs_intent
  → Searches vector DB for "healthcare"
  → AI filters relevant documents
  → Sends matching documents ✅

Result: User receives existing documents about healthcare
```

### Scenario 4: Mixed Request

```
User: "Create PDF for Alex's skills"
Bot: [Creates PDF]

User: "Send me those sources and also documents about CaseBase to alex@email.com"
System Logic:
  ✓ user_wants_sources = True ("sources" detected)
  → Triggers send_source_docs_intent
  → Processes "those sources" part
  → Also might trigger send_docs_intent for "documents about CaseBase"

Result: Handles complex multi-intent request appropriately
```

## Email Memory System

### How Email Memory Works

The system automatically remembers email addresses from previous messages in the conversation:

**Location**: `utils/helpers.py:14-33`

```python
def extract_most_recent_email_from_history(conversation_history: List[Dict]) -> Optional[str]:
    """
    Extract the most recently mentioned email address from conversation history.
    Searches from newest to oldest messages.
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Search from newest to oldest
    for msg in reversed(conversation_history):
        content = msg.get('content', '')
        matches = re.findall(email_pattern, content)
        if matches:
            return matches[-1]  # Return the last email found in the message

    return None
```

### Email Memory Examples

```
Example 1: First Email Remembered
User: "Send PDF to alex@example.com"
Bot: [Sends PDF, remembers alex@example.com]

User: "Send me another PDF"
Bot: [Uses remembered alex@example.com]

Example 2: Email Override
User: "Send PDF to alex@example.com"
Bot: [Remembers alex@example.com]

User: "Send to john@test.com instead"
Bot: [Uses john@test.com, now remembered]
```

## PDF Tracking System

### Extracting Generated PDFs

**Location**: `utils/helpers.py:36-68`

The system tracks all generated PDFs by parsing assistant messages for PDF download URLs:

```python
def extract_generated_pdfs_from_history(history: List[Dict]) -> List[Dict]:
    """
    Extract all generated PDF S3 keys from conversation history.

    Returns:
        List of dicts with 's3_key', 'timestamp', 'filename' for each PDF
    """
    generated_pdfs = []
    s3_key_pattern = r'/api/pdfs/view/(generated_pdfs/[^\s\)]+\.pdf)'

    for msg in history:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if 'Download PDF' in content or '/api/pdfs/view/' in content:
                matches = re.findall(s3_key_pattern, content)
                for s3_key in matches:
                    # Extract timestamp from S3 key
                    # Format: generated_pdfs/20251209_195408_document_content.pdf
                    timestamp_match = re.search(r'generated_pdfs/(\d{8}_\d{6})_', s3_key)

                    generated_pdfs.append({
                        's3_key': s3_key,
                        'timestamp': timestamp_match.group(1) if timestamp_match else None,
                        'filename': s3_key.split('/')[-1]
                    })

    return generated_pdfs
```

### PDF Tracking Examples

```
Conversation:
Assistant: "I've created your PDF! Download: /api/pdfs/view/generated_pdfs/20251209_195408_alex_skills.pdf"
Assistant: "Here's another PDF: /api/pdfs/view/generated_pdfs/20251209_195420_casebase_role.pdf"

Extracted PDFs:
[
    {
        's3_key': 'generated_pdfs/20251209_195408_alex_skills.pdf',
        'timestamp': '20251209_195408',
        'filename': '20251209_195408_alex_skills.pdf'
    },
    {
        's3_key': 'generated_pdfs/20251209_195420_casebase_role.pdf',
        'timestamp': '20251209_195420',
        'filename': '20251209_195420_casebase_role.pdf'
    }
]
```

## Source Document Tracking

### Retrieving Source Documents for PDFs

**Location**: `utils/helpers.py:71-104`

Generated PDFs store metadata about which source documents were used:

```python
def get_source_documents_for_pdf(s3_service, pdf_s3_key: str) -> List[str]:
    """
    Retrieve source document S3 keys from PDF metadata.

    Args:
        s3_service: S3Service instance
        pdf_s3_key: S3 key of the generated PDF

    Returns:
        List of source document S3 keys
    """
    try:
        response = s3_service.s3_client.head_object(
            Bucket=s3_service.bucket_name,
            Key=pdf_s3_key
        )

        metadata = response.get('Metadata', {})
        source_docs_str = metadata.get('source_documents', '')

        if source_docs_str:
            # Split comma-separated S3 keys
            source_docs = [doc.strip() for doc in source_docs_str.split(',')]
            return [doc for doc in source_docs if doc]  # Filter empty strings

        return []

    except Exception as e:
        logger.error(f"Error getting source documents for PDF {pdf_s3_key}: {str(e)}")
        return []
```

### PDF Metadata Storage

When a PDF is generated, metadata is stored in S3:

**Location**: `routes/chat.py:1154-1159` and `1193-1197`

```python
# Store metadata with the PDF
Metadata={
    'generated_at': timestamp,  # When PDF was created
    'type': pdf_intent["type"],  # "history" or "vector_content"
    'source_documents': source_docs_str  # Comma-separated S3 keys
}
```

## Testing Intent Detection

### Manual Testing

```python
# Test bulk send intent
message = "Send those PDFs to alex@example.com"
history = [...]  # Include generated PDF messages
result = await chat_service.detect_bulk_pdf_send_intent(message, history, None)
# Expected: {"wants_bulk_send": True, "email_address": "alex@example.com", ...}

# Test source docs intent
message = "Send me the sources for those"
result = await chat_service.detect_send_source_docs_intent(message, history, "alex@example.com")
# Expected: {"wants_send_sources": True, "email_address": "alex@example.com", "scope": "those"}

# Test send documents intent
message = "Send documents about healthcare to john@test.com"
result = await chat_service.detect_send_documents_intent(message, [], None)
# Expected: {"wants_send_docs": True, "email_address": "john@test.com", "topic": "healthcare"}
```

### Priority Testing

Test that the priority system works correctly:

```python
# Scenario: Recent PDFs exist + "send those" → Should trigger bulk_send
history_with_pdfs = [
    {"role": "assistant", "content": "Download: /api/pdfs/view/generated_pdfs/20251209_195408_test.pdf"}
]
message = "Send those to alex@email.com"

# Priority check should trigger bulk_send first
all_pdfs = extract_generated_pdfs_from_history(history_with_pdfs)
assert len(all_pdfs) > 0
assert "send" in message.lower()
assert "source" not in message.lower()
# → bulk_send_intent should be checked first

# Scenario: Recent PDFs + "send those sources" → Should trigger send_source_docs
message_with_source = "Send me the sources for those"
assert "source" in message_with_source.lower()
# → Priority check should be skipped, send_source_docs_intent checked instead
```

## Troubleshooting

### Issue: Wrong intent triggered

**Problem**: User says "send those" but wrong documents are sent

**Solution**: Check priority logic
1. Verify recent PDFs exist in conversation history
2. Check if "source" keyword is present (should skip bulk_send priority)
3. Verify bulk_send_intent is being checked first when appropriate

### Issue: Email not remembered

**Problem**: System asks for email even though user provided it before

**Solution**: Check email memory
1. Verify conversation history includes previous messages
2. Check email was in correct format (valid regex)
3. Ensure remembered_email is passed to intent detection functions

### Issue: Source documents not found

**Problem**: System can't find source documents for generated PDF

**Solution**: Check metadata storage
1. Verify PDF metadata was stored correctly in S3
2. Check `source_documents` field in metadata
3. Ensure source document S3 keys are valid and files exist

## Architecture Diagram

```
User Message: "Send those to my email"
        |
        v
    [Email Intent Detection]
        |
        v
    [Context Analysis]
        |
        ├─ Check: Recent PDFs exist? ✓
        ├─ Check: Send keywords present? ✓
        └─ Check: Source keywords present? ✗
        |
        v
    [Priority Decision]
        |
        └─> PRIORITY: Check Bulk Send Intent FIRST
            |
            ├─ Triggers? YES
            |   └─> [Bulk Send Handler]
            |       └─> Extract generated PDFs from history
            |       └─> Download from S3
            |       └─> Send via email
            |
            └─ Triggers? NO
                └─> [Check Send Docs Intent]
                    └─> Search vector DB for documents
                    └─> AI filter relevance
                    └─> Send via email
```

## Key Files

### Intent Detection
- `chat_service.py:182-805` - All intent detection methods
- `routes/chat.py:181-208` - Priority logic implementation
- `routes/chat.py:499-511` - Source docs skip logic

### Helper Functions
- `utils/helpers.py:14-33` - Email extraction
- `utils/helpers.py:36-68` - PDF tracking
- `utils/helpers.py:71-104` - Source document retrieval

### Email Service
- `email_service.py:29-109` - Single PDF email
- `email_service.py:111-208` - PDF with sources email
- `email_service.py:210-290` - Multiple documents email

## Version History

### v2.0 (Latest) - Priority-Based Intent Detection
- ✅ Added priority logic for bulk_send_intent
- ✅ Improved pronoun handling ("those", "them", "these")
- ✅ Enhanced source docs intent to require explicit "source" keyword
- ✅ Skip logic to prevent multiple intents from triggering
- ✅ Context analysis before intent detection

### v1.0 - Initial Multi-Intent System
- Basic intent detection for chat, PDF, email, and bulk send
- Email memory system
- PDF tracking from conversation history
- Source document inclusion in PDFs

## Best Practices

1. **Always provide conversation history** when calling intent detection methods
2. **Pass remembered_email** to enable seamless multi-step interactions
3. **Test with real conversation flows** to validate priority logic
4. **Monitor logs** to see which intents are triggering (`logger.info` statements)
5. **Update prompts carefully** - small changes can affect accuracy

## Future Enhancements

- Machine learning for intent classification (faster than LLM-based)
- Intent confidence scores for better decision making
- Multi-intent support (handle multiple intents in one message)
- User preference learning (remember preferred email format, etc.)
- Intent history tracking and analytics

# PDF Processing for Vector Database

This guide shows how to process PDF documents and add them to your vector database for RAG (Retrieval-Augmented Generation).

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Process a PDF
```python
from vector_db import VectorEmbeddingModel, VectorDatabase

# Initialize
embed_model = VectorEmbeddingModel()
vector_db = VectorDatabase(embed_model)

# Add a PDF
pdf_path = r"c:\path\to\your\document.pdf"
vector_db.add_pdf(pdf_path, metadata={'title': 'My Document', 'author': 'John Doe'})

# Search
results = vector_db.search("your query here")
```

### 3. Use with RAG
```python
# In basic_rag.py, uncomment and modify this line:
add_pdf_to_database(r"c:\Users\ldahl\Downloads\ijspp-article-p1159.pdf", {'title': 'IJSPP Article'})
```

## Features

- **PDF Text Extraction**: Automatically extracts text from PDF files
- **Metadata Support**: Attach metadata to documents for better context
- **Chunking**: Automatically splits documents into manageable chunks
- **Similarity Search**: Find relevant content using vector similarity
- **Source Tracking**: Know which document each result came from

## API Reference

### VectorDatabase.add_pdf(pdf_path, metadata=None)
Add a PDF document to the vector database.

**Parameters:**
- `pdf_path`: Path to the PDF file
- `metadata`: Optional dictionary with document metadata

### VectorDatabase.search(query, k=2)
Search for similar content.

**Parameters:**
- `query`: Search query string
- `k`: Number of results to return

**Returns:**
List of dictionaries with 'text', 'metadata', and 'similarity_score' keys.

## Example Output
```
Query: 'What is the main topic?'
Result 1:
  Text: The main topic of this paper is machine learning applications...
  Source: ijspp-article-p1159.pdf
  Similarity: 0.85
```

## Troubleshooting

- **No text extracted**: Some PDFs may have image-based content. Consider using OCR tools.
- **Large PDFs**: Processing may take time for large documents.
- **Memory usage**: Large document collections may require significant memory.
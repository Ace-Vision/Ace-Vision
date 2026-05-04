# Vector database classes for RAG system

from sentence_transformers import SentenceTransformer
import numpy as np
from PyPDF2 import PdfReader
import os

class VectorEmbeddingModel:
    """Handles text embedding and preprocessing"""
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        return self.model.encode(texts)

    def chunk_text(self, text, chunk_size=50):
        words = text.split()

        return [" ".join(words[i:i+chunk_size])
                for i in range(0, len(words), chunk_size)]

class VectorDatabase:
    """Handles vector storage, indexing, and retrieval"""
    def __init__(self, embedding_model: VectorEmbeddingModel):
        self.embedding_model = embedding_model
        self.chunks = []
        self.embeddings = []
        self.document_metadata = []  # Store metadata about each document

    def extract_text_from_pdf(self, pdf_path):
        """Extract text content from a PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

    def add_pdf(self, pdf_path, metadata=None):
        """Add a PDF document to the vector database"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Extract text from PDF
        pdf_text = self.extract_text_from_pdf(pdf_path)

        if not pdf_text:
            print(f"No text extracted from {pdf_path}")
            return

        # Create metadata for this document
        doc_metadata = {
            'source': pdf_path,
            'type': 'pdf',
            'filename': os.path.basename(pdf_path),
            **(metadata or {})
        }

        # Add the document
        self.add_documents([pdf_text], doc_metadata)

    def add_documents(self, documents, metadata=None):
        """Add documents to the vector database"""
        for i, doc in enumerate(documents):
            # Chunk the document
            doc_chunks = self.embedding_model.chunk_text(doc)

            # Generate embeddings for chunks
            chunk_embeddings = self.embedding_model.encode(doc_chunks)

            # Store chunks and embeddings
            self.chunks.extend(doc_chunks)
            self.embeddings.extend(chunk_embeddings)

            # Store metadata for each chunk (repeating doc metadata for each chunk)
            doc_meta = metadata or {'type': 'text'}
            for _ in doc_chunks:
                self.document_metadata.append(doc_meta)

    def search(self, query, k=2):
        """Search for similar documents"""
        if not self.chunks:
            return []

        # Encode the query
        query_embedding = self.embedding_model.encode([query])[0]

        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding)

        # Get top k indices
        top_k_indices = np.argsort(similarities)[-k:]

        # Return the corresponding chunks with metadata
        results = []
        for idx in top_k_indices:
            results.append({
                'text': self.chunks[idx],
                'metadata': self.document_metadata[idx],
                'similarity_score': similarities[idx]
            })

        return results
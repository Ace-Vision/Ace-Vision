
# Import required modules
from sentence_transformers import SentenceTransformer
import numpy as np
import requests
from vector_db import VectorEmbeddingModel, VectorDatabase  # Import the classes
import os

# Initialize the vector database system
embed_model = VectorEmbeddingModel()
vector_db = VectorDatabase(embed_model)

# Example: Add a PDF to the vector database
def add_pdf_to_database(pdf_path, metadata=None):
    """Helper function to add a PDF to the vector database"""
    try:
        vector_db.add_pdf(pdf_path, metadata)
        print(f"✅ Successfully added PDF: {os.path.basename(pdf_path)}")
        print(f"Total chunks in database: {len(vector_db.chunks)}")
    except Exception as e:
        print(f"❌ Error adding PDF: {e}")

# Uncomment the line below to add your PDF:
add_pdf_to_database(r"c:\Users\ldahl\Downloads\ijspp-article-p1159.pdf", {'title': 'IJSPP Article'})

# Defining a function to query the LLM with retrieved context and the question
def ask_llm(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]

# Main function to perform RAG query
def rag_query(question):
    # Use the VectorDatabase search method instead of the old retrieve function
    search_results = vector_db.search(question)

    # Extract text from search results and include source information
    context_parts = []
    for result in search_results:
        source = result['metadata'].get('filename', 'Unknown source')
        context_parts.append(f"From {source}: {result['text']}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a scientifically accurate tennis coach. Use the followinng numerical data
to provide technical advice on tennis serve improvement.
Max characters in response: 150.
Context:
{context}

Question:
{question}

Answer:
"""

    return ask_llm(prompt)

# Example usage

print(rag_query("Contact angle: 80 degrees,/" \
"Hip angle: 45 degrees,/" \
"Shoulder angle: 30 degrees,/" \
"Knee angle: 20 degrees,/" \
"Elbow angle: 15 degrees,/" \
"Racket head speed: 120 km/h,/"))
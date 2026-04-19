# PDF Processing and Vector Database Example

from vector_db import VectorEmbeddingModel, VectorDatabase
import os

def main():
    # Initialize the vector database system
    print("Initializing vector database...")
    embed_model = VectorEmbeddingModel()
    vector_db = VectorDatabase(embed_model)

    # Path to the PDF file (adjust this path as needed)
    pdf_path = r"c:\Users\ldahl\Downloads\ijspp-article-p1159.pdf"

    # Check if PDF exists
    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")

        # Add the PDF to the vector database
        try:
            vector_db.add_pdf(pdf_path, metadata={'title': 'IJSPP Article', 'year': '2023'})
            print("✅ PDF successfully added to vector database!")
            print(f"Total chunks in database: {len(vector_db.chunks)}")

        except Exception as e:
            print(f"❌ Error processing PDF: {e}")
            return
    else:
        print(f"❌ PDF file not found: {pdf_path}")
        print("Please update the pdf_path variable with the correct file location.")
        return

    # Test search functionality
    print("\n🔍 Testing search functionality...")

    test_queries = [
        "What is the main topic of this paper?",
        "What methodology was used?",
        "What are the key findings?"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = vector_db.search(query, k=2)

        if results:
            for i, result in enumerate(results, 1):
                print(f"Result {i}:")
                print(f"  Text: {result['text'][:200]}...")
                print(f"  Source: {result['metadata'].get('filename', 'Unknown')}")
                print(".4f")
        else:
            print("  No results found")

if __name__ == "__main__":
    main()
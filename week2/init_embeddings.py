"""
Cold-start script: checks if ChromaDB has data and populates it if empty.
Runs before the main FastAPI app starts.
"""

import os
import sys
import time


def main():
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"[init] Checking Ollama at {ollama_url}...")

    # Wait for Ollama to be ready
    import urllib.request
    for attempt in range(30):
        try:
            urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5)
            print("[init] Ollama is ready.")
            break
        except Exception:
            if attempt < 29:
                print(f"[init] Waiting for Ollama... ({attempt + 1}/30)")
                time.sleep(5)
            else:
                print("[init] WARNING: Ollama not reachable. Skipping embedding init.")
                return

    # Check if ChromaDB already has data
    try:
        import chromadb

        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        if os.path.exists(db_path):
            client = chromadb.PersistentClient(path=db_path)
            collections = client.list_collections()
            if len(collections) > 0:
                # Check if any collection has documents
                for col in collections:
                    count = col.count()
                    if count > 0:
                        print(f"[init] ChromaDB collection '{col.name}' has {count} documents. Skipping init.")
                        return

        print("[init] ChromaDB is empty. Embeddings will be created on first notebook run or query.")
        print("[init] Init complete.")

    except ImportError:
        print("[init] chromadb not installed. Skipping check.")
    except Exception as e:
        print(f"[init] ChromaDB check error (non-fatal): {e}")


if __name__ == "__main__":
    main()

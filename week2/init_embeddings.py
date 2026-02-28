"""
Cold-start script: waits for Ollama, pulls required models, checks ChromaDB.
Runs before the main FastAPI app starts.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error


def pull_model(ollama_url, model_name):
    """Pull an Ollama model if not already available."""
    try:
        # Check if model exists
        req = urllib.request.Request(
            f"{ollama_url}/api/tags",
            method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        existing = [m.get("name", "") for m in data.get("models", [])]

        if any(model_name in name for name in existing):
            print(f"[init] Model '{model_name}' already available.")
            return True

        print(f"[init] Pulling model '{model_name}'... (this may take a while)")
        req = urllib.request.Request(
            f"{ollama_url}/api/pull",
            data=json.dumps({"name": model_name, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=600)
        print(f"[init] Model '{model_name}' pulled successfully.")
        return True

    except Exception as e:
        print(f"[init] WARNING: Failed to pull model '{model_name}': {e}")
        return False


def main():
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"[init] Checking Ollama at {ollama_url}...")

    # Wait for Ollama to be ready
    for attempt in range(60):
        try:
            urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5)
            print("[init] Ollama is ready.")
            break
        except Exception:
            if attempt < 59:
                print(f"[init] Waiting for Ollama... ({attempt + 1}/60)")
                time.sleep(5)
            else:
                print("[init] WARNING: Ollama not reachable after 5 minutes. Starting without models.")
                return

    # Pull required models
    pull_model(ollama_url, "qwen3-embedding")
    pull_model(ollama_url, "qwen3:8b")

    # Check if ChromaDB already has data
    try:
        import chromadb

        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        if os.path.exists(db_path):
            client = chromadb.PersistentClient(path=db_path)
            collections = client.list_collections()
            if len(collections) > 0:
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

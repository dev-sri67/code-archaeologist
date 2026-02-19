"""Vector Store - SQLite implementation with local sentence-transformer embeddings.

Uses in-process embedding generation via embedding_service for fast,
batch-capable vector operations with no external API dependencies.
"""
from typing import List, Dict, Any, Optional
import sqlite3
import json
import hashlib
from pathlib import Path
import numpy as np
import logging

from app.services.embedding_service import generate_embedding, generate_embeddings_batch
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class VectorStore:
    """SQLite-based vector store with cosine similarity search."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = Path(persist_dir) if persist_dir else Path(settings.VECTOR_DB_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.persist_dir / "vectors.db"
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    repo_id INTEGER NOT NULL,
                    snippet_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repo ON embeddings(repo_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_snippet ON embeddings(repo_id, snippet_id)")

    def _generate_id(self, repo_id: int, snippet_id: str) -> str:
        """Generate a unique document ID."""
        content = f"{repo_id}:{snippet_id}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_collection(self, repo_id: int):
        """Compatibility method - returns self."""
        return self

    async def add_code_snippet(self, repo_id: int, snippet_id: str, code: str, metadata: Dict):
        """Add a code snippet to the store."""
        doc_id = self._generate_id(repo_id, snippet_id)
        embedding = generate_embedding(code)
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO embeddings
                   (id, repo_id, snippet_id, code, metadata, embedding)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (doc_id, repo_id, snippet_id, code, json.dumps(metadata), embedding_blob)
            )

    async def add_documents_batch(self, repo_id: int, documents: List[Dict]):
        """Add multiple documents with batch embedding generation.

        Generates all embeddings in one batch call, then bulk inserts.
        Much faster than sequential add_code_snippet calls.
        """
        if not documents:
            return

        # Extract all texts for batch embedding
        texts = [doc['code'] for doc in documents]
        embeddings = generate_embeddings_batch(texts)

        with sqlite3.connect(self.db_path) as conn:
            rows = []
            for doc, embedding in zip(documents, embeddings):
                doc_id = self._generate_id(repo_id, doc['snippet_id'])
                embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
                rows.append((
                    doc_id, repo_id, doc['snippet_id'],
                    doc['code'], json.dumps(doc['metadata']), embedding_blob
                ))

            conn.executemany(
                """INSERT OR REPLACE INTO embeddings
                   (id, repo_id, snippet_id, code, metadata, embedding)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows
            )

    async def search(self, repo_id: int, query: str, n_results: int = 5) -> List[Dict]:
        """Search using cosine similarity on embeddings."""
        query_embedding = generate_embedding(query)
        query_vec = np.array(query_embedding, dtype=np.float32)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, snippet_id, code, metadata, embedding FROM embeddings WHERE repo_id = ?",
                (repo_id,)
            )
            results = []
            for row in cursor:
                embedding = np.frombuffer(row[4], dtype=np.float32)

                # Cosine similarity
                norm_query = np.linalg.norm(query_vec)
                norm_emb = np.linalg.norm(embedding)
                if norm_query > 0 and norm_emb > 0:
                    similarity = float(np.dot(query_vec, embedding) / (norm_query * norm_emb))
                else:
                    similarity = 0.0

                results.append({
                    'id': row[0],
                    'snippet_id': row[1],
                    'code': row[2],
                    'metadata': json.loads(row[3]),
                    'similarity': similarity
                })

            # Sort by similarity (descending)
            results.sort(key=lambda x: x['similarity'], reverse=True)

            # Convert similarity to distance (smaller is better)
            for r in results[:n_results]:
                r['distance'] = 1 - r['similarity']
                del r['similarity']

            return results[:n_results]

    def delete_repo_collection(self, repo_id: int):
        """Delete all embeddings for a repository."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM embeddings WHERE repo_id = ?", (repo_id,))

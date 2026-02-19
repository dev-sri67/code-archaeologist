"""
Unit tests for Vector Store Service.
"""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from app.services.vector_store import VectorStore


class TestVectorStore:
    """Test Vector Store functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def vector_store(self, temp_dir):
        """Create vector store instance with temp directory."""
        return VectorStore(persist_dir=temp_dir)
    
    @pytest.mark.asyncio
    async def test_vector_store_initialization(self, vector_store):
        """Test vector store initialization."""
        assert vector_store.persist_dir is not None
        # ChromaDB uses persist_dir directly; SQLite has db_path
        if hasattr(vector_store, 'db_path'):
            assert vector_store.db_path is not None
    
    @pytest.mark.asyncio
    async def test_add_code_snippet(self, vector_store):
        """Test adding a code snippet."""
        repo_id = 1
        snippet_id = "test_snippet_1"
        code = "def hello():\n    return 'world'"
        metadata = {
            "file_path": "test.py",
            "entity_name": "hello",
            "entity_type": "function"
        }
        
        # Add snippet
        await vector_store.add_code_snippet(repo_id, snippet_id, code, metadata)
        
        # Verify it was added (search for it)
        results = await vector_store.search(repo_id, "hello world", n_results=5)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_empty_repo(self, vector_store):
        """Test searching in empty repository."""
        results = await vector_store.search(999, "nonexistent", n_results=5)
        assert isinstance(results, list)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_with_results(self, vector_store):
        """Test searching with multiple snippets."""
        repo_id = 1
        
        # Add multiple snippets
        snippets = [
            ("func1", "def calculate_sum(a, b):\n    return a + b"),
            ("func2", "def calculate_product(a, b):\n    return a * b"),
            ("func3", "def process_data(data):\n    return data.upper()")
        ]
        
        for snippet_id, code in snippets:
            await vector_store.add_code_snippet(
                repo_id, snippet_id, code,
                {"file_path": "test.py", "entity_name": snippet_id}
            )
        
        # Search for calculation-related snippets
        results = await vector_store.search(repo_id, "calculate", n_results=2)
        
        assert len(results) >= 1
        assert len(results) <= 2
        
        # Results should have required fields
        for result in results:
            assert 'code' in result
            assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_search_n_results_limit(self, vector_store):
        """Test that search respects n_results limit."""
        repo_id = 1
        
        # Add 5 snippets
        for i in range(5):
            await vector_store.add_code_snippet(
                repo_id, f"snippet_{i}",
                f"def function_{i}(): pass",
                {"file": f"file{i}.py"}
            )
        
        # Search with limit
        results = await vector_store.search(repo_id, "function", n_results=2)
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_generate_embedding_fallback(self, vector_store):
        """Test embedding generation (should use fallback hash)."""
        code = "test code snippet"
        embedding = await vector_store.generate_embedding(code)
        
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, vector_store):
        """Test that same code generates same embedding."""
        code = "def same_function(): pass"
        
        emb1 = await vector_store.generate_embedding(code)
        emb2 = await vector_store.generate_embedding(code)
        
        assert emb1 == emb2
    
    @pytest.mark.asyncio
    async def test_delete_repo_collection(self, vector_store):
        """Test deleting a repository's collection."""
        repo_id = 1
        
        # Add snippets
        await vector_store.add_code_snippet(
            repo_id, "snippet_1",
            "test code",
            {"file": "test.py"}
        )
        
        # Verify it exists
        results = await vector_store.search(repo_id, "test", n_results=10)
        assert len(results) > 0
        
        # Delete collection
        vector_store.delete_repo_collection(repo_id)
        
        # Verify it's gone
        results = await vector_store.search(repo_id, "test", n_results=10)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_add_documents_batch(self, vector_store):
        """Test batch adding documents."""
        repo_id = 1
        documents = [
            {
                'snippet_id': 'doc1',
                'code': 'function one() {}',
                'metadata': {'type': 'function'}
            },
            {
                'snippet_id': 'doc2',
                'code': 'function two() {}',
                'metadata': {'type': 'function'}
            },
            {
                'snippet_id': 'doc3',
                'code': 'const three = 3;',
                'metadata': {'type': 'variable'}
            }
        ]
        
        await vector_store.add_documents_batch(repo_id, documents)
        
        # Verify all were added
        results = await vector_store.search(repo_id, "function", n_results=10)
        assert len(results) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

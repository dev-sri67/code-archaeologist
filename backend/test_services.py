"""Test script for VectorStore and LLM service integration"""
import asyncio
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.vector_store import VectorStore, _CHROMADB_AVAILABLE
from app.services.llm_service import LLMService


async def test_vector_store():
    """Test VectorStore functionality (SQLite fallback on Python 3.14+)"""
    print("=" * 50)
    backend = "ChromaDB" if _CHROMADB_AVAILABLE else "SQLite"
    print(f"TESTING VECTOR STORE ({backend})")
    print("=" * 50)
    
    try:
        # Initialize vector store
        store = VectorStore()
        print(f"✓ VectorStore initialized ({backend} backend)")
        
        # Test getting/creating collection
        repo_id = 999
        collection = store.get_collection(repo_id)
        print(f"✓ Collection retrieved/created for repo {repo_id}")
        
        # Since we don't have OpenAI key, we'll test with fallback embeddings
        test_docs = [
            {
                "snippet_id": "test_1",
                "code": "def hello_world():\n    print('Hello, World!')",
                "metadata": {"file_path": "test.py", "language": "python"}
            },
            {
                "snippet_id": "test_2",
                "code": "class Calculator:\n    def add(self, a, b):\n        return a + b",
                "metadata": {"file_path": "calc.py", "language": "python"}
            }
        ]
        
        # Test document insertion
        for doc in test_docs:
            await store.add_code_snippet(repo_id, doc["snippet_id"], doc["code"], doc["metadata"])
        print(f"✓ Added {len(test_docs)} test documents")
        
        # Test search
        results = await store.search(repo_id, "hello world", n_results=2)
        print(f"✓ Search returned {len(results)} results")
        
        # Cleanup
        store.delete_repo_collection(repo_id)
        print("✓ Collection deleted")
        
        print(f"\n✅ VECTOR STORE TESTS PASSED ({backend})")
        return True
        
    except Exception as e:
        print(f"\n❌ VECTOR STORE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_service():
    """Test LLM service"""
    print("\n" + "=" * 50)
    print("TESTING LLM SERVICE")
    print("=" * 50)
    
    try:
        service = LLMService()
        print("✓ LLMService initialized")
        
        if service.client is None:
            print("⚠ OpenAI API key not set - service will raise error when called")
        else:
            print("✓ OpenAI client configured")
        
        print("\n✅ LLM SERVICE INITIALIZATION PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM SERVICE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test that all imports work"""
    print("=" * 50)
    print("TESTING IMPORTS")
    print("=" * 50)
    
    imports_ok = True
    
    print(f"Backend: {'ChromaDB' if _CHROMADB_AVAILABLE else 'SQLite (fallback)'}")
    
    try:
        from openai import AsyncOpenAI
        print("✓ openai imported")
    except ImportError as e:
        print(f"✗ Failed to import openai: {e}")
        imports_ok = False
    
    try:
        print("✓ VectorStore imported")
    except ImportError as e:
        print(f"✗ Failed to import VectorStore: {e}")
        imports_ok = False
    
    try:
        print("✓ LLMService imported")
    except ImportError as e:
        print(f"✗ Failed to import LLMService: {e}")
        imports_ok = False
    
    if imports_ok:
        print("\n✅ ALL IMPORTS PASSED")
    else:
        print("\n❌ SOME IMPORTS FAILED")
    
    return imports_ok


async def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("CODE ARCHAEOLOGIST - SANDBOX TESTS")
    print("=" * 50)
    
    if not test_imports():
        print("\n❌ Tests aborted - failed imports")
        return False
    
    vs_ok = await test_vector_store()
    llm_ok = await test_llm_service()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Vector Store: {'✅ PASS' if vs_ok else '❌ FAIL'}")
    print(f"LLM Service: {'✅ PASS' if llm_ok else '❌ FAIL'}")
    
    if vs_ok and llm_ok:
        print("\n🎉 ALL TESTS PASSED")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

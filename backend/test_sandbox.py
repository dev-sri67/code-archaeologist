"""Sandbox test - works without ChromaDB by mocking the vector store"""
import sys
import os
import asyncio

# Mock ChromaDB before importing
class MockChromaDB:
    """Mock ChromaDB for testing without the actual library"""
    pass

sys.modules['chromadb'] = MockChromaDB()
sys.modules['chromadb.config'] = type(sys)('chromadb.config')
sys.modules['chromadb.config'].Settings = lambda **kwargs: None

from app.services.llm_service import LLMService
from app.config import get_settings

async def test_llm_service():
    """Test LLM service initialization and structure"""
    print("=" * 50)
    print("TESTING LLM SERVICE")
    print("=" * 50)
    
    try:
        service = LLMService()
        print("✓ LLMService initialized")
        print(f"  Model: {service.model}")
        print(f"  Client configured: {service.client is not None}")
        
        # Check config
        settings = get_settings()
        print(f"\n  OpenAI API Key set: {bool(settings.OPENAI_API_KEY)}")
        print(f"  ChromaDB dir: {settings.CHROMA_PERSIST_DIR}")
        
        print("\n✅ LLM SERVICE TEST PASSED")
        return True
    except Exception as e:
        print(f"\n❌ LLM SERVICE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_store_code():
    """Test vector store code structure (without running ChromaDB)"""
    print("\n" + "=" * 50)
    print("TESTING VECTOR STORE CODE STRUCTURE")
    print("=" * 50)
    
    try:
        # Read the vector store file and check it has the right methods
        with open('app/services/vector_store.py', 'r') as f:
            content = f.read()
        
        required_methods = [
            '__init__',
            'get_collection',
            'generate_embedding',
            'add_code_snippet',
            'search',
            'delete_repo_collection',
            'add_documents_batch'
        ]
        
        found_methods = []
        for method in required_methods:
            if f'def {method}' in content:
                found_methods.append(method)
                print(f"✓ Method '{method}' found")
            else:
                print(f"✗ Method '{method}' NOT found")
        
        # Check for ChromaDB imports
        has_chromadb = 'import chromadb' in content
        has_openai = 'from openai import' in content
        
        print(f"\n  ChromaDB import: {'✓' if has_chromadb else '✗'}")
        print(f"  OpenAI import: {'✓' if has_openai else '✗'}")
        
        if len(found_methods) == len(required_methods):
            print("\n✅ VECTOR STORE CODE STRUCTURE VALID")
            return True
        else:
            print(f"\n⚠️  Missing {len(required_methods) - len(found_methods)} methods")
            return False
            
    except Exception as e:
        print(f"\n❌ VECTOR STORE CODE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_code_structure():
    """Test LLM service code structure"""
    print("\n" + "=" * 50)
    print("TESTING LLM SERVICE CODE STRUCTURE")
    print("=" * 50)
    
    try:
        with open('app/services/llm_service.py', 'r') as f:
            content = f.read()
        
        required_methods = [
            '__init__',
            '_call_llm',
            'generate_file_summary',
            'explain_function',
            'answer_query',
            'explain_file_detailed',
            'suggest_refactorings'
        ]
        
        found_methods = []
        for method in required_methods:
            if f'def {method}' in content:
                found_methods.append(method)
                print(f"✓ Method '{method}' found")
            else:
                print(f"✗ Method '{method}' NOT found")
        
        # Check for OpenAI usage
        has_openai_client = 'AsyncOpenAI' in content
        has_chat_completions = 'chat.completions.create' in content
        
        print(f"\n  AsyncOpenAI client: {'✓' if has_openai_client else '✗'}")
        print(f"  Chat completions: {'✓' if has_chat_completions else '✗'}")
        
        if len(found_methods) == len(required_methods):
            print("\n✅ LLM SERVICE CODE STRUCTURE VALID")
            return True
        else:
            print(f"\n⚠️  Missing {len(required_methods) - len(found_methods)} methods")
            return False
            
    except Exception as e:
        print(f"\n❌ LLM SERVICE CODE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 50)
    print("CODE ARCHAEOLOGIST - SANDBOX STRUCTURE TESTS")
    print("=" * 50)
    print(f"\nPython version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("Note: Skipping ChromaDB runtime - Python 3.14 incompatibility")
    print()
    
    # Run tests
    llm_init_ok = await test_llm_service()
    vs_code_ok = test_vector_store_code()
    llm_code_ok = test_llm_code_structure()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"LLM Service Init: {'✅' if llm_init_ok else '❌'}")
    print(f"Vector Store Code: {'✅' if vs_code_ok else '❌'}")
    print(f"LLM Service Code: {'✅' if llm_code_ok else '❌'}")
    
    if llm_init_ok and vs_code_ok and llm_code_ok:
        print("\n🎉 ALL STRUCTURE TESTS PASSED")
        print("\n⚠️  NOTE: Full integration tests require Python 3.11-3.13")
        print("   for ChromaDB compatibility. Code structure is correct.")
        return True
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

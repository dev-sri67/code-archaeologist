"""Compatibility test - checks environment before full tests"""
import sys

print(f"Python version: {sys.version}")
print("=" * 50)

# Test imports
print("\nTesting imports...")

# Test openai
print("\n1. Testing OpenAI...")
try:
    from openai import AsyncOpenAI
    print("   ✓ openai imported successfully")
except Exception as e:
    print(f"   ✗ openai import failed: {e}")

# Test chromadb
print("\n2. Testing ChromaDB...")
try:
    import chromadb
    print("   ✓ chromadb imported successfully")
    print(f"   Version: {chromadb.__version__ if hasattr(chromadb, '__version__') else 'unknown'}")
except Exception as e:
    print(f"   ✗ chromadb import failed: {e}")
    print(f"   Error type: {type(e).__name__}")

# Test pydantic
print("\n3. Testing Pydantic...")
try:
    import pydantic
    print(f"   Pydantic version: {pydantic.__version__}")
except Exception as e:
    print(f"   ✗ pydantic import failed: {e}")

# Memory info
print("\n4. Testing memory...")
try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"   RAM: {mem.total / 1e9:.1f} GB total, {mem.available / 1e9:.1f} GB available")
except:
    print("   psutil not installed")

print("\n" + "=" * 50)
print("RECOMMENDATION:")
if sys.version_info.major == 3 and sys.version_info.minor >= 14:
    print("⚠️  Python 3.14+ detected. ChromaDB has compatibility issues.")
    print("   Options:")
    print("   1. Use Docker with Python 3.11-3.13")
    print("   2. Wait for ChromaDB to officially support Python 3.14")
    print("   3. Use alternative: pgvector with PostgreSQL")
else:
    print("✅ Python version is compatible with ChromaDB")

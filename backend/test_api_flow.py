#!/usr/bin/env python
"""
Test the full API flow end-to-end.
"""
import asyncio
import sys
from fastapi.testclient import TestClient
from app.main import app
from app.database import AsyncSessionLocal, init_db

async def setup():
    """Initialize the database."""
    await init_db()
    print("✓ Database initialized")

def test_api_endpoints():
    """Test API endpoints."""
    client = TestClient(app)
    
    # Test health check
    print("\n1. Testing health check...")
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'
    print("✓ Health check passed")
    
    # Test root endpoint
    print("\n2. Testing root endpoint...")
    response = client.get('/')
    assert response.status_code == 200
    print("✓ Root endpoint passed")
    
    # Test repository listing (should be empty)
    print("\n3. Testing repository listing...")
    response = client.get('/api/repos')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    print(f"✓ Repository listing passed (found {len(response.json())} repos)")
    
    # Test invalid repo access
    print("\n4. Testing invalid repo access...")
    response = client.get('/api/repos/99999')
    assert response.status_code == 404
    print("✓ Invalid repo access correctly rejected")
    
    # Test invalid repo files
    print("\n5. Testing invalid repo files...")
    response = client.get('/api/repos/99999/files')
    assert response.status_code == 404
    print("✓ Invalid repo files correctly rejected")
    
    # Test invalid repo graph
    print("\n6. Testing invalid repo graph...")
    response = client.get('/api/repos/99999/graph')
    assert response.status_code == 404
    print("✓ Invalid repo graph correctly rejected")
    
    # Test chat query with invalid repo
    print("\n7. Testing chat query with invalid repo...")
    response = client.post('/api/chat/query', json={
        'query': 'What does this code do?',
        'repo_id': 99999
    })
    assert response.status_code == 404
    print("✓ Chat query with invalid repo correctly rejected")
    
    # Test analysis endpoints with invalid repo
    print("\n8. Testing analysis endpoints with invalid repo...")
    response = client.get('/api/analysis/repos/99999/relationships')
    assert response.status_code == 404
    print("✓ Analysis relationships with invalid repo correctly rejected")
    
    response = client.get('/api/analysis/repos/99999/dependencies')
    assert response.status_code == 404
    print("✓ Analysis dependencies with invalid repo correctly rejected")
    
    response = client.get('/api/analysis/repos/99999/call-graph')
    assert response.status_code == 404
    print("✓ Analysis call-graph with invalid repo correctly rejected")
    
    response = client.get('/api/analysis/repos/99999/metrics')
    assert response.status_code == 404
    print("✓ Analysis metrics with invalid repo correctly rejected")
    
    print("\n✅ All API endpoint tests passed!")
    return True

if __name__ == "__main__":
    print("Testing Code Archaeologist API...")
    
    # Run setup
    asyncio.run(setup())
    
    # Test endpoints
    try:
        test_api_endpoints()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

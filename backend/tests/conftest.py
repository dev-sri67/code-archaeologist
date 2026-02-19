"""
Pytest configuration and fixtures for Code Archaeologist tests.
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.config import Settings


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create a test database session for async tests."""
    # Use SQLite in-memory database for tests
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def test_settings(monkeypatch):
    """Create test settings."""
    settings = Settings(
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        OPENAI_API_KEY="test-key",
        GITHUB_TOKEN="test-token",
        CHROMA_PERSIST_DIR="./test_chroma_db",
        REPO_CLONE_DIR="./test_cloned_repos"
    )
    
    # Patch settings globally
    import app.config
    original_get_settings = app.config.get_settings
    
    def patched_get_settings():
        return settings
    
    monkeypatch.setattr(app.config, "get_settings", patched_get_settings)
    
    return settings


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    return a * b

class Calculator:
    def __init__(self):
        self.result = 0
    
    def compute(self, x, y):
        self.result = add(x, y)
        return self.result
    
    def compute_product(self, x, y):
        self.result = multiply(x, y)
        return self.result

result = add(5, 3)
calc = Calculator()
"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
function add(a, b) {
    return a + b;
}

function multiply(a, b) {
    return a * b;
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    compute(x, y) {
        this.result = add(x, y);
        return this.result;
    }
    
    computeProduct(x, y) {
        this.result = multiply(x, y);
        return this.result;
    }
}

const result = add(5, 3);
const calc = new Calculator();
"""


class AsyncTestClient:
    """Async test client for FastAPI testing."""
    
    def __init__(self, app):
        from fastapi.testclient import TestClient
        self.client = TestClient(app)
    
    async def get(self, url, **kwargs):
        """Async GET request."""
        return self.client.get(url, **kwargs)
    
    async def post(self, url, **kwargs):
        """Async POST request."""
        return self.client.post(url, **kwargs)
    
    async def delete(self, url, **kwargs):
        """Async DELETE request."""
        return self.client.delete(url, **kwargs)


@pytest.fixture
async def client():
    """Create a test client for FastAPI."""
    from app.main import app
    return AsyncTestClient(app)

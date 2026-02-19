"""
Code Archaeologist - FastAPI Application

Main entry point for the Code Archaeologist backend API.
Provides endpoints for repository analysis, code exploration, and AI-powered queries.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db

# Import routers
from app.routers import repos, chat, files, analysis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database tables
    - Shutdown: Cleanup resources
    """
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    await init_db()
    print("Database initialized successfully")
    
    yield
    
    # Shutdown
    print("Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Code Archaeologist API - AI-powered code exploration and analysis.
    
    ## Features
    
    * **Repository Analysis**: Clone and analyze GitHub repositories
    * **Code Exploration**: Browse files and entities with AI summaries
    * **RAG Chat**: Ask questions about your codebase in natural language
    * **Graph Visualization**: Visualize code relationships and dependencies
    
    ## Getting Started
    
    1. Submit a repository for analysis: `POST /api/repos/analyze`
    2. Check analysis status: `GET /api/repos/{id}/status`
    3. Chat with your code: `POST /api/chat/query`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and basic info.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "debug": settings.DEBUG
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - returns API info.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include all routers
app.include_router(repos.router)
app.include_router(chat.router)
app.include_router(files.router)
app.include_router(analysis.router)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    if settings.DEBUG:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )

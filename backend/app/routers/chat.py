"""
Chat Routes

API endpoints for RAG-based code queries.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import logging

from app.database import get_db
from app.models import Repository, File, Entity
from app.schemas import ChatQuery, ChatResponse
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService
from app.config import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    query_data: ChatQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG endpoint that answers questions about the codebase.
    
    Steps:
    1. Perform vector search for relevant code snippets
    2. Call LLM with retrieved context + user query
    3. Return answer with source references
    """
    # Verify repository exists
    repo = await db.get(Repository, query_data.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        # Step 1: Vector search
        vector_store = VectorStore()
        search_results = await vector_store.search(
            repo_id=query_data.repo_id,
            query=query_data.query,
            n_results=settings.RAG_RESULTS_LIMIT
        )
        
        if not search_results:
            # Fallback: no vector results found
            return ChatResponse(
                answer="I couldn't find any relevant code snippets for your query. "
                       "The repository might still be indexing or the query might not match any code patterns.",
                sources=[],
                confidence=0.0
            )
        
        # Step 2: Call LLM with context + query
        llm_service = LLMService()
        
        # Build repository context
        repo_context = f"Repository: {repo.name}\nOwner: {repo.owner}"
        if repo.description:
            repo_context += f"\nDescription: {repo.description}"
        
        # Get LLM answer
        result = await llm_service.answer_query(
            query=query_data.query,
            code_snippets=search_results,
            repo_context=repo_context
        )
        
        # Step 3: Return formatted response
        return ChatResponse(
            answer=result['answer'],
            sources=result['sources'],
            confidence=result['confidence']
        )
        
    except Exception as e:
        logger.error(f"Error processing chat query for repo {query_data.repo_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your query. Please try again."
        )


@router.post("/query/stream")
async def chat_query_stream(
    query_data: ChatQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming RAG endpoint for real-time responses.
    
    Returns SSE (Server-Sent Events) stream of the answer.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    repo = await db.get(Repository, query_data.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    async def generate_stream():
        """Generate streaming response chunks."""
        try:
            # Get vector search results
            vector_store = VectorStore()
            search_results = await vector_store.search(
                repo_id=query_data.repo_id,
                query=query_data.query,
                n_results=5
            )
            
            # Send sources first
            sources = [
                {
                    'file_path': s.get('metadata', {}).get('file_path', 'unknown'),
                    'entity_name': s.get('metadata', {}).get('entity_name', 'N/A'),
                }
                for s in search_results[:3]
            ]
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # Stream LLM response in chunks
            llm_service = LLMService()
            result = await llm_service.answer_query(
                query=query_data.query,
                code_snippets=search_results
            )
            
            # Simulate streaming by splitting answer into chunks
            answer = result['answer']
            words = answer.split()
            chunk_size = 5
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk + ' '})}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'confidence': result['confidence']})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

"""
File Routes

API endpoints for file management and analysis.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import aiofiles
import os

from app.database import get_db
from app.models import File, Entity, EntityType, Repository
from app.schemas import FileResponse, EntityResponse, FileExplainResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get file details by ID.
    
    Returns file metadata including path, language, size, and AI-generated summary.
    """
    result = await db.execute(
        select(File).where(File.id == file_id)
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return file


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get raw file content.
    
    Reads the actual file from the cloned repository and returns its contents.
    """
    result = await db.execute(
        select(File, Repository).join(Repository).where(File.id == file_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    
    file, repo = row
    
    # Construct file path from repo clone directory
    # Assuming repos are cloned to a local directory structure
    from app.services.repository_ingester import RepositoryIngester
    ingester = RepositoryIngester()
    
    repo_dir = ingester.get_repo_path(repo.url)

    # Use pathlib for safer path handling
    from pathlib import Path
    repo_path = Path(repo_dir).resolve()
    file_path = (repo_path / file.path).resolve()

    # Security check: ensure path is within repo directory
    try:
        file_path.relative_to(repo_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid file path - outside repository directory")
    
    # Read file content
    try:
        async with aiofiles.open(str(file_path), 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        
        return {
            "file_id": file_id,
            "path": file.path,
            "content": content,
            "language": file.language,
            "size_bytes": file.size_bytes,
            "line_count": len(content.split('\n')) if content else 0
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/{file_id}/explain", response_model=FileExplainResponse)
async def explain_file(
    file_id: int,
    explanation_type: str = "overview",
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI explanation of a file.
    
    Uses LLM to generate a detailed explanation including:
    - Overall purpose and functionality
    - Key entities (functions, classes)
    - Architecture insights
    - Complexity estimation
    
    Query params:
        explanation_type: 'overview', 'detailed', or 'architecture'
    """
    # Get file with repository info
    result = await db.execute(
        select(File, Repository).join(Repository).where(File.id == file_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    
    file, repo = row
    
    # Get file content
    from app.services.repository_ingester import RepositoryIngester
    from pathlib import Path
    ingester = RepositoryIngester()
    repo_dir = ingester.get_repo_path(repo.url)

    # Use pathlib for safer path handling
    repo_path = Path(repo_dir).resolve()
    file_path = (repo_path / file.path).resolve()

    # Security check: ensure path is within repo directory
    try:
        file_path.relative_to(repo_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid file path - outside repository directory")

    try:
        async with aiofiles.open(str(file_path), 'r', encoding='utf-8', errors='ignore') as f:
            code = await f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    # Get entities in this file
    result = await db.execute(
        select(Entity).where(Entity.file_id == file_id)
    )
    entities = result.scalars().all()
    
    entity_list = [
        {
            'name': e.name,
            'type': e.type.value,
            'line': e.start_line
        }
        for e in entities
    ]
    
    # Generate explanation using LLM
    llm_service = LLMService()
    
    try:
        explanation_result = await llm_service.explain_file_detailed(
            file_path=file.path,
            code=code,
            entities=entity_list,
            language=file.language or "python"
        )
        
        key_entities = explanation_result.get('key_entities', [e['name'] for e in entity_list[:10]])
        
        return FileExplainResponse(
            file_id=file_id,
            path=file.path,
            explanation=explanation_result['explanation'],
            key_entities=key_entities,
            complexity_score=explanation_result.get('complexity_score')
        )
        
    except Exception as e:
        # Fallback: return basic info if LLM fails
        return FileExplainResponse(
            file_id=file_id,
            path=file.path,
            explanation=f"Could not generate detailed explanation: {str(e)}\n\n"
                       f"This {file.language or 'code'} file contains {len(entities)} detected entities.",
            key_entities=[e['name'] for e in entity_list[:10]],
            complexity_score=None
        )


@router.get("/{file_id}/entities", response_model=list[EntityResponse])
async def get_file_entities(
    file_id: int,
    entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all entities (functions, classes, etc.) in a file.
    
    Query params:
        entity_type: Filter by type ('function', 'class', 'method', etc.)
    """
    # Verify file exists
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Build query
    query = select(Entity).where(Entity.file_id == file_id)
    
    if entity_type:
        try:
            entity_type_enum = EntityType(entity_type.lower())
            query = query.where(Entity.type == entity_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid entity_type. Valid values: {[e.value for e in EntityType]}"
            )
    
    # Order by line number for logical reading
    query = query.order_by(Entity.start_line)
    
    result = await db.execute(query)
    entities = result.scalars().all()
    
    return entities

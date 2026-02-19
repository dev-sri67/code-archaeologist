"""
Repository Routes
API endpoints for repository management.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from app.database import get_db
from app.models import Repository, AnalysisStatus
from app.schemas import (
    RepositoryCreate, RepositoryResponse, RepositoryStatus,
    FileResponse, GraphResponse, GraphNode, GraphEdge
)
from app.services.repository_ingester import RepositoryIngester
from app.services.analysis_service import AnalysisService
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/repos", tags=["repositories"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=RepositoryResponse)
async def analyze_repository(
    repo_data: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start analysis of a GitHub repository.
    
    This endpoint:
    1. Fetches repository metadata from GitHub
    2. Creates or updates repository record
    3. Queues analysis task in background
    
    Args:
        repo_data: Repository URL to analyze
        background_tasks: Background task manager
        db: Database session
        
    Returns:
        RepositoryResponse: Repository details and analysis status
        
    Raises:
        HTTPException: If URL is invalid or repo fetch fails
    """
    logger.info(f"Analyzing repository: {repo_data.url}")
    
    # Fetch repo info from GitHub
    ingester = RepositoryIngester()
    try:
        info = await ingester.fetch_repo_info(repo_data.url)
        logger.debug(f"Fetched repo info: {info}")
    except Exception as e:
        logger.error(f"Failed to fetch repo info: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch repo: {str(e)}")
    
    # Check if repo already exists
    result = await db.execute(
        select(Repository).where(Repository.url == repo_data.url)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Re-analyze existing repo
        existing.status = AnalysisStatus.PENDING
        existing.status_message = "Queued for re-analysis"
        repo = existing
    else:
        # Create new repo
        repo = Repository(
            url=repo_data.url,
            name=info.get("name", ""),
            owner=info.get("owner", ""),
            description=info.get("description", ""),
            default_branch=info.get("default_branch", "main"),
            status=AnalysisStatus.PENDING,
            status_message="Queued for analysis",
            file_count=0,
            language_breakdown={}
        )
        db.add(repo)
    
    await db.commit()
    await db.refresh(repo)
    
    # Start background analysis
    async def run_analysis():
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            service = AnalysisService(db=session)
            await service.analyze_repository(repo.id)
    
    background_tasks.add_task(run_analysis)
    
    return repo


@router.get("/{repo_id}/status", response_model=RepositoryStatus)
async def get_repo_status(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get analysis status for a repository."""
    service = AnalysisService(db)
    try:
        return await service.get_analysis_status(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get repository details."""
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/{repo_id}/files", response_model=List[FileResponse])
async def get_repo_files(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all files for a repository."""
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    from app.models import File
    result = await db.execute(
        select(File).where(File.repo_id == repo_id)
    )
    files = result.scalars().all()
    return files


@router.get("/{repo_id}/graph", response_model=GraphResponse)
async def get_repo_graph(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get graph data for repository visualization."""
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    service = GraphService(db)
    graph_data = await service.generate_repo_graph(repo_id)
    return GraphResponse(nodes=graph_data["nodes"], edges=graph_data["edges"])


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    db: AsyncSession = Depends(get_db)
):
    """List all analyzed repositories."""
    result = await db.execute(select(Repository))
    repos = result.scalars().all()
    return repos


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a repository and all its data."""
    from app.services.vector_store import VectorStore
    
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Clean up vector store
    vector_store = VectorStore()
    vector_store.delete_repo_collection(repo_id)
    
    # Delete from database (cascade will handle related records)
    await db.delete(repo)
    await db.commit()
    
    return {"status": "deleted", "id": repo_id}
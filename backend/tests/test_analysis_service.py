"""
Unit tests for Analysis Service.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis_service import AnalysisService
from app.models import Repository, File, Entity, EntityType, AnalysisStatus


class TestAnalysisService:
    """Test AnalysisService functionality."""
    
    @pytest.fixture
    async def analysis_service(self, test_db):
        """Create analysis service instance."""
        return AnalysisService(db=test_db)
    
    @pytest.fixture
    async def test_repo(self, test_db):
        """Create a test repository."""
        repo = Repository(
            name="test-repo",
            url="https://github.com/test/test-repo",
            owner="test",
            description="Test repository",
            status=AnalysisStatus.PENDING
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        return repo
    
    @pytest.mark.asyncio
    async def test_analysis_service_initialization(self, analysis_service):
        """Test that analysis service initializes correctly."""
        assert analysis_service.db is not None
        assert analysis_service.ingester is not None
        assert analysis_service.parser is not None
        assert analysis_service.vector_store is not None
        assert analysis_service.llm is not None
    
    @pytest.mark.asyncio
    async def test_get_analysis_status(self, test_db, test_repo):
        """Test getting analysis status."""
        service = AnalysisService(db=test_db)
        
        status = await service.get_analysis_status(test_repo.id)
        
        assert status['id'] == test_repo.id
        assert status['status'] == AnalysisStatus.PENDING.value
        assert 'progress_percent' in status
        assert status['progress_percent'] == 0.0
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_not_found(self, test_db):
        """Test getting status for non-existent repository."""
        service = AnalysisService(db=test_db)
        
        with pytest.raises(ValueError, match="Repository .* not found"):
            await service.get_analysis_status(9999)
    
    @pytest.mark.asyncio
    async def test_parse_entities_no_files(self, test_db, test_repo):
        """Test parsing entities when no files exist."""
        service = AnalysisService(db=test_db)
        
        # Should not raise error even with no files
        await service._parse_entities(test_repo.id, "/tmp/test")
        
        # Repository should still exist
        repo = await test_db.get(Repository, test_repo.id)
        assert repo is not None
    
    @pytest.mark.asyncio
    async def test_detect_relationships_no_entities(self, test_db, test_repo):
        """Test detecting relationships when no entities exist."""
        service = AnalysisService(db=test_db)
        
        # Should not raise error
        await service._detect_relationships(test_repo.id)
        
        # Repository should still exist
        repo = await test_db.get(Repository, test_repo.id)
        assert repo is not None
    
    def test_calculate_progress(self):
        """Test progress calculation."""
        service = AnalysisService(db=None)  # type: ignore
        
        # Create mock repository with different statuses
        repo_pending = MagicMock()
        repo_pending.status = AnalysisStatus.PENDING
        
        repo_in_progress = MagicMock()
        repo_in_progress.status = AnalysisStatus.IN_PROGRESS
        
        repo_completed = MagicMock()
        repo_completed.status = AnalysisStatus.COMPLETED
        
        repo_failed = MagicMock()
        repo_failed.status = AnalysisStatus.FAILED
        
        assert service._calculate_progress(repo_pending) == 0.0
        assert service._calculate_progress(repo_in_progress) == 50.0
        assert service._calculate_progress(repo_completed) == 100.0
        assert service._calculate_progress(repo_failed) == 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_repository_not_found(self, test_db):
        """Test analyzing non-existent repository."""
        service = AnalysisService(db=test_db)
        
        with pytest.raises(ValueError, match="Repository .* not found"):
            await service.analyze_repository(9999)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

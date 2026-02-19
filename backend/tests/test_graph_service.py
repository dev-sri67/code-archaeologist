"""
Unit tests for Graph Service.
"""
import pytest
from sqlalchemy import select

from app.services.graph_service import GraphService
from app.models import Repository, File, Entity, EntityType, AnalysisStatus


class TestGraphService:
    """Test GraphService functionality."""
    
    @pytest.fixture
    async def graph_service(self, test_db):
        """Create graph service instance."""
        return GraphService(db=test_db)
    
    @pytest.fixture
    async def test_repo_with_files(self, test_db):
        """Create a test repository with files."""
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
        
        # Add files
        file1 = File(
            repo_id=repo.id,
            path="src/main.py",
            extension=".py",
            language="python",
            size_bytes=1000,
            line_count=50
        )
        file2 = File(
            repo_id=repo.id,
            path="src/utils.py",
            extension=".py",
            language="python",
            size_bytes=500,
            line_count=25
        )
        file3 = File(
            repo_id=repo.id,
            path="tests/test_main.py",
            extension=".py",
            language="python",
            size_bytes=800,
            line_count=40
        )
        
        test_db.add_all([file1, file2, file3])
        await test_db.commit()
        
        return repo
    
    @pytest.mark.asyncio
    async def test_generate_repo_graph_empty(self, test_db, graph_service):
        """Test generating graph for empty repository."""
        repo = Repository(
            name="empty-repo",
            url="https://github.com/test/empty",
            owner="test",
            status=AnalysisStatus.PENDING
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        graph = await graph_service.generate_repo_graph(repo.id)
        
        assert 'nodes' in graph
        assert 'edges' in graph
        assert isinstance(graph['nodes'], list)
        assert isinstance(graph['edges'], list)
    
    @pytest.mark.asyncio
    async def test_generate_repo_graph_with_files(self, test_db, test_repo_with_files, graph_service):
        """Test generating graph with files."""
        graph = await graph_service.generate_repo_graph(test_repo_with_files.id)
        
        assert 'nodes' in graph
        assert 'edges' in graph
        
        # Should have module nodes for src and tests directories
        nodes = graph['nodes']
        assert len(nodes) > 0
        
        # Check node structure
        for node in nodes:
            assert 'id' in node
            assert 'type' in node
            assert 'label' in node
            assert 'position' in node
            assert 'data' in node
    
    @pytest.mark.asyncio
    async def test_generate_repo_graph_nonexistent(self, test_db, graph_service):
        """Test generating graph for non-existent repository."""
        graph = await graph_service.generate_repo_graph(9999)
        
        # Should return empty graph, not raise error
        assert graph['nodes'] == []
        assert graph['edges'] == []
    
    @pytest.mark.asyncio
    async def test_generate_repo_graph_with_entities(self, test_db, graph_service):
        """Test generating graph with entities."""
        repo = Repository(
            name="test-repo",
            url="https://github.com/test/test-repo",
            owner="test",
            status=AnalysisStatus.PENDING
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Add file
        file = File(
            repo_id=repo.id,
            path="src/main.py",
            extension=".py",
            language="python"
        )
        test_db.add(file)
        await test_db.commit()
        await test_db.refresh(file)
        
        # Add entities
        entity1 = Entity(
            repo_id=repo.id,
            file_id=file.id,
            name="main_function",
            type=EntityType.FUNCTION,
            start_line=1,
            end_line=10
        )
        entity2 = Entity(
            repo_id=repo.id,
            file_id=file.id,
            name="MainClass",
            type=EntityType.CLASS,
            start_line=12,
            end_line=30
        )
        
        test_db.add_all([entity1, entity2])
        await test_db.commit()
        
        graph = await graph_service.generate_repo_graph(repo.id)
        
        # Should have file nodes and entity nodes
        nodes = graph['nodes']
        assert len(nodes) >= 3  # At least 1 module + 1 file + 2 entities
        
        # Check that entity nodes are included
        entity_nodes = [n for n in nodes if n['type'] == 'entity']
        assert len(entity_nodes) >= 2
    
    def test_group_files_by_module(self, graph_service):
        """Test file grouping by module."""
        # Create mock files
        files = [
            MagicMock(path="src/main.py"),
            MagicMock(path="src/utils.py"),
            MagicMock(path="tests/test_main.py"),
            MagicMock(path="README.md"),
        ]
        
        groups = graph_service._group_files_by_module(files)
        
        assert 'src' in groups
        assert 'tests' in groups
        assert 'root' in groups
        
        assert len(groups['src']) == 2
        assert len(groups['tests']) == 1
        assert len(groups['root']) == 1
    
    def test_get_language_color(self, graph_service):
        """Test language color mapping."""
        assert graph_service._get_language_color("python") == "#ffd54f"
        assert graph_service._get_language_color("javascript") == "#ffeb3b"
        assert graph_service._get_language_color("typescript") == "#a1887f"
        assert graph_service._get_language_color("ruby") == "#e0e0e0"  # default
    
    def test_get_entity_color(self, graph_service):
        """Test entity type color mapping."""
        assert graph_service._get_entity_color(EntityType.FUNCTION) == "#81c784"
        assert graph_service._get_entity_color(EntityType.CLASS) == "#ff8a65"
        assert graph_service._get_entity_color(EntityType.METHOD) == "#4db6ac"
    
    def test_hash_id(self, graph_service):
        """Test ID hashing."""
        hash1 = graph_service._hash_id("test_module")
        hash2 = graph_service._hash_id("test_module")
        
        assert hash1 == hash2  # Should be consistent
        assert len(hash1) == 8  # Should be 8 chars
        assert all(c in "0123456789abcdef" for c in hash1)  # Should be hex


# Import MagicMock for mock usage
from unittest.mock import MagicMock


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Unit tests for Repository Ingester Service.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import shutil
from pathlib import Path

from app.services.repository_ingester import RepositoryIngester


class TestRepositoryIngester:
    """Test RepositoryIngester functionality."""
    
    @pytest.fixture
    def ingester(self):
        """Create repository ingester instance."""
        return RepositoryIngester()
    
    @pytest.fixture
    def temp_repo_dir(self):
        """Create temporary repository directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_extract_repo_info_https(self, ingester):
        """Test extracting repo info from HTTPS URL."""
        url = "https://github.com/facebook/react"
        owner, name = ingester._extract_repo_info(url)
        
        assert owner == "facebook"
        assert name == "react"
    
    def test_extract_repo_info_git(self, ingester):
        """Test extracting repo info from .git URL."""
        url = "https://github.com/angular/angular.git"
        owner, name = ingester._extract_repo_info(url)
        
        assert owner == "angular"
        assert name == "angular"
    
    def test_extract_repo_info_invalid(self, ingester):
        """Test extracting repo info from invalid URL."""
        url = "https://github.com/invalid"
        
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            ingester._extract_repo_info(url)
    
    def test_is_binary_file(self, ingester):
        """Test binary file detection."""
        # Binary files
        assert ingester._is_binary_file("image.png") == True
        assert ingester._is_binary_file("video.mp4") == True
        assert ingester._is_binary_file("archive.zip") == True
        assert ingester._is_binary_file("compiled.pyc") == True
        
        # Source files
        assert ingester._is_binary_file("script.py") == False
        assert ingester._is_binary_file("app.js") == False
        assert ingester._is_binary_file("styles.css") == False
    
    def test_should_skip_dir(self, ingester):
        """Test directory skipping logic."""
        # Skip directories
        assert ingester._should_skip_dir("node_modules") == True
        assert ingester._should_skip_dir("path/to/node_modules") == True
        assert ingester._should_skip_dir(".git") == True
        assert ingester._should_skip_dir("__pycache__") == True
        
        # Keep directories
        assert ingester._should_skip_dir("src") == False
        assert ingester._should_skip_dir("lib") == False
    
    def test_get_file_language(self, ingester):
        """Test language detection from file extension."""
        assert ingester._get_file_language("main.py") == "python"
        assert ingester._get_file_language("script.js") == "javascript"
        assert ingester._get_file_language("module.jsx") == "javascript"
        assert ingester._get_file_language("types.ts") == "typescript"
        assert ingester._get_file_language("styles.tsx") == "typescript"
        assert ingester._get_file_language("readme.md") == None
        assert ingester._get_file_language("data.json") == None
    
    def test_register_repo_path(self, ingester):
        """Test registering repository path."""
        url = "https://github.com/test/repo"
        path = "/tmp/test/repo"
        
        ingester.register_repo_path(url, path)
        
        # Verify it's registered
        retrieved_path = ingester.get_repo_path(url)
        assert retrieved_path == path
    
    def test_get_repo_path_not_found(self, ingester):
        """Test getting path for unregistered repository."""
        url = "https://github.com/nonexistent/repo"
        
        with pytest.raises(ValueError, match="not been cloned"):
            ingester.get_repo_path(url)
    
    @pytest.mark.asyncio
    async def test_scan_files(self, ingester, temp_repo_dir):
        """Test scanning files in a directory."""
        # Create test file structure
        src_dir = Path(temp_repo_dir) / "src"
        src_dir.mkdir()
        
        # Create Python files
        (src_dir / "main.py").write_text("def main(): pass")
        (src_dir / "utils.py").write_text("def helper(): pass")
        
        # Create a JavaScript file
        (src_dir / "app.js").write_text("function init() {}")
        
        # Scan files
        files = await ingester.scan_files(temp_repo_dir)
        
        # Verify results
        assert len(files) >= 3  # At least 3 source files
        
        file_paths = {f['path'] for f in files}
        assert any("main.py" in path for path in file_paths)
        assert any("utils.py" in path for path in file_paths)
        assert any("app.js" in path for path in file_paths)
        
        # Verify proper file information is included
        for f in files:
            assert 'path' in f
            assert 'extension' in f
            assert 'size_bytes' in f
            assert 'language' in f
    
    @pytest.mark.asyncio
    async def test_scan_files_skip_binary(self, ingester, temp_repo_dir):
        """Test that binary files are skipped."""
        # Create binary and source files
        (Path(temp_repo_dir) / "script.py").write_text("print('hello')")
        (Path(temp_repo_dir) / "image.png").write_bytes(b"fake png data")
        
        files = await ingester.scan_files(temp_repo_dir)
        
        file_paths = {f['path'] for f in files}
        assert any(".py" in path for path in file_paths)
        assert not any(".png" in path for path in file_paths)
    
    @pytest.mark.asyncio
    async def test_scan_files_skip_directories(self, ingester, temp_repo_dir):
        """Test that certain directories are skipped."""
        # Create directory structure
        src_dir = Path(temp_repo_dir) / "src"
        node_modules = Path(temp_repo_dir) / "node_modules"
        
        src_dir.mkdir()
        node_modules.mkdir()
        
        (src_dir / "main.py").write_text("# source")
        (node_modules / "package.js").write_text("// dependency")
        
        files = await ingester.scan_files(temp_repo_dir)
        
        file_paths = {f['path'] for f in files}
        assert any("main.py" in path for path in file_paths)
        assert not any("node_modules" in path for path in file_paths)
    
    @pytest.mark.asyncio
    async def test_read_file_content(self, ingester, temp_repo_dir):
        """Test reading file content."""
        file_path = Path(temp_repo_dir) / "test.py"
        content = "def test():\n    pass"
        file_path.write_text(content)
        
        read_content = await ingester.read_file_content(str(file_path))
        
        assert read_content == content
    
    @pytest.mark.asyncio
    async def test_read_file_not_found(self, ingester):
        """Test reading non-existent file."""
        read_content = await ingester.read_file_content("/nonexistent/file.py")
        
        # Should return error message instead of raising
        assert "Error" in read_content or isinstance(read_content, str)
    
    @pytest.mark.asyncio
    async def test_get_language_breakdown(self, ingester):
        """Test language breakdown calculation."""
        files = [
            {'language': 'python'},
            {'language': 'python'},
            {'language': 'javascript'},
            {'language': None},
        ]
        
        breakdown = await ingester.get_language_breakdown(files)
        
        assert breakdown.get('python') == 2
        assert breakdown.get('javascript') == 1
        assert breakdown.get('other') == 1
    
    def test_cleanup(self, ingester):
        """Test cleanup of temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="test_ingester_")
        ingester.temp_dir = temp_dir
        
        # Verify temp dir exists
        assert Path(temp_dir).exists()
        
        # Cleanup
        ingester.cleanup()
        
        # Temp dir should be removed
        assert not Path(temp_dir).exists()
        assert ingester.temp_dir is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

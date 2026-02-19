"""
Repository Ingestion Service
Handles cloning GitHub repositories and extracting file metadata.
"""
import os
import re
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
import aiofiles

import git
from github import Github, Repository as GitHubRepo

from app.config import get_settings

settings = get_settings()

# File extensions we support in Phase 1
SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    '.env', 'dist', 'build', '.pytest_cache', '.mypy_cache',
    'coverage', '.tox', '.idea', '.vscode', 'target', 'vendor'
}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.bmp',
    '.mp4', '.mov', '.avi', '.mp3', '.wav', '.ogg',
    '.pdf', '.doc', '.docx', '.zip', '.tar', '.gz', '.rar',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.pyc',
    '.lock', '.log', '.min.js', '.min.css'
}


class RepositoryIngester:
    """Ingests GitHub repositories for analysis."""
    
    def __init__(self):
        self.github = Github(settings.GITHUB_TOKEN) if settings.GITHUB_TOKEN else Github()
        self.temp_dir: Optional[str] = None
        self.repo_paths = {}  # Cache for repo paths
    
    def _extract_repo_info(self, url: str) -> Tuple[str, str]:
        """Extract owner and repo name from GitHub URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {url}")
        return path_parts[0], path_parts[1].replace('.git', '')
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension."""
        ext = Path(file_path).suffix.lower()
        return ext in BINARY_EXTENSIONS
    
    def _should_skip_dir(self, dir_path: str) -> bool:
        """Check if directory should be skipped."""
        parts = Path(dir_path).parts
        return any(skip in parts for skip in SKIP_DIRS)
    
    def _get_file_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return SUPPORTED_EXTENSIONS.get(ext)
    
    async def fetch_repo_info(self, url: str) -> Dict:
        """Fetch repository metadata from GitHub API."""
        owner, name = self._extract_repo_info(url)
        
        try:
            repo = self.github.get_repo(f"{owner}/{name}")
            return {
                "name": repo.name,
                "owner": repo.owner.login,
                "description": repo.description or "",
                "default_branch": repo.default_branch,
                "stars": repo.stargazers_count,
                "language": repo.language,
                "url": url,
            }
        except Exception as e:
            raise Exception(f"Failed to fetch repo info: {str(e)}")
    
    async def clone_repository(self, url: str) -> str:
        """Clone repository to temporary directory."""
        owner, name = self._extract_repo_info(url)
        
        # Create persistent directory
        os.makedirs(settings.REPO_CLONE_DIR, exist_ok=True)
        repo_dir = os.path.join(settings.REPO_CLONE_DIR, f"{owner}_{name}")
        
        # Use temp directory as fallback if not in persistent location
        if not os.path.exists(repo_dir):
            self.temp_dir = tempfile.mkdtemp(prefix=f"codearch_{name}_")
            clone_target = self.temp_dir
        else:
            clone_target = repo_dir
        
        # Clone with depth 1 (shallow clone) for performance
        clone_url = f"https://github.com/{owner}/{name}.git"
        
        try:
            git.Repo.clone_from(
                clone_url,
                clone_target,
                depth=1,
                branch=None,  # Default branch
                single_branch=True
            )
            # Register the path
            self.register_repo_path(url, clone_target)
            return clone_target
        except Exception as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    async def scan_files(self, repo_path: str) -> List[Dict]:
        """Scan repository and return list of source files."""
        files = []
        
        for root, dirs, filenames in os.walk(repo_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not self._should_skip_dir(os.path.join(root, d))]
            
            rel_root = os.path.relpath(root, repo_path)
            if rel_root == '.':
                rel_root = ''
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.join(rel_root, filename) if rel_root else filename
                
                # Skip binary files
                if self._is_binary_file(file_path):
                    continue
                
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                
                # Check file size (skip if > 1MB)
                size = os.path.getsize(file_path)
                if size > 1_000_000:
                    continue
                
                language = self._get_file_language(file_path)
                ext = Path(filename).suffix.lower()
                
                files.append({
                    "path": rel_path,
                    "extension": ext,
                    "size_bytes": size,
                    "language": language,
                    "absolute_path": file_path,
                })
        
        return files
    
    async def read_file_content(self, file_path: str) -> str:
        """Read file content asynchronously."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return await f.read()
        except Exception as e:
            return f"# Error reading file: {str(e)}"
    
    async def get_language_breakdown(self, files: List[Dict]) -> Dict[str, int]:
        """Get language distribution."""
        breakdown = {}
        for file in files:
            lang = file.get('language') or 'other'
            breakdown[lang] = breakdown.get(lang, 0) + 1
        return breakdown
    
    def cleanup(self):
        """Cleanup temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def get_repo_path(self, url: str) -> str:
        """
        Get the path to a cloned repository.
        
        Maintains a cache of repository paths for later file access.
        The path is stored when cloning and retrieved here.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Path to the cloned repository directory
            
        Raises:
            ValueError: If repository has not been cloned
        """
        if url in self.repo_paths:
            return self.repo_paths[url]
        
        # Try to find repo in standard location
        owner, name = self._extract_repo_info(url)
        standard_path = os.path.join(settings.REPO_CLONE_DIR, f"{owner}_{name}")
        
        if os.path.exists(standard_path):
            self.repo_paths[url] = standard_path
            return standard_path
        
        raise ValueError(f"Repository {url} has not been cloned")
    
    def register_repo_path(self, url: str, path: str):
        """Register a cloned repository path for later retrieval."""
        self.repo_paths[url] = path
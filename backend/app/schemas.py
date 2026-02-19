from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


# Enums
class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"


class RelationshipType(str, Enum):
    CALLS = "calls"
    INHERITS = "inherits"
    IMPORTS = "imports"
    CONTAINS = "contains"
    REFERENCES = "references"


# Repository Schemas
class RepositoryBase(BaseModel):
    url: str
    name: Optional[str] = None


class RepositoryCreate(RepositoryBase):
    @field_validator('url')
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Validate that URL is from an allowed git hosting platform."""
        from app.config import get_settings
        settings = get_settings()

        # Normalize URL
        v = v.strip().rstrip('/')

        # Check if URL matches allowed domains
        allowed_patterns = [
            r'^https?://github\.com/[\w\-]+/[\w\-\.]+$',
            r'^https?://gitlab\.com/[\w\-]+/[\w\-\.]+$',
        ]

        if not any(re.match(pattern, v) for pattern in allowed_patterns):
            raise ValueError(
                "Invalid repository URL. Must be a GitHub or GitLab URL in format: "
                "https://github.com/owner/repo or https://gitlab.com/owner/repo"
            )

        return v


class RepositoryResponse(RepositoryBase):
    id: int
    owner: str
    description: Optional[str] = None
    default_branch: str
    status: AnalysisStatus
    status_message: Optional[str] = None
    file_count: int
    language_breakdown: Dict[str, Any]
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RepositoryStatus(BaseModel):
    id: int
    status: AnalysisStatus
    status_message: Optional[str] = None
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)


# File Schemas
class FileResponse(BaseModel):
    id: int
    repo_id: int
    path: str
    extension: Optional[str] = None
    size_bytes: Optional[int] = None
    line_count: Optional[int] = None
    language: Optional[str] = None
    summary: Optional[str] = None
    
    class Config:
        from_attributes = True


# Entity Schemas
class EntityResponse(BaseModel):
    id: int
    repo_id: int
    file_id: int
    name: str
    type: EntityType
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    signature: Optional[str] = None
    logic_summary: Optional[str] = None
    
    class Config:
        from_attributes = True


class EntityDetail(EntityResponse):
    docstring: Optional[str] = None
    code_snippet: Optional[str] = None


# Relationship Schemas
class RelationshipResponse(BaseModel):
    id: int
    source_entity_id: int
    target_entity_id: int
    relationship_type: RelationshipType
    
    class Config:
        from_attributes = True


# Graph Schemas (for React Flow)
class GraphNode(BaseModel):
    id: str
    type: str  # 'file', 'class', 'function', 'module'
    label: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: Dict[str, Any] = Field(default_factory=dict)
    style: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: Optional[str] = "default"
    label: Optional[str] = None
    animated: bool = False
    style: Optional[Dict[str, Any]] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Chat Schemas
class ChatQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    repo_id: int = Field(..., gt=0)
    conversation_id: Optional[str] = None

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Sanitize and validate query string."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        # Remove any potential command injection attempts
        forbidden_chars = ['\x00', '\r']
        for char in forbidden_chars:
            if char in v:
                raise ValueError("Query contains invalid characters")
        return v


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float


class FileExplainRequest(BaseModel):
    file_id: int
    explanation_type: str = "overview"  # 'overview', 'detailed', 'architecture'


class FileExplainResponse(BaseModel):
    file_id: int
    path: str
    explanation: str
    key_entities: List[str]
    complexity_score: Optional[float] = None
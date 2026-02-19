from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

def utc_now():
    """Get current UTC time in timezone-aware format."""
    return datetime.now(timezone.utc)


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    owner = Column(String(255), nullable=False)
    description = Column(Text)
    default_branch = Column(String(100), default="main")
    last_synced_at = Column(DateTime, default=utc_now)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    status_message = Column(Text)
    file_count = Column(Integer, default=0)
    language_breakdown = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)
    
    # Relationships
    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="repository", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    path = Column(String(500), nullable=False)
    extension = Column(String(20))
    size_bytes = Column(Integer)
    line_count = Column(Integer)
    language = Column(String(50), index=True)
    summary = Column(Text)  # AI-generated summary
    last_modified_at = Column(DateTime)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    repository = relationship("Repository", back_populates="files")
    entities = relationship("Entity", back_populates="file", cascade="all, delete-orphan")

    # Composite indexes
    __table_args__ = (
        Index('idx_files_repo_language', 'repo_id', 'language'),
    )


class EntityType(str, enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"


class Entity(Base):
    """Code entities: functions, classes, methods, etc."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(Enum(EntityType), nullable=False, index=True)
    start_line = Column(Integer)
    end_line = Column(Integer)
    signature = Column(Text)
    docstring = Column(Text)
    logic_summary = Column(Text)  # AI-generated explanation
    code_snippet = Column(Text)  # Raw code
    vector_id = Column(String(100))  # Reference to vector store
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    repository = relationship("Repository", back_populates="entities")
    file = relationship("File", back_populates="entities")
    outgoing_relations = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    incoming_relations = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target"
    )

    # Composite indexes
    __table_args__ = (
        Index('idx_entities_repo_type', 'repo_id', 'type'),
        Index('idx_entities_file_type', 'file_id', 'type'),
    )


class RelationshipType(str, enum.Enum):
    CALLS = "calls"           # Function A calls Function B
    INHERITS = "inherits"     # Class A inherits from Class B
    IMPORTS = "imports"       # File A imports from File B
    CONTAINS = "contains"     # Class A contains Method B
    REFERENCES = "references" # Function A references Variable B


class Relationship(Base):
    """Relationships between code entities"""
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    target_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    relationship_type = Column(Enum(RelationshipType), nullable=False, index=True)
    rel_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    source = relationship("Entity", foreign_keys=[source_entity_id], back_populates="outgoing_relations")
    target = relationship("Entity", foreign_keys=[target_entity_id], back_populates="incoming_relations")

    # Composite indexes
    __table_args__ = (
        Index('idx_relationships_source_type', 'source_entity_id', 'relationship_type'),
        Index('idx_relationships_target_type', 'target_entity_id', 'relationship_type'),
    )
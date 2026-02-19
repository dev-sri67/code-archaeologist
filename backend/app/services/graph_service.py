"""
Graph Service
Generates graph data for visualization in React Flow.
"""
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from app.models import Repository, File, Entity, EntityType, Relationship


class GraphService:
    """Generate graph structures for frontend visualization."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_repo_graph(self, repo_id: int) -> Dict[str, List[Dict]]:
        """Generate nodes and edges for repository visualization."""
        
        nodes = []
        edges = []
        node_positions = {}
        
        # Get repository
        result = await self.db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            return {"nodes": [], "edges": []}
        
        # Get files
        result = await self.db.execute(
            select(File).where(File.repo_id == repo_id)
        )
        files = result.scalars().all()
        
        # Group files by type/module
        file_groups = self._group_files_by_module(files)
        
        # Create module nodes
        y_offset = 0
        for module_name, module_files in file_groups.items():
            module_id = f"module_{self._hash_id(module_name)}"
            
            nodes.append({
                "id": module_id,
                "type": "module",
                "label": module_name,
                "position": {"x": 0, "y": y_offset},
                "data": {
                    "file_count": len(module_files),
                    "languages": list(set(f.language for f in module_files if f.language))
                },
                "style": {
                    "backgroundColor": "#e3f2fd",
                    "border": "2px solid #1976d2",
                    "borderRadius": "8px",
                    "padding": "10px"
                }
            })
            
            # Add file nodes inside module
            x_offset = 200
            for file in module_files:
                file_id = f"file_{file.id}"
                nodes.append({
                    "id": file_id,
                    "type": "file",
                    "label": file.path.split('/')[-1],
                    "position": {"x": x_offset, "y": y_offset},
                    "data": {
                        "path": file.path,
                        "language": file.language,
                        "line_count": file.line_count,
                        "summary": file.summary
                    },
                    "style": {
                        "backgroundColor": self._get_language_color(file.language),
                        "borderRadius": "4px",
                        "padding": "5px"
                    }
                })
                
                # Connect module to file
                edges.append({
                    "id": f"e_{module_id}_{file_id}",
                    "source": module_id,
                    "target": file_id,
                    "type": "smoothstep",
                    "style": {"stroke": "#90a4ae"}
                })
                
                y_offset += 80
            
            y_offset += 40
        
        # Add entity nodes for items with logic summaries
        result = await self.db.execute(
            select(Entity).where(Entity.repo_id == repo_id)
        )
        entities = result.scalars().all()
        
        for entity in entities:
            if not entity.file_id:
                continue
                
            entity_id = f"entity_{entity.id}"
            parent_file_id = f"file_{entity.file_id}"
            
            nodes.append({
                "id": entity_id,
                "type": "entity",
                "label": entity.name,
                "position": {"x": 500, "y": y_offset},
                "data": {
                    "type": entity.type.value,
                    "lines": f"{entity.start_line}-{entity.end_line}",
                    "summary": entity.logic_summary
                },
                "style": {
                    "backgroundColor": self._get_entity_color(entity.type),
                    "borderRadius": "50%",
                    "width": "60px",
                    "height": "60px"
                }
            })
            
            # Connect file to entity
            edges.append({
                "id": f"e_{parent_file_id}_{entity_id}",
                "source": parent_file_id,
                "target": entity_id,
                "type": "smoothstep",
                "label": entity.type.value,
                "style": {"stroke": "#64b5f6"}
            })
            
            y_offset += 70
        
        return {"nodes": nodes, "edges": edges}
    
    def _group_files_by_module(self, files: List[File]) -> Dict[str, List[File]]:
        """Group files by their directory structure."""
        groups = {}
        
        for file in files:
            path_parts = file.path.split('/')
            if len(path_parts) > 1:
                # Group by root directory
                module = path_parts[0]
            else:
                module = "root"
            
            if module not in groups:
                groups[module] = []
            groups[module].append(file)
        
        # Sort to keep consistent ordering
        return dict(sorted(groups.items()))
    
    def _hash_id(self, text: str) -> str:
        """Create a short hash for IDs."""
        return hashlib.md5(text.encode()).hexdigest()[:8]
    
    def _get_language_color(self, language: str) -> str:
        """Get color for language."""
        colors = {
            "python": "#ffd54f",
            "javascript": "#ffeb3b",
            "typescript": "#a1887f",
            "other": "#e0e0e0"
        }
        return colors.get(language, colors["other"])
    
    def _get_entity_color(self, entity_type: EntityType) -> str:
        """Get color for entity type."""
        colors = {
            EntityType.FUNCTION: "#81c784",
            EntityType.CLASS: "#ff8a65",
            EntityType.METHOD: "#4db6ac",
            EntityType.VARIABLE: "#90caf9",
            EntityType.IMPORT: "#ce93d8",
            EntityType.MODULE: "#b0bec5"
        }
        return colors.get(entity_type, "#e0e0e0")
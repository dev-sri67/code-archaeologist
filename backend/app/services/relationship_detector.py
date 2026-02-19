"""
Relationship Detection Service
Detects and extracts relationships between code entities.
"""
import re
from typing import List, Dict, Set, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Entity, File, Relationship, RelationshipType, EntityType, Repository


class RelationshipDetector:
    """Detects relationships between code entities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def detect_all_relationships(self, repo_id: int) -> int:
        """
        Detect all relationships in a repository.
        
        Returns:
            Number of relationships detected
        """
        # Get all entities
        result = await self.db.execute(
            select(Entity).where(Entity.repo_id == repo_id)
        )
        entities = result.scalars().all()
        
        # Build entity name map for quick lookup
        entity_map = {entity.name: entity for entity in entities}
        
        relationships_created = 0
        
        for entity in entities:
            if not entity.code_snippet:
                continue
            
            # Detect calls
            called_names = self._extract_function_calls(entity.code_snippet)
            for called_name in called_names:
                if called_name in entity_map and called_name != entity.name:
                    rel = Relationship(
                        source_entity_id=entity.id,
                        target_entity_id=entity_map[called_name].id,
                        relationship_type=RelationshipType.CALLS
                    )
                    self.db.add(rel)
                    relationships_created += 1
            
            # Detect contains (methods in classes)
            if entity.type == EntityType.CLASS:
                contained_methods = self._extract_class_methods(entity.code_snippet)
                for method_name in contained_methods:
                    if method_name in entity_map:
                        rel = Relationship(
                            source_entity_id=entity.id,
                            target_entity_id=entity_map[method_name].id,
                            relationship_type=RelationshipType.CONTAINS
                        )
                        self.db.add(rel)
                        relationships_created += 1
            
            # Detect inheritance
            if entity.type == EntityType.CLASS:
                parent_names = self._extract_parent_classes(entity.code_snippet)
                for parent_name in parent_names:
                    if parent_name in entity_map:
                        rel = Relationship(
                            source_entity_id=entity.id,
                            target_entity_id=entity_map[parent_name].id,
                            relationship_type=RelationshipType.INHERITS
                        )
                        self.db.add(rel)
                        relationships_created += 1
        
        # Detect file-level imports
        await self._detect_imports(repo_id, relationships_created)
        
        await self.db.commit()
        return relationships_created
    
    async def _detect_imports(self, repo_id: int, rel_count: int) -> int:
        """Detect import relationships between files."""
        
        # Get all files
        result = await self.db.execute(
            select(File).where(File.repo_id == repo_id)
        )
        files = result.scalars().all()
        
        file_map = {file.path: file for file in files}
        
        imports_found = 0
        
        for file in files:
            # Get entities in this file to link imports
            result = await self.db.execute(
                select(Entity).where(Entity.file_id == file.id)
            )
            entities = result.scalars().all()
            
            for entity in entities:
                if not entity.code_snippet:
                    continue
                
                # Extract imports from code
                imported_modules = self._extract_imports(entity.code_snippet)
                
                for imported_path in imported_modules:
                    # Try to find corresponding file
                    for potential_file_path, potential_file in file_map.items():
                        if self._is_import_match(imported_path, potential_file_path):
                            # Create import relationship
                            rel = Relationship(
                                source_entity_id=entity.id,
                                target_entity_id=None,  # File-level
                                relationship_type=RelationshipType.IMPORTS,
                                rel_metadata={
                                    "source_file": file.path,
                                    "target_file": potential_file_path,
                                    "import_name": imported_path
                                }
                            )
                            self.db.add(rel)
                            imports_found += 1
                            break
        
        return imports_found
    
    def _extract_function_calls(self, code: str) -> Set[str]:
        """Extract function call names from code."""
        calls = set()
        
        # Keywords to exclude
        keywords = {'if', 'for', 'while', 'def', 'class', 'return', 'with', 'try', 'except',
                    'elif', 'else', 'switch', 'case', 'do', 'catch', 'finally', 'function',
                    'const', 'let', 'var', 'new', 'typeof', 'instanceof', 'delete', 'throw'}
        
        # Python function calls: func_name(
        python_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(python_pattern, code):
            func_name = match.group(1)
            # Exclude keywords and special methods
            if func_name not in keywords:
                calls.add(func_name)
        
        # JavaScript/TypeScript calls
        js_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\('
        for match in re.finditer(js_pattern, code):
            func_name = match.group(1)
            if func_name not in keywords:
                calls.add(func_name)
        
        return calls
    
    def _extract_class_methods(self, code: str) -> Set[str]:
        """Extract method names defined within a class."""
        methods = set()
        
        # Python methods in class (indented def)
        python_pattern = r'^\s{2,}def\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(python_pattern, code, re.MULTILINE):
            methods.add(match.group(1))
        
        # JavaScript methods in class
        js_pattern = r'(?:^\s+)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\('
        for match in re.finditer(js_pattern, code, re.MULTILINE):
            methods.add(match.group(1))
        
        return methods
    
    def _extract_parent_classes(self, code: str) -> Set[str]:
        """Extract parent class names from inheritance."""
        parents = set()
        
        # Python inheritance: class ChildClass(ParentClass, Mixin):
        # This captures the entire parentheses content, then extracts individual parents
        python_pattern = r'class\s+\w+\s*\(\s*([^)]+)\s*\)'
        for match in re.finditer(python_pattern, code):
            parent_list = match.group(1)
            # Split by comma and extract each parent name
            for parent in parent_list.split(','):
                parent_name = parent.strip()
                # Remove any brackets/generics for TypeScript/Java style
                parent_name = parent_name.split('[')[0].strip()
                if parent_name and parent_name.isidentifier():
                    parents.add(parent_name)
        
        # JavaScript/TypeScript extends: class Child extends Parent
        js_pattern = r'class\s+\w+\s+extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*)'
        for match in re.finditer(js_pattern, code):
            parents.add(match.group(1))
        
        return parents
    
    def _extract_imports(self, code: str) -> Set[str]:
        """Extract import module names."""
        imports = set()
        
        # Python imports
        python_patterns = [
            r'from\s+([a-zA-Z0-9._]+)\s+import',
            r'import\s+([a-zA-Z0-9._]+)',
        ]
        
        for pattern in python_patterns:
            for match in re.finditer(pattern, code):
                imports.add(match.group(1))
        
        # JavaScript/TypeScript imports
        js_patterns = [
            r"import\s+.*from\s+['\"]([^'\"]+)['\"]",
            r"require\s*\(\s*['\"]([^'\"]+)['\"]",
        ]
        
        for pattern in js_patterns:
            for match in re.finditer(pattern, code):
                imports.add(match.group(1))
        
        return imports
    
    def _is_import_match(self, import_path: str, file_path: str) -> bool:
        """
        Check if an import path matches a file path.
        
        Examples:
            import_path='utils.helpers', file_path='utils/helpers.py' -> True
            import_path='./models', file_path='models/index.js' -> True
            import_path='utils', file_path='helpers/utils.py' -> False
            import_path='utils', file_path='utils/helpers.js' -> True
        """
        # Normalize paths
        import_normalized = import_path.replace('.', '/').strip('./ ')
        file_normalized = file_path.replace('\\', '/').lower()
        
        # Remove extensions from file path
        file_base = file_normalized.rsplit('.', 1)[0]
        
        # Handle __init__ files: 'models' should match 'models/__init__'
        if file_base.endswith('/__init__'):
            file_base = file_base.replace('/__init__', '')
        
        # Direct match
        if file_base == import_normalized:
            return True
        
        # Check if file is inside import directory: 
        # 'utils' matches 'utils/helpers' or 'utils/index'
        # but NOT 'helpers/utils' (because utils is not a directory prefix)
        if file_base.startswith(import_normalized + '/'):
            return True
        
        return False
    
    async def get_call_graph(self, repo_id: int) -> Dict:
        """
        Generate a call graph for the repository.
        
        Returns:
            {
                'nodes': [{'id': entity_id, 'name': entity_name, ...}],
                'edges': [{'source': id1, 'target': id2, 'type': 'calls'}]
            }
        """
        # Get all CALLS relationships
        result = await self.db.execute(
            select(Relationship).where(
                (Relationship.relationship_type == RelationshipType.CALLS)
            )
        )
        relationships = result.scalars().all()
        
        # Get entities involved
        entity_ids = set()
        for rel in relationships:
            entity_ids.add(rel.source_entity_id)
            entity_ids.add(rel.target_entity_id)
        
        result = await self.db.execute(
            select(Entity).where(Entity.id.in_(entity_ids))
        )
        entities = result.scalars().all()
        entity_map = {e.id: e for e in entities}
        
        # Build graph
        nodes = [
            {
                'id': entity.id,
                'name': entity.name,
                'type': entity.type.value,
                'in_degree': sum(1 for r in relationships if r.target_entity_id == entity.id),
                'out_degree': sum(1 for r in relationships if r.source_entity_id == entity.id),
            }
            for entity in entities
        ]
        
        edges = [
            {
                'source': rel.source_entity_id,
                'target': rel.target_entity_id,
                'type': 'calls'
            }
            for rel in relationships
        ]
        
        return {'nodes': nodes, 'edges': edges}
    
    async def get_dependency_matrix(self, repo_id: int) -> Dict:
        """
        Generate a dependency matrix for files.
        
        Returns matrix of which files depend on which files.
        """
        result = await self.db.execute(
            select(File).where(File.repo_id == repo_id)
        )
        files = result.scalars().all()
        
        # Initialize matrix
        matrix = {
            file.path: {other_file.path: 0 for other_file in files}
            for file in files
        }
        
        # Get all import relationships
        result = await self.db.execute(
            select(Relationship).where(
                (Relationship.relationship_type == RelationshipType.IMPORTS)
            )
        )
        imports = result.scalars().all()
        
        # Populate matrix
        for import_rel in imports:
            metadata = import_rel.rel_metadata or {}
            source_file = metadata.get('source_file')
            target_file = metadata.get('target_file')
            
            if source_file in matrix and target_file in matrix[source_file]:
                matrix[source_file][target_file] += 1
        
        return matrix
    
    async def detect_circular_dependencies(self, repo_id: int) -> List[List[str]]:
        """
        Detect circular dependencies in the repository.
        
        Returns:
            List of dependency cycles (each cycle is a list of file paths)
        """
        # Build dependency graph
        dependency_matrix = await self.get_dependency_matrix(repo_id)
        
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            """DFS to find cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor, count in dependency_matrix[node].items():
                if count > 0:
                    if neighbor not in visited:
                        dfs(neighbor, path)
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        if cycle not in cycles:  # Avoid duplicates
                            cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        # Find all cycles
        for file_path in dependency_matrix.keys():
            if file_path not in visited:
                dfs(file_path, [])
        
        return cycles

"""
Code Analysis Routes

API endpoints for advanced code analysis features:
- Relationships and dependency graphs
- Code metrics
- Refactoring suggestions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.models import Repository, Entity, Relationship, RelationshipType, File
from app.schemas import RelationshipResponse
from app.services.relationship_detector import RelationshipDetector
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/repos/{repo_id}/relationships", response_model=List[RelationshipResponse])
async def get_repository_relationships(
    repo_id: int,
    relationship_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all relationships in a repository.
    
    Query params:
        relationship_type: Filter by type ('calls', 'imports', 'inherits', 'contains', 'references')
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Build query
    query = select(Relationship)
    
    if relationship_type:
        try:
            rel_type_enum = RelationshipType(relationship_type.lower())
            query = query.where(Relationship.relationship_type == rel_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship_type. Valid values: {[t.value for t in RelationshipType]}"
            )
    
    result = await db.execute(query)
    relationships = result.scalars().all()
    
    return relationships


@router.get("/repos/{repo_id}/dependencies")
async def get_repository_dependencies(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get file dependency graph.
    
    Shows which files depend on which files through imports.
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    detector = RelationshipDetector(db)
    
    try:
        dependency_matrix = await detector.get_dependency_matrix(repo_id)
        cycles = await detector.detect_circular_dependencies(repo_id)
        
        return {
            'repo_id': repo_id,
            'dependency_matrix': dependency_matrix,
            'circular_dependencies': cycles,
            'total_dependencies': sum(
                sum(1 for count in deps.values() if count > 0)
                for deps in dependency_matrix.values()
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing dependencies: {str(e)}")


@router.get("/repos/{repo_id}/call-graph")
async def get_call_graph(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get call graph showing which functions call which functions.
    
    Returns nodes (functions) and edges (calls) suitable for visualization.
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    detector = RelationshipDetector(db)
    
    try:
        call_graph = await detector.get_call_graph(repo_id)
        return call_graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating call graph: {str(e)}")


@router.get("/entities/{entity_id}/relations")
async def get_entity_relations(
    entity_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all relationships for a specific entity.
    
    Returns both incoming and outgoing relationships.
    """
    # Verify entity exists
    entity = await db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Get outgoing relationships
    result = await db.execute(
        select(Relationship).where(Relationship.source_entity_id == entity_id)
    )
    outgoing = result.scalars().all()
    
    # Get incoming relationships
    result = await db.execute(
        select(Relationship).where(Relationship.target_entity_id == entity_id)
    )
    incoming = result.scalars().all()
    
    # Get related entity details
    outgoing_details = []
    for rel in outgoing:
        target = await db.get(Entity, rel.target_entity_id)
        if target:
            outgoing_details.append({
                'relationship_id': rel.id,
                'type': rel.relationship_type.value,
                'source': {'id': entity.id, 'name': entity.name},
                'target': {'id': target.id, 'name': target.name},
                'metadata': rel.rel_metadata
            })
    
    incoming_details = []
    for rel in incoming:
        source = await db.get(Entity, rel.source_entity_id)
        if source:
            incoming_details.append({
                'relationship_id': rel.id,
                'type': rel.relationship_type.value,
                'source': {'id': source.id, 'name': source.name},
                'target': {'id': entity.id, 'name': entity.name},
                'metadata': rel.rel_metadata
            })
    
    return {
        'entity_id': entity_id,
        'entity_name': entity.name,
        'outgoing': outgoing_details,
        'incoming': incoming_details,
        'total_relations': len(outgoing_details) + len(incoming_details)
    }


@router.get("/repos/{repo_id}/metrics")
async def get_repository_metrics(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get code metrics for a repository.
    
    Includes:
    - LOC (lines of code)
    - Complexity metrics
    - Modularity score
    - Coupling metrics
    - Hotspots
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Get all entities
    result = await db.execute(
        select(Entity).where(Entity.repo_id == repo_id)
    )
    entities = result.scalars().all()
    
    # Get all relationships
    result = await db.execute(
        select(Relationship)
    )
    all_relationships = result.scalars().all()
    
    # Calculate metrics
    total_loc = sum((entity.end_line or 0) - (entity.start_line or 0) for entity in entities)
    
    # Complexity: number of relationships per entity
    entity_complexity = {}
    for entity in entities:
        in_degree = sum(1 for r in all_relationships if r.target_entity_id == entity.id)
        out_degree = sum(1 for r in all_relationships if r.source_entity_id == entity.id)
        entity_complexity[entity.name] = in_degree + out_degree
    
    # Find hotspots (entities with high complexity)
    hotspots = sorted(entity_complexity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'repo_id': repo_id,
        'total_lines_of_code': total_loc,
        'total_entities': len(entities),
        'total_relationships': len(all_relationships),
        'average_complexity': sum(entity_complexity.values()) / len(entity_complexity) if entity_complexity else 0,
        'hotspots': [{'name': name, 'complexity': score} for name, score in hotspots],
        'entities_by_type': {
            'functions': len([e for e in entities if e.type.value == 'function']),
            'classes': len([e for e in entities if e.type.value == 'class']),
            'methods': len([e for e in entities if e.type.value == 'method']),
            'variables': len([e for e in entities if e.type.value == 'variable']),
            'imports': len([e for e in entities if e.type.value == 'import']),
            'modules': len([e for e in entities if e.type.value == 'module']),
        }
    }


@router.get("/repos/{repo_id}/refactoring-suggestions")
async def get_refactoring_suggestions(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get refactoring suggestions for the repository.
    
    Uses AI to identify:
    - High complexity functions
    - Highly coupled modules
    - Dead code candidates
    - Refactoring opportunities
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Get hotspot entities
    result = await db.execute(
        select(Entity).where(Entity.repo_id == repo_id)
    )
    entities = result.scalars().all()
    
    # Get relationships for complexity analysis
    detector = RelationshipDetector(db)
    call_graph = await detector.get_call_graph(repo_id)
    
    suggestions = []
    llm_service = LLMService()
    
    # Analyze top hotspots
    sorted_nodes = sorted(call_graph['nodes'], key=lambda x: x['in_degree'] + x['out_degree'], reverse=True)
    
    for node in sorted_nodes[:5]:  # Top 5 hotspots
        entity = next((e for e in entities if e.id == node['id']), None)
        if not entity or not entity.code_snippet:
            continue
        
        # Get LLM suggestions
        try:
            refactoring_ideas = await llm_service.suggest_refactorings(
                entity.code_snippet,
                'python',  # Would need to be dynamic based on language
                {'complexity': node['in_degree'] + node['out_degree']}
            )
            
            suggestions.extend([
                {
                    'entity_id': entity.id,
                    'entity_name': entity.name,
                    'entity_type': entity.type.value,
                    'title': idea.get('title'),
                    'description': idea.get('description'),
                    'priority': idea.get('priority', 'medium'),
                    'complexity_score': node['in_degree'] + node['out_degree']
                }
                for idea in refactoring_ideas[:3]
            ])
        except Exception as e:
            pass  # Continue if LLM fails
    
    return {
        'repo_id': repo_id,
        'suggestions': suggestions,
        'total_suggestions': len(suggestions)
    }


@router.post("/repos/{repo_id}/scan-circular-deps")
async def scan_circular_dependencies(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan for circular dependencies in the repository.
    
    Returns all dependency cycles found.
    """
    # Verify repo exists
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    detector = RelationshipDetector(db)
    
    try:
        cycles = await detector.detect_circular_dependencies(repo_id)
        
        return {
            'repo_id': repo_id,
            'circular_dependencies': cycles,
            'total_cycles': len(cycles),
            'severity': 'high' if len(cycles) > 5 else 'medium' if len(cycles) > 0 else 'low'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning for circular dependencies: {str(e)}")

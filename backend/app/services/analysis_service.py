"""
Analysis Service
Orchestrates the full repository analysis pipeline.
Uses batched LLM calls and batch embeddings for efficiency.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import logging
import math

from app.models import Repository, File, Entity, EntityType, AnalysisStatus
from app.services.repository_ingester import RepositoryIngester
from app.services.ast_parser import ASTParser
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService
from app.services.relationship_detector import RelationshipDetector
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AnalysisService:
    """Coordinates the analysis of code repositories."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ingester = RepositoryIngester()
        self.parser = ASTParser()
        self.vector_store = VectorStore()
        self.llm = LLMService()

    async def analyze_repository(self, repo_id: int) -> None:
        """
        Run full analysis pipeline on a repository.

        Phases:
        1. Clone and scan repository files
        2. Parse code entities with batched LLM summaries
        3. Detect relationships between entities
        4. Generate embeddings (batch)
        5. Finalize and update status
        """
        repo = await self.db.get(Repository, repo_id)
        if not repo:
            logger.error(f"Repository {repo_id} not found")
            raise ValueError(f"Repository {repo_id} not found")

        logger.info(f"Starting analysis for repository: {repo.name} (id={repo_id})")
        repo.status = AnalysisStatus.IN_PROGRESS
        repo.status_message = "Starting analysis..."
        await self.db.commit()

        try:
            # Phase 1: Clone and scan
            logger.debug(f"Phase 1: Cloning and scanning repository {repo_id}")
            repo_path = await self._clone_and_scan(repo_id)

            # Phase 2: Parse code entities (batched LLM calls)
            logger.debug(f"Phase 2: Parsing code entities for repository {repo_id}")
            await self._parse_entities(repo_id, repo_path)

            # Phase 3: Detect relationships (if enabled)
            if settings.ENABLE_RELATIONSHIP_DETECTION:
                logger.debug(f"Phase 3: Detecting relationships for repository {repo_id}")
                await self._detect_relationships(repo_id)
            else:
                logger.debug(f"Phase 3: Skipped (relationship detection disabled)")

            # Phase 4: Generate embeddings (batch)
            logger.debug(f"Phase 4: Generating embeddings for repository {repo_id}")
            await self._generate_embeddings(repo_id)

            # Phase 5: Finalize
            logger.info(f"Analysis completed successfully for repository {repo_id}")
            repo.status = AnalysisStatus.COMPLETED
            repo.status_message = "Analysis complete"
            await self.db.commit()

        except Exception as e:
            logger.error(f"Analysis failed for repository {repo_id}: {str(e)}", exc_info=True)
            repo.status = AnalysisStatus.FAILED
            repo.status_message = f"Analysis failed: {str(e)}"
            await self.db.commit()
            raise
        finally:
            self.ingester.cleanup()
            logger.debug(f"Cleaned up temporary files for repository {repo_id}")

    async def _clone_and_scan(self, repo_id: int) -> str:
        """Clone repo and save file metadata."""
        repo = await self.db.get(Repository, repo_id)
        repo.status_message = "Cloning repository..."
        await self.db.commit()

        repo_path = await self.ingester.clone_repository(repo.url)

        repo.status_message = "Scanning files..."
        await self.db.commit()

        files = await self.ingester.scan_files(repo_path)

        for file_info in files:
            file_record = File(
                repo_id=repo_id,
                path=file_info['path'],
                extension=file_info['extension'],
                size_bytes=file_info['size_bytes'],
                language=file_info['language']
            )
            self.db.add(file_record)

        repo.file_count = len(files)
        repo.language_breakdown = await self.ingester.get_language_breakdown(files)
        await self.db.commit()

        return repo_path

    async def _parse_entities(self, repo_id: int, repo_path: str) -> None:
        """Parse code structure, then batch-generate file summaries and entity explanations."""
        repo = await self.db.get(Repository, repo_id)
        repo.status_message = "Parsing code structure..."
        await self.db.commit()

        result = await self.db.execute(
            select(File).where(File.repo_id == repo_id)
        )
        files = result.scalars().all()

        # Phase 2a: Parse all files and collect data for batching
        files_for_summary = []  # (file_record, content, entities_data)
        all_entities_for_explanation = []  # (entity_data, language, file_record)

        for file_record in files:
            if not file_record.language:
                continue

            abs_path = f"{repo_path}/{file_record.path}"
            content = await self.ingester.read_file_content(abs_path)

            entities = self.parser.parse_file(content, file_record.language)

            if entities:
                file_record.line_count = len(content.split('\n'))
                files_for_summary.append({
                    'file_record': file_record,
                    'path': file_record.path,
                    'code': content,
                    'language': file_record.language,
                    'entities': entities,
                })

            for entity_data in entities:
                all_entities_for_explanation.append({
                    'entity_data': entity_data,
                    'language': file_record.language,
                    'file_record': file_record,
                })

        # Phase 2b: Batch generate file summaries (3 files per LLM call)
        if files_for_summary:
            repo.status_message = f"Generating summaries for {len(files_for_summary)} files..."
            await self.db.commit()

            summary_inputs = [
                {'path': f['path'], 'code': f['code'], 'language': f['language']}
                for f in files_for_summary
            ]
            summaries = await self.llm.generate_file_summaries_batch(summary_inputs)

            for f_info, summary in zip(files_for_summary, summaries):
                f_info['file_record'].summary = summary

        # Phase 2c: Batch generate entity explanations (5 per LLM call)
        if all_entities_for_explanation:
            repo.status_message = f"Explaining {len(all_entities_for_explanation)} code entities..."
            await self.db.commit()

            explanation_inputs = [
                {
                    'name': e['entity_data']['name'],
                    'code': e['entity_data']['code'][:2000],
                    'language': e['language'],
                }
                for e in all_entities_for_explanation
            ]
            explanations = await self.llm.explain_functions_batch(explanation_inputs)

            # Create Entity records with explanations
            for e_info, explanation in zip(all_entities_for_explanation, explanations):
                entity_data = e_info['entity_data']
                entity = Entity(
                    repo_id=repo_id,
                    file_id=e_info['file_record'].id,
                    name=entity_data['name'],
                    type=EntityType(entity_data['type']),
                    start_line=entity_data['start_line'],
                    end_line=entity_data['end_line'],
                    code_snippet=entity_data['code'][:2000],
                    logic_summary=explanation,
                )
                self.db.add(entity)

        await self.db.commit()

    async def _detect_relationships(self, repo_id: int) -> None:
        """Detect relationships between code entities."""
        repo = await self.db.get(Repository, repo_id)
        repo.status_message = "Detecting code relationships..."
        await self.db.commit()

        detector = RelationshipDetector(self.db)
        rel_count = await detector.detect_all_relationships(repo_id)

        repo.status_message = f"Detected {rel_count} relationships"
        await self.db.commit()

    async def _generate_embeddings(self, repo_id: int) -> None:
        """Generate embeddings for all entities using batch encoding."""
        repo = await self.db.get(Repository, repo_id)
        repo.status_message = "Generating embeddings..."
        await self.db.commit()

        result = await self.db.execute(
            select(Entity).where(Entity.repo_id == repo_id)
        )
        entities = result.scalars().all()

        # Build batch documents
        documents = []
        for entity in entities:
            code = entity.code_snippet or entity.logic_summary or ""
            metadata = {
                'file_path': entity.file.path if entity.file else 'unknown',
                'entity_name': entity.name,
                'entity_type': entity.type.value,
                'repo_id': repo_id,
                'line_range': [entity.start_line, entity.end_line]
            }
            documents.append({
                'snippet_id': f"entity_{entity.id}",
                'code': code,
                'metadata': metadata,
            })

        # Use batch add (generates all embeddings in one batch call)
        batch_size = settings.BATCH_SIZE
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            await self.vector_store.add_documents_batch(repo_id, batch)

        logger.info(f"Generated embeddings for {len(documents)} entities")
        repo.status_message = "Embeddings generated"
        await self.db.commit()

    async def get_analysis_status(self, repo_id: int) -> Dict[str, Any]:
        """Get current analysis status."""
        repo = await self.db.get(Repository, repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        return {
            'id': repo_id,
            'status': repo.status.value,
            'status_message': repo.status_message,
            'progress_percent': self._calculate_progress(repo)
        }

    def _calculate_progress(self, repo: Repository) -> float:
        """Estimate analysis progress."""
        status_map = {
            AnalysisStatus.PENDING: 0.0,
            AnalysisStatus.IN_PROGRESS: 50.0,
            AnalysisStatus.COMPLETED: 100.0,
            AnalysisStatus.FAILED: 0.0
        }
        return status_map.get(repo.status, 0.0)

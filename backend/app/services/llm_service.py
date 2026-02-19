"""LLM Service - OpenAI-compatible implementation (works with Ollama)

Provides AI-powered code analysis capabilities.
Includes batch methods for efficient multi-file/entity processing.
"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import get_settings
import logging
import asyncio
import math

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMService:
    """LLM service for code analysis (OpenAI-compatible, defaults to Ollama)."""

    def __init__(self):
        api_key = settings.OPENAI_API_KEY or "ollama"
        client_kwargs = {"api_key": api_key}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        self.client = AsyncOpenAI(**client_kwargs)
        self.model = settings.OPENAI_MODEL or "deepseek-coder-v2:16b"

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """Call LLM API with proper error handling."""
        if temperature is None:
            temperature = settings.OPENAI_TEMPERATURE

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise Exception(f"LLM API error: {str(e)}")

    # ── Single-item methods (used by chat/analysis routers) ──

    async def generate_file_summary(self, file_path: str, code: str, language: str) -> str:
        """Generate a summary of a file."""
        system_prompt = f"""You are a code analyst. Summarize the purpose and key functionality of this {language} file in 2-3 sentences.
Be concise and technical. Focus on what the file does, not line-by-line details."""

        user_prompt = f"""File: {file_path}
Language: {language}

```
{code[:4000]}
```

Provide a brief summary:"""

        return await self._call_llm(system_prompt, user_prompt)

    async def explain_function(self, name: str, code: str, language: str) -> str:
        """Explain a specific function."""
        system_prompt = f"""You are a code analyst. Explain what this {language} function does in 1-2 sentences.
Focus on inputs, outputs, and purpose."""

        user_prompt = f"""Function: {name}
Language: {language}

```
{code}
```

Brief explanation:"""

        return await self._call_llm(system_prompt, user_prompt)

    async def answer_query(self, query: str, code_snippets: List[Dict], repo_context: Any = None) -> Dict:
        """Answer a query based on relevant code snippets."""
        system_prompt = """You are a code analysis assistant. Answer the user's question based on the provided code snippets.
Include specific references to files and functions. Be technical and accurate.
If you cannot answer from the snippets, say so clearly."""

        # Format snippets for context
        snippets_text = []
        sources = []
        for i, snippet in enumerate(code_snippets[:settings.RAG_RESULTS_LIMIT]):
            meta = snippet.get('metadata', {})
            file_path = meta.get('file_path', 'unknown')
            entity_name = meta.get('entity_name', 'N/A')
            line_range = meta.get('line_range', [0, 0])
            code = snippet.get('code', '')

            snippets_text.append(f"""--- Snippet {i+1} ---
File: {file_path}
Entity: {entity_name}
Lines: {line_range[0]}-{line_range[1]}

```
{code[:2000]}
```
""")

            sources.append({
                'file_path': file_path,
                'entity_name': entity_name,
                'line_range': line_range,
                'code': code[:500]
            })

        user_prompt = f"""Question: {query}

{chr(10).join(snippets_text)}

Based on these code snippets, answer the question:"""

        answer = await self._call_llm(system_prompt, user_prompt)

        return {
            'answer': answer,
            'sources': sources,
            'confidence': 0.85
        }

    async def explain_file_detailed(self, file_path: str, code: str, entities: List, language: str) -> Dict:
        """Generate detailed file explanation with key entities."""
        system_prompt = f"""You are a code analyst. Provide a detailed explanation of this {language} file.
Include:
1. Overall purpose
2. Key components/functions
3. Dependencies and patterns used
4. Complexity assessment

Format with clear sections."""

        # Format entities
        entities_text = []
        entity_names = []
        for entity in entities[:10]:
            name = entity.get('name', 'unknown')
            entity_type = entity.get('type', 'unknown')
            line_start = entity.get('line_start', 0)

            entity_names.append(name)
            entities_text.append(f"- {name} ({entity_type}) at line {line_start}")

        user_prompt = f"""File: {file_path}
Language: {language}

Key entities:
{chr(10).join(entities_text)}

Full code:
```
{code[:5000]}
```

Provide a detailed analysis:"""

        explanation = await self._call_llm(system_prompt, user_prompt)

        return {
            'explanation': explanation,
            'key_entities': entity_names,
            'complexity_score': min(1.0, len(entities) / 20)
        }

    async def suggest_refactorings(self, code: str, language: str, context: Dict = None) -> List[Dict]:
        """Suggest potential refactoring opportunities."""
        system_prompt = """You are a senior software engineer reviewing code for refactoring opportunities.
Identify code smells, complexity issues, or improvements. If no issues found, say "No significant refactoring needed."

Return JSON format with suggestions:
{
    "suggestions": [
        {
            "title": "brief title",
            "description": "detailed explanation",
            "priority": "low|medium|high",
            "line_range": [start, end]
        }
    ]
}"""

        user_prompt = f"""Language: {language}

```
{code[:5000]}
```

Suggest refactorings (JSON format only):"""

        try:
            response = await self._call_llm(system_prompt, user_prompt)
            import json
            result = json.loads(response)
            return result.get('suggestions', [])
        except:
            return []

    # ── Batch methods (used by analysis pipeline) ──

    async def generate_file_summaries_batch(self, files: List[Dict]) -> List[str]:
        """Summarize multiple files per LLM call (3 files per prompt).

        Args:
            files: List of dicts with keys: path, code, language

        Returns:
            List of summary strings, one per input file.
        """
        batch_size = 3
        all_summaries = []
        semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)

        async def process_batch(batch: List[Dict]) -> List[str]:
            async with semaphore:
                return await self._summarize_files_batch(batch)

        tasks = []
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            tasks.append(process_batch(batch))

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(batch_results):
            batch = files[i * batch_size:(i + 1) * batch_size]
            if isinstance(result, Exception):
                logger.error(f"Batch file summary failed: {result}")
                all_summaries.extend(["Summary generation failed"] * len(batch))
            else:
                all_summaries.extend(result)

        return all_summaries

    async def _summarize_files_batch(self, files: List[Dict]) -> List[str]:
        """Internal: summarize a batch of files in a single LLM call."""
        system_prompt = """You are a code analyst. For each numbered file below, provide a 2-3 sentence technical summary.
Format your response as a numbered list matching the input numbers. Each summary should focus on what the file does."""

        file_sections = []
        for i, f in enumerate(files, 1):
            truncated = f['code'][:3000]
            file_sections.append(f"""[{i}] File: {f['path']} (Language: {f['language']})
```
{truncated}
```""")

        user_prompt = f"""Summarize each file:

{chr(10).join(file_sections)}

Provide numbered summaries:"""

        response = await self._call_llm(system_prompt, user_prompt)
        return self._parse_numbered_list(response, len(files))

    async def explain_functions_batch(self, functions: List[Dict]) -> List[str]:
        """Explain multiple functions/entities per LLM call (5 per prompt).

        Args:
            functions: List of dicts with keys: name, code, language

        Returns:
            List of explanation strings, one per input function.
        """
        batch_size = settings.LLM_BATCH_SIZE
        all_explanations = []
        semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)

        async def process_batch(batch: List[Dict]) -> List[str]:
            async with semaphore:
                return await self._explain_functions_batch(batch)

        tasks = []
        for i in range(0, len(functions), batch_size):
            batch = functions[i:i + batch_size]
            tasks.append(process_batch(batch))

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(batch_results):
            batch = functions[i * batch_size:(i + 1) * batch_size]
            if isinstance(result, Exception):
                logger.error(f"Batch function explanation failed: {result}")
                all_explanations.extend(["Explanation generation failed"] * len(batch))
            else:
                all_explanations.extend(result)

        return all_explanations

    async def _explain_functions_batch(self, functions: List[Dict]) -> List[str]:
        """Internal: explain a batch of functions in a single LLM call."""
        system_prompt = """You are a code analyst. For each numbered function below, explain what it does in 1-2 sentences.
Focus on inputs, outputs, and purpose. Format as a numbered list matching the input numbers."""

        func_sections = []
        for i, f in enumerate(functions, 1):
            truncated = f['code'][:1500]
            func_sections.append(f"""[{i}] {f['name']} ({f['language']}):
```
{truncated}
```""")

        user_prompt = f"""Explain each function:

{chr(10).join(func_sections)}

Provide numbered explanations:"""

        response = await self._call_llm(system_prompt, user_prompt)
        return self._parse_numbered_list(response, len(functions))

    def _parse_numbered_list(self, response: str, expected_count: int) -> List[str]:
        """Parse a numbered list response from the LLM.

        Handles formats like:
        - [1] Summary text
        - 1. Summary text
        - 1) Summary text

        Falls back to splitting by double newlines if numbered parsing fails.
        """
        import re
        lines = response.strip().split('\n')

        # Try parsing numbered items
        items = []
        current_item = []
        current_num = 0

        for line in lines:
            # Match numbered patterns: [1], 1., 1)
            match = re.match(r'^\s*(?:\[(\d+)\]|(\d+)[.)]\s)', line)
            if match:
                num = int(match.group(1) or match.group(2))
                if current_item:
                    items.append(' '.join(current_item).strip())
                current_item = [re.sub(r'^\s*(?:\[\d+\]|\d+[.)]\s*)', '', line).strip()]
                current_num = num
            elif current_item:
                current_item.append(line.strip())

        if current_item:
            items.append(' '.join(current_item).strip())

        # If we got the right number of items, return them
        if len(items) == expected_count:
            return items

        # Fallback: if we got more items than expected, take first N
        if len(items) > expected_count:
            return items[:expected_count]

        # Fallback: split by double newlines
        if len(items) < expected_count:
            paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
            if len(paragraphs) >= expected_count:
                return paragraphs[:expected_count]

        # Last resort: pad with the response or a default
        while len(items) < expected_count:
            items.append("Summary not available")

        return items

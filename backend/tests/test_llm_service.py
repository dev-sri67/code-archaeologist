"""
Unit tests for LLM service.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_service import LLMService


class TestLLMService:
    """Test LLM service functionality."""
    
    @pytest.fixture
    def llm_service(self, test_settings):
        """Create LLM service instance."""
        return LLMService()
    
    @pytest.mark.asyncio
    async def test_generate_file_summary(self, llm_service):
        """Test file summary generation."""
        code = """
        def calculate_factorial(n):
            if n <= 1:
                return 1
            return n * calculate_factorial(n - 1)
        """
        
        # Mock the OpenAI call
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = "Function to calculate factorial using recursion"
            
            result = await llm_service.generate_file_summary(
                'math_utils.py',
                code,
                'python'
            )
            
            assert isinstance(result, str)
            assert len(result) > 0
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_explain_function(self, llm_service):
        """Test function explanation generation."""
        code = """
        def add(a, b):
            return a + b
        """
        
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = "Adds two numbers and returns the result"
            
            result = await llm_service.explain_function(
                'add',
                code,
                'python'
            )
            
            assert isinstance(result, str)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_answer_query(self, llm_service):
        """Test query answering with code context."""
        snippets = [
            {
                'metadata': {
                    'file_path': 'utils.py',
                    'entity_name': 'add',
                    'line_range': [1, 3]
                },
                'code': 'def add(a, b): return a + b'
            }
        ]
        
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = "The add function returns the sum of two numbers"
            
            result = await llm_service.answer_query(
                'How does add work?',
                snippets
            )
            
            assert 'answer' in result
            assert 'sources' in result
            assert 'confidence' in result
            assert len(result['sources']) > 0
    
    @pytest.mark.asyncio
    async def test_explain_file_detailed(self, llm_service, sample_python_code):
        """Test detailed file explanation."""
        entities = [
            {'name': 'add', 'type': 'function', 'line': 1},
            {'name': 'multiply', 'type': 'function', 'line': 4},
            {'name': 'Calculator', 'type': 'class', 'line': 7}
        ]
        
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = "This file contains calculator utilities with basic arithmetic functions and a Calculator class"
            
            result = await llm_service.explain_file_detailed(
                'calculator.py',
                sample_python_code,
                entities,
                'python'
            )
            
            assert 'explanation' in result
            assert 'key_entities' in result
            assert 'complexity_score' in result
            assert len(result['key_entities']) > 0
    
    @pytest.mark.asyncio
    async def test_suggest_refactorings(self, llm_service):
        """Test refactoring suggestion generation."""
        code = """
        def process_data(data):
            if data is None:
                return None
            result = []
            for item in data:
                if isinstance(item, dict):
                    if 'key' in item:
                        result.append(item['key'])
            return result
        """
        
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = """
            {
                "suggestions": [
                    {
                        "title": "Reduce nesting",
                        "description": "Use list comprehension to reduce nesting levels",
                        "priority": "medium",
                        "line_range": [1, 10]
                    }
                ]
            }
            """
            
            result = await llm_service.suggest_refactorings(code, 'python')
            
            # Result can be empty list or contain suggestions
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_answer_query_without_snippets(self, llm_service):
        """Test query answering with no code snippets."""
        with patch.object(llm_service, '_call_llm') as mock_call:
            mock_call.return_value = "Unable to find relevant code snippets"
            
            result = await llm_service.answer_query(
                'How does the system work?',
                []  # Empty snippets
            )
            
            assert 'answer' in result
            assert 'sources' in result
            assert len(result['sources']) == 0
    
    def test_llm_service_configuration(self, llm_service, test_settings):
        """Test LLM service is properly configured."""
        assert llm_service.model == test_settings.OPENAI_MODEL
        # Client may be None if API key is missing
        if test_settings.OPENAI_API_KEY:
            assert llm_service.client is not None
    
    @pytest.mark.asyncio
    async def test_call_llm_error_handling(self, llm_service):
        """Test error handling in LLM calls."""
        with patch.object(llm_service, 'client') as mock_client:
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            with pytest.raises(Exception):
                await llm_service._call_llm(
                    "system prompt",
                    "user prompt"
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

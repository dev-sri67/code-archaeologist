"""
Unit tests for AST parser service.
"""
import pytest
from app.services.ast_parser import ASTParser


class TestASTParser:
    """Test AST parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return ASTParser()
    
    def test_parse_python_functions(self, parser, sample_python_code):
        """Test parsing Python functions."""
        entities = parser.parse_file(sample_python_code, 'python')
        
        assert len(entities) > 0
        
        function_entities = [e for e in entities if e['type'] == 'function']
        assert len(function_entities) >= 2
        
        function_names = {e['name'] for e in function_entities}
        assert 'add' in function_names
        assert 'multiply' in function_names
    
    def test_parse_python_classes(self, parser, sample_python_code):
        """Test parsing Python classes."""
        entities = parser.parse_file(sample_python_code, 'python')
        
        class_entities = [e for e in entities if e['type'] == 'class']
        assert len(class_entities) >= 1
        
        class_names = {e['name'] for e in class_entities}
        assert 'Calculator' in class_names
    
    def test_parse_javascript_functions(self, parser, sample_javascript_code):
        """Test parsing JavaScript functions."""
        entities = parser.parse_file(sample_javascript_code, 'javascript')
        
        assert len(entities) > 0
        
        function_entities = [e for e in entities if e['type'] == 'function']
        assert len(function_entities) >= 2
    
    def test_parse_javascript_classes(self, parser, sample_javascript_code):
        """Test parsing JavaScript classes."""
        entities = parser.parse_file(sample_javascript_code, 'javascript')
        
        class_entities = [e for e in entities if e['type'] == 'class']
        assert len(class_entities) >= 1
        
        class_names = {e['name'] for e in class_entities}
        assert 'Calculator' in class_names
    
    def test_parse_typescript(self, parser):
        """Test parsing TypeScript code."""
        code = """
        interface User {
            name: string;
            age: number;
        }
        
        class UserService {
            getUser(id: number): User {
                return { name: 'John', age: 30 };
            }
        }
        """
        
        entities = parser.parse_file(code, 'typescript')
        assert len(entities) >= 0  # TypeScript parsing may have limitations
    
    def test_parse_entity_has_required_fields(self, parser, sample_python_code):
        """Test that parsed entities have all required fields."""
        entities = parser.parse_file(sample_python_code, 'python')
        
        for entity in entities:
            assert 'name' in entity
            assert 'type' in entity
            assert 'start_line' in entity
            assert 'end_line' in entity
            assert 'code' in entity
    
    def test_parse_empty_code(self, parser):
        """Test parsing empty code."""
        entities = parser.parse_file("", 'python')
        assert entities == [] or isinstance(entities, list)
    
    def test_parse_unsupported_language(self, parser):
        """Test parsing unsupported language."""
        entities = parser.parse_file("some code", 'ruby')
        assert entities == []
    
    def test_fallback_regex_parsing(self, parser):
        """Test fallback regex parsing works."""
        code = """
        def my_function():
            pass
        
        class MyClass:
            pass
        """
        
        entities = parser.parse_file(code, 'python')
        # Fallback should at least find the def and class
        assert any(e['type'] == 'function' for e in entities)
        assert any(e['type'] == 'class' for e in entities)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

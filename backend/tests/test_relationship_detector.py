"""
Unit tests for relationship detection service.
"""
import pytest
from app.services.relationship_detector import RelationshipDetector


class TestRelationshipDetector:
    """Test relationship detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance (for sync tests, db is not used)."""
        # Sync tests use pure functions that don't need db
        return RelationshipDetector(None)  # type: ignore
    
    def test_extract_function_calls(self, detector):
        """Test extracting function calls from code."""
        code = """
        result = add(5, 3)
        total = multiply(result, 2)
        print(total)
        """
        
        calls = detector._extract_function_calls(code)
        
        assert 'add' in calls
        assert 'multiply' in calls
        assert 'print' in calls
    
    def test_extract_class_methods(self, detector):
        """Test extracting methods from class definition."""
        code = """
        class Calculator:
            def add(self, a, b):
                return a + b
            
            def multiply(self, a, b):
                return a * b
        """
        
        methods = detector._extract_class_methods(code)
        
        assert 'add' in methods
        assert 'multiply' in methods
    
    def test_extract_parent_classes_python(self, detector):
        """Test extracting parent classes from Python code."""
        code = """
        class Child(Parent):
            pass
        
        class GrandChild(Child, Mixin):
            pass
        """
        
        parents = detector._extract_parent_classes(code)
        
        assert 'Parent' in parents
        assert 'Child' in parents
        assert 'Mixin' in parents
    
    def test_extract_parent_classes_javascript(self, detector):
        """Test extracting parent classes from JavaScript code."""
        code = """
        class Child extends Parent {
        }
        
        class GrandChild extends Child {
        }
        """
        
        parents = detector._extract_parent_classes(code)
        
        assert 'Parent' in parents
        assert 'Child' in parents
    
    def test_extract_imports_python(self, detector):
        """Test extracting imports from Python code."""
        code = """
        from utils.helpers import add
        import math
        from collections import defaultdict
        """
        
        imports = detector._extract_imports(code)
        
        assert 'utils.helpers' in imports
        assert 'math' in imports
        assert 'collections' in imports
    
    def test_extract_imports_javascript(self, detector):
        """Test extracting imports from JavaScript code."""
        code = """
        import { add } from './utils.js';
        import React from 'react';
        const fs = require('fs');
        """
        
        imports = detector._extract_imports(code)
        
        assert './utils.js' in imports or 'utils.js' in imports
        assert 'react' in imports or 'React' in imports
        assert 'fs' in imports
    
    def test_is_import_match_python(self, detector):
        """Test import path matching for Python."""
        # Test cases
        assert detector._is_import_match('utils.helpers', 'utils/helpers.py')
        assert detector._is_import_match('models', 'models/__init__.py')
        assert not detector._is_import_match('utils', 'helpers/utils.py')
    
    def test_is_import_match_javascript(self, detector):
        """Test import path matching for JavaScript."""
        assert detector._is_import_match('./utils', 'utils/index.js')
        assert detector._is_import_match('utils', 'utils/helpers.js')
    
    def test_no_false_positives_in_calls(self, detector):
        """Test that keywords are excluded from function calls."""
        code = """
        if (x > 0):
            for item in items:
                while count < 10:
                    result = func()
        """
        
        calls = detector._extract_function_calls(code)
        
        # Should not include control flow keywords
        assert 'if' not in calls
        assert 'for' not in calls
        assert 'while' not in calls
        
        # Should include actual function call
        assert 'func' in calls
    
    def test_extract_imports_handles_edge_cases(self, detector):
        """Test import extraction with various formats."""
        code = """
        from . import sibling
        from .. import parent
        from ...root import module
        """
        
        imports = detector._extract_imports(code)
        
        # Relative imports should be detected
        assert len(imports) > 0
    
    @pytest.mark.asyncio
    async def test_get_call_graph_structure(self, test_db):
        """Test call graph generation structure."""
        # This test would require setting up entities first
        # Placeholder for async test
        detector = RelationshipDetector(test_db)
        # TODO: Implement with actual entities
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
AST Parser Service - Code structure extractor with fallback
"""
from typing import List, Dict, Any, Optional
import re

# Try tree-sitter, fallback to regex if unavailable
try:
    from tree_sitter_python import language as PYTHON_LANGUAGE
    from tree_sitter_javascript import language as JAVASCRIPT_LANGUAGE
    from tree_sitter import Parser, Language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class ASTParser:
    """Parse code and extract entities using Tree-sitter (or regex fallback)."""
    
    def __init__(self):
        self.parsers = {}
        self.tree_sitter_ok = False
        
        if TREE_SITTER_AVAILABLE:
            try:
                for lang_name, lang in [('python', PYTHON_LANGUAGE), ('javascript', JAVASCRIPT_LANGUAGE)]:
                    parser = Parser()
                    parser.set_language(Language(lang))
                    self.parsers[lang_name] = parser
                self.parsers['typescript'] = self.parsers['javascript']
                self.tree_sitter_ok = True
            except Exception as e:
                print(f"Tree-sitter init error: {e}")
    
    def parse_file(self, content: str, language: str) -> List[Dict[str, Any]]:
        if language not in ['python', 'javascript', 'typescript']:
            return []
        
        if self.tree_sitter_ok and language in self.parsers:
            try:
                tree = self.parsers[language].parse(bytes(content, "utf8"))
                if language == 'python':
                    return self._extract_python_entities(tree.root_node, content)
                return self._extract_js_entities(tree.root_node, content)
            except Exception as e:
                print(f"Tree-sitter parse error: {e}")
        
        # Fallback to regex
        return self._fallback_extract(content, language)
    
    def _extract_python_entities(self, node, content: str) -> List[Dict]:
        entities = []
        for child in node.children:
            if child.type == 'function_definition':
                name_node = child.child_by_field_name('name')
                if name_node:
                    entities.append({
                        'name': content[name_node.start_byte:name_node.end_byte],
                        'type': 'function',
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1,
                        'code': content[child.start_byte:child.end_byte],
                    })
            elif child.type == 'class_definition':
                name_node = child.child_by_field_name('name')
                if name_node:
                    entities.append({
                        'name': content[name_node.start_byte:name_node.end_byte],
                        'type': 'class',
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1,
                        'code': content[child.start_byte:child.end_byte],
                    })
        return entities
    
    def _extract_js_entities(self, node, content: str) -> List[Dict]:
        entities = []
        for child in node.children:
            if child.type in ['function_declaration', 'method_definition']:
                name_node = child.child_by_field_name('name')
                if name_node:
                    entities.append({
                        'name': content[name_node.start_byte:name_node.end_byte],
                        'type': 'function',
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1,
                        'code': content[child.start_byte:child.end_byte],
                    })
            elif child.type == 'class_declaration':
                name_node = child.child_by_field_name('name')
                if name_node:
                    entities.append({
                        'name': content[name_node.start_byte:name_node.end_byte],
                        'type': 'class',
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1,
                        'code': content[child.start_byte:child.end_byte],
                    })
        return entities
    
    def _fallback_extract(self, content: str, language: str) -> List[Dict]:
        entities = []
        lines = content.split('\n')
        
        if language == 'python':
            for i, line in enumerate(lines, 1):
                if func_match := re.match(r'^\s*def\s+(\w+)', line):
                    entities.append({
                        'name': func_match.group(1),
                        'type': 'function',
                        'start_line': i,
                        'end_line': i,
                        'code': line.strip(),
                    })
                elif class_match := re.match(r'^\s*class\s+(\w+)', line):
                    entities.append({
                        'name': class_match.group(1),
                        'type': 'class',
                        'start_line': i,
                        'end_line': i,
                        'code': line.strip(),
                    })
        else:  # javascript/typescript
            for i, line in enumerate(lines, 1):
                for pattern in [
                    r'(?:async\s+)?function\s+(\w+)',
                    r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(',
                ]:
                    if match := re.search(pattern, line):
                        entities.append({
                            'name': match.group(1),
                            'type': 'function',
                            'start_line': i,
                            'end_line': i,
                            'code': line.strip(),
                        })
                        break
                if class_match := re.match(r'^\s*class\s+(\w+)', line):
                    entities.append({
                        'name': class_match.group(1),
                        'type': 'class',
                        'start_line': i,
                        'end_line': i,
                        'code': line.strip(),
                    })
        
        return entities
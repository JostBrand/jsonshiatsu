"""
JSON Preprocessor - Handles common malformed JSON patterns.

This module provides preprocessing functions to clean and extract JSON from
various malformed formats commonly found in real-world data.
"""

import re
from typing import List, Optional, Tuple


class JSONPreprocessor:
    """Preprocessor for cleaning malformed JSON responses."""
    
    @staticmethod
    def extract_from_markdown(text: str) -> str:
        """
        Extract JSON from markdown code blocks.
        
        Handles:
        - ```json ... ```
        - ``` ... ```
        - `...` (inline)
        """
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        inline_pattern = r'`([^`]*[{[].*?[}\]][^`]*)`'
        match = re.search(inline_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return text
    
    @staticmethod
    def remove_trailing_text(text: str) -> str:
        """
        Remove explanatory text that appears after valid JSON.
        
        Handles cases where text is added after the JSON.
        """
        text = text.strip()
        
        # Find the last occurrence of } or ] that could end valid JSON
        json_end_chars = ['}', ']', '"', "'", 'e', 'l', 'E']  # null, true, false endings
        
        # Try to find complete JSON structures
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        last_valid_pos = -1
        
        for i, char in enumerate(text):
            if escaped:
                escaped = False
                continue
                
            if char == '\\' and in_string:
                escaped = True
                continue
            
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                
                # Check if we have a complete structure
                if brace_count == 0 and bracket_count == 0 and char in json_end_chars:
                    last_valid_pos = i
        
        if last_valid_pos > -1:
            return text[:last_valid_pos + 1]
        
        return text
    
    @staticmethod
    def remove_comments(text: str) -> str:
        """
        Remove JavaScript-style comments from JSON.
        
        Handles:
        - // line comments
        - /* block comments */
        """
        text = re.sub(r'//.*?(?=\n|$)', '', text, flags=re.MULTILINE)
        
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        
        return text
    
    @staticmethod
    def extract_first_json(text: str) -> str:
        """
        Extract the first complete JSON object/array from text with multiple JSONs.
        """
        text = text.strip()
        
        # Find the first JSON structure
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        start_pos = -1
        
        for i, char in enumerate(text):
            if escaped:
                escaped = False
                continue
                
            if char == '\\' and in_string:
                escaped = True
                continue
            
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char in ['{', '[']:
                    if start_pos == -1:
                        start_pos = i
                    if char == '{':
                        brace_count += 1
                    else:
                        bracket_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == ']':
                    bracket_count -= 1
                
                # Check if we have a complete structure
                if start_pos != -1 and brace_count == 0 and bracket_count == 0:
                    return text[start_pos:i + 1]
        
        return text
    
    @staticmethod
    def unwrap_function_calls(text: str) -> str:
        """
        Remove function call wrappers around JSON.
        
        Handles:
        - parse_json({"key": "value"})
        - return {"key": "value"}
        - const data = {"key": "value"}
        """
        text = text.strip()
        
        # Remove function calls like parse_json(...), JSON.parse(...), etc.
        func_pattern = r'^[a-zA-Z_][a-zA-Z0-9_.]*\s*\(\s*(.*)\s*\)\s*;?\s*$'
        match = re.match(func_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Remove return statements
        return_pattern = r'^return\s+(.*?)\s*;?\s*$'
        match = re.match(return_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Remove variable assignments
        var_pattern = r'^(?:const|let|var)\s+\w+\s*=\s*(.*?)\s*;?\s*$'
        match = re.match(var_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return text
    
    @staticmethod
    def normalize_quotes(text: str) -> str:
        """
        Normalize non-standard quotation marks to standard JSON quotes.
        
        This handles smart quotes, guillemets, and other quote-like characters
        that might appear in copy-pasted or internationalized content.
        """
        # Map of non-standard quotes to standard quotes
        quote_mapping = {
            # Smart double quotes
            '"': '"',  # U+201C Left double quotation mark
            '"': '"',  # U+201D Right double quotation mark
            '„': '"',  # U+201E Double low-9 quotation mark
            
            # Smart single quotes  
            ''': "'",  # U+2018 Left single quotation mark
            ''': "'",  # U+2019 Right single quotation mark
            '‚': "'",  # U+201A Single low-9 quotation mark
            
            # Guillemets (French quotes)
            '«': '"',  # U+00AB Left-pointing double angle quotation mark
            '»': '"',  # U+00BB Right-pointing double angle quotation mark
            '‹': "'",  # U+2039 Single left-pointing angle quotation mark
            '›': "'",  # U+203A Single right-pointing angle quotation mark
            
            # Other quote-like characters
            '`': "'",  # U+0060 Grave accent (sometimes used as quote)
            '´': "'",  # U+00B4 Acute accent (sometimes used as quote)
            
            # CJK quotes
            '「': '"',  # U+300C Left corner bracket
            '」': '"',  # U+300D Right corner bracket
            '『': '"',  # U+300E Left white corner bracket  
            '』': '"',  # U+300F Right white corner bracket
        }
        
        for non_standard, standard in quote_mapping.items():
            text = text.replace(non_standard, standard)
        
        return text
    
    @staticmethod
    def normalize_boolean_null(text: str) -> str:
        """
        Normalize non-standard boolean and null values.
        
        Converts:
        - True/False -> true/false
        - None -> null
        - yes/no -> true/false
        - undefined -> null
        """
        # Handle Python-style booleans and None
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)
        
        # Handle yes/no
        text = re.sub(r'\byes\b', 'true', text, flags=re.IGNORECASE)
        text = re.sub(r'\bno\b', 'false', text, flags=re.IGNORECASE)
        
        # Handle undefined
        text = re.sub(r'\bundefined\b', 'null', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        """
        Attempt to fix common string escaping issues.
        
        Uses intelligent detection to identify file paths and other strings
        where backslashes are likely meant to be literal rather than escape sequences.
        
        This avoids the problem where \f is a valid JSON escape (form feed)
        but users typically want literal \f in file paths.
        """
        def fix_file_paths(match):
            full_match = match.group(0)
            content = match.group(1)
            
            # Skip if no backslashes
            if '\\' not in content:
                return full_match
            
            # Detect if this looks like a file path or similar literal string
            file_indicators = [
                'data', 'file', 'temp', 'usr', 'var', 'home', 'program', 'windows',
                'documents', 'desktop', 'downloads', 'system', 'config', 'etc',
                'bin', 'lib', 'src', 'test', 'backup', 'log', 'cache', 'tmp'
            ]
            
            content_lower = content.lower()
            # If the string contains valid JSON escape sequences (Unicode or standard escapes),
            # be very conservative about treating it as a file path
            has_json_escapes = re.search(r'\\[\\"/bfnrtu]|\\u[0-9a-fA-F]{4}', content)
            
            if has_json_escapes:
                # Only treat as file path if it has strong file path indicators
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators) or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or after space/slash
                    re.search(r'(?:^|[\s/\\])[a-zA-Z]:', content)
                )
            else:
                # No JSON escapes - use broader file path detection
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators) or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or after space/slash
                    re.search(r'(?:^|[\s/\\])[a-zA-Z]:', content) or
                    # Contains actual path separators (not JSON escape sequences)
                    # Only consider it a path if there are backslashes that are NOT valid JSON escapes
                    (content.count('\\') >= 2 and 
                     re.search(r'\\(?![\\"/bfnrtu]|u[0-9a-fA-F]{4})', content)) or
                    # Contains common file extensions (but not Unicode escapes)
                    # Must be a backslash followed by path components and an extension
                    re.search(r'\\[^u\\]+\.[a-zA-Z0-9]{1,4}$', content) or
                    # Or a regular path with extension at the end
                    re.search(r'[a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,4}$', content.split('\\')[-1])
                )
            
            if looks_like_path:
                # Escape all single backslashes in suspected file paths
                escaped_content = content.replace('\\', '\\\\')
                return f'"{escaped_content}"'
            else:
                # For non-path strings, only escape invalid JSON escapes
                # This preserves intentional \n, \t, etc. and valid Unicode escapes
                escaped_content = re.sub(r'\\(?![\\"/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', content)
                return f'"{escaped_content}"'
        
        # Apply to all quoted strings
        text = re.sub(r'"([^"]*)"', fix_file_paths, text)
        
        return text
    
    @staticmethod
    def handle_incomplete_json(text: str) -> str:
        """
        Attempt to complete incomplete JSON structures by adding missing closing braces/brackets.
        
        This is a best-effort approach for handling truncated JSON.
        """
        text = text.strip()
        
        # Track opening/closing brackets and braces with positions to handle nesting correctly
        stack = []
        in_string = False
        string_char = None
        escaped = False
        
        for char in text:
            if escaped:
                escaped = False
                continue
                
            if char == '\\' and in_string:
                escaped = True
                continue
            
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char in ['{', '[']:
                    stack.append(char)
                elif char == '}':
                    if stack and stack[-1] == '{':
                        stack.pop()
                elif char == ']':
                    if stack and stack[-1] == '[':
                        stack.pop()
        
        # Close unclosed strings
        if in_string and string_char:
            text += string_char
        
        # Add missing closing brackets and braces in reverse order (LIFO)
        while stack:
            opener = stack.pop()
            if opener == '{':
                text += '}'
            elif opener == '[':
                text += ']'
        
        return text
    
    @staticmethod
    def handle_sparse_arrays(text: str) -> str:
        """
        Handle sparse arrays by converting double commas to null values.
        
        Converts:
        - [1,, 3] -> [1, null, 3]  (valid - arrays can have sparse elements)
        - {key1: val1,, key2: val2} -> {key1: val1, key2: val2}  (remove invalid syntax)
        
        Note: Only arrays support sparse elements. Objects with double commas are invalid.
        """
        import re
        
        # FIRST: Clean up invalid object sparse syntax BEFORE processing arrays
        # This prevents ,, in objects from being converted to null
        def clean_object_double_commas(text):
            """Remove double commas from object contexts only (invalid JSON)."""
            # Be very careful to only clean object contexts, not array contexts
            lines = text.split('\n')
            result_lines = []
            
            for line in lines:
                # Only clean lines that contain : (indicating object key-value pairs)
                # AND don't contain [ or ] (indicating array context)
                if ':' in line and '[' not in line and ']' not in line:
                    # Remove double commas in object context
                    cleaned = re.sub(r',\s*,+', ',', line)
                    result_lines.append(cleaned)
                else:
                    result_lines.append(line)
            
            return '\n'.join(result_lines)
        
        text = clean_object_double_commas(text)
        
        # SECOND: Process arrays to convert sparse elements to null
        def fix_sparse_in_array(match):
            """Fix sparse elements within an array."""
            content = match.group(1)
            
            # Only process if this looks like a real array (not object)
            # Skip if content has : which indicates object key-value pairs
            if ':' in content:
                return match.group(0)  # Return unchanged
            
            fixed_content = content
            
            # Handle leading commas: [, -> [null,
            fixed_content = re.sub(r'^(\s*),', r'\1null,', fixed_content)
            
            # Handle multiple consecutive commas: ,, -> , null,
            while ',,' in fixed_content:
                fixed_content = fixed_content.replace(',,', ', null,')
            
            # Handle trailing comma after comma: ,] -> , null] 
            # But be careful not to double-add if we already processed double commas
            if fixed_content.strip().endswith(',') and not fixed_content.strip().endswith('null,'):
                fixed_content = fixed_content.rstrip().rstrip(',') + ', null'
            
            return '[' + fixed_content + ']'
        
        # Match array patterns: [...] 
        array_pattern = r'\[([^\[\]]*?)\]'
        text = re.sub(array_pattern, fix_sparse_in_array, text)
        
        return text
    
    @classmethod
    def preprocess(cls, text: str, aggressive: bool = False, config=None) -> str:
        """
        Apply preprocessing steps to clean malformed JSON.
        
        Args:
            text: Raw text that may contain JSON
            aggressive: If True, apply aggressive cleaning (deprecated, use config)
            config: PreprocessingConfig object for granular control
        
        Returns:
            Cleaned JSON string
        """
        # Handle backward compatibility
        if config is None:
            from ..utils.config import PreprocessingConfig
            if aggressive:
                config = PreprocessingConfig.aggressive()
            else:
                config = PreprocessingConfig.aggressive()  # New default
        
        # Apply preprocessing steps based on config
        if config.extract_from_markdown:
            text = cls.extract_from_markdown(text)
        
        if config.remove_comments:
            text = cls.remove_comments(text)
        
        if config.unwrap_function_calls:
            text = cls.unwrap_function_calls(text)
        
        if config.extract_first_json:
            text = cls.extract_first_json(text)
        
        if config.remove_trailing_text:
            text = cls.remove_trailing_text(text)
        
        if config.normalize_quotes:
            text = cls.normalize_quotes(text)
        
        if config.normalize_boolean_null:
            text = cls.normalize_boolean_null(text)
        
        if config.fix_unescaped_strings:
            text = cls.fix_unescaped_strings(text)
        
        if config.handle_incomplete_json:
            text = cls.handle_incomplete_json(text)
        
        # Handle sparse arrays as final step
        if config.handle_sparse_arrays:
            text = cls.handle_sparse_arrays(text)
        
        return text.strip()
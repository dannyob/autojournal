"""Tests for orgmode export functionality"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime
from pathlib import Path
from autojournal.journal_manager import OrgmodeExporter
import sys


class TestOrgmodeExporter:
    """Test orgmode export functionality using LLM"""
    
    def test_init(self):
        """Test OrgmodeExporter initialization"""
        exporter = OrgmodeExporter("test_goals.md")
        assert exporter.goals_file == Path("test_goals.md")
        assert exporter.onebig_file == Path("/users/danny/private/nextcloud/org/wiki/onebig.org")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.cwd')
    def test_export_journal_to_orgmode_file_not_found(self, mock_cwd, mock_exists):
        """Test export when journal file doesn't exist"""
        mock_cwd.return_value = Path("/test/dir")
        mock_exists.return_value = False
        
        exporter = OrgmodeExporter()
        target_date = datetime(2025, 6, 2)
        
        with pytest.raises(FileNotFoundError, match="Journal file not found"):
            exporter.export_journal_to_orgmode(target_date)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.cwd')
    def test_export_journal_to_orgmode_calls_export_file(self, mock_cwd, mock_exists):
        """Test that export_journal_to_orgmode calls export_journal_file_to_orgmode"""
        mock_cwd.return_value = Path("/test/dir")
        mock_exists.return_value = True
        
        exporter = OrgmodeExporter()
        target_date = datetime(2025, 6, 2)
        
        with patch.object(exporter, 'export_journal_file_to_orgmode') as mock_export:
            mock_export.return_value = "mocked orgmode content"
            result = exporter.export_journal_to_orgmode(target_date)
        
        expected_path = "/test/dir/journal-2025-06-02.md"
        mock_export.assert_called_once_with(expected_path, target_date)
        assert result == "mocked orgmode content"
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_journal_file_to_orgmode_success(self, mock_file, mock_exists):
        """Test successful export using LLM"""
        mock_exists.return_value = True
        
        # Setup file reads
        mock_file.return_value.read.side_effect = [
            "# Goals content",
            "# Onebig content", 
            "# Journal content"
        ]
        
        # Create mock modules
        mock_llm = MagicMock()
        mock_config = MagicMock()
        
        # Setup config mocks
        mock_config.get_prompt.return_value = "Convert journal: {goals_content} {onebig_content} {journal_content} {date} {journal_date}"
        mock_config.get_model.return_value = "gpt-4o-mini"
        
        # Setup LLM mocks
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text.return_value = """Here's your orgmode export:

```orgmode
Generated orgmode content
```

Hope this helps!"""
        mock_model.prompt.return_value = mock_response
        mock_llm.get_model.return_value = mock_model
        
        # Temporarily add to sys.modules
        sys.modules['llm'] = mock_llm
        sys.modules['autojournal.config'] = MagicMock(config=mock_config)
        
        try:
            # Run the test
            exporter = OrgmodeExporter("goals.md")
            result = exporter.export_journal_file_to_orgmode("journal.md", datetime(2025, 6, 2))
            
            # Verify results
            assert result == "Generated orgmode content"
            mock_config.get_prompt.assert_called_once_with("orgmode_export")
            mock_config.get_model.assert_called_once_with("orgmode_export")
            mock_llm.get_model.assert_called_once_with("gpt-4o-mini")
            
            # Verify prompt was called with correct format
            expected_prompt = "Convert journal: # Goals content # Onebig content # Journal content 2025-06-02 Mon 2025-06-02"
            mock_model.prompt.assert_called_once_with(expected_prompt)
        finally:
            # Clean up sys.modules
            if 'llm' in sys.modules:
                del sys.modules['llm']
            if 'autojournal.config' in sys.modules:
                del sys.modules['autojournal.config']
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    def test_export_journal_file_with_missing_files(self, mock_open_builtin, mock_exists):
        """Test export when goals or onebig files are missing"""
        mock_exists.return_value = True
        
        # Setup file reading to simulate missing files
        def open_side_effect(path, *args, **kwargs):
            path_str = str(path)
            if "goals" in path_str:
                raise FileNotFoundError("Goals file not found")
            elif "onebig" in path_str:
                raise FileNotFoundError("Onebig file not found")
            else:
                return mock_open(read_data="# Journal content")()
        
        mock_open_builtin.side_effect = open_side_effect
        
        # Create mock modules
        mock_llm = MagicMock()
        mock_config = MagicMock()
        
        mock_config.get_prompt.return_value = "{goals_content} {onebig_content} {journal_content}"
        mock_config.get_model.return_value = "gpt-4o-mini"
        
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text.return_value = """Processing complete:

```
Generated with errors
```"""
        mock_model.prompt.return_value = mock_response
        mock_llm.get_model.return_value = mock_model
        
        # Temporarily add to sys.modules
        sys.modules['llm'] = mock_llm
        sys.modules['autojournal.config'] = MagicMock(config=mock_config)
        
        try:
            exporter = OrgmodeExporter("goals.md")
            result = exporter.export_journal_file_to_orgmode("journal.md", datetime(2025, 6, 2))
            
            # Should still work but with error messages in content
            assert result == "Generated with errors"
            # Verify error messages were included in prompt
            prompt_call = mock_model.prompt.call_args[0][0]
            assert "Error reading goals file" in prompt_call
            assert "Error reading onebig file" in prompt_call
        finally:
            # Clean up sys.modules
            if 'llm' in sys.modules:
                del sys.modules['llm']
            if 'autojournal.config' in sys.modules:
                del sys.modules['autojournal.config']
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_journal_file_fallback_model(self, mock_file, mock_exists):
        """Test fallback to alternative model when primary fails"""
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = ["# Goals", "# Onebig", "# Journal"]
        
        # Create mock modules
        mock_llm = MagicMock()
        mock_config = MagicMock()
        
        mock_config.get_prompt.return_value = "{goals_content}"
        mock_config.get_model.side_effect = ["bad-model", "gpt-3.5-turbo"]  # First returns bad model, then fallback
        
        # First model fails, second succeeds
        def get_model_side_effect(model_name):
            if model_name == "bad-model":
                raise Exception("Model not found")
            else:
                mock_model = Mock()
                mock_response = Mock()
                mock_response.text.return_value = """Here's the fallback result:

```
Fallback generated content
```"""
                mock_model.prompt.return_value = mock_response
                return mock_model
        
        mock_llm.get_model.side_effect = get_model_side_effect
        
        # Temporarily add to sys.modules
        sys.modules['llm'] = mock_llm
        sys.modules['autojournal.config'] = MagicMock(config=mock_config)
        
        try:
            exporter = OrgmodeExporter("goals.md")
            result = exporter.export_journal_file_to_orgmode("journal.md", datetime(2025, 6, 2))
            
            assert result == "Fallback generated content"
            # Verify fallback model was used
            assert mock_llm.get_model.call_count == 2
            mock_llm.get_model.assert_any_call("bad-model")
            mock_llm.get_model.assert_any_call("gpt-3.5-turbo")
        finally:
            # Clean up sys.modules
            if 'llm' in sys.modules:
                del sys.modules['llm']
            if 'autojournal.config' in sys.modules:
                del sys.modules['autojournal.config']
    
    def test_export_journal_file_not_found(self):
        """Test export when journal file doesn't exist"""
        exporter = OrgmodeExporter()
        
        with pytest.raises(FileNotFoundError, match="Journal file not found"):
            exporter.export_journal_file_to_orgmode("nonexistent.md", datetime(2025, 6, 2))
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_journal_without_llm_library(self, mock_file, mock_exists):
        """Test error when llm library is not available"""
        mock_exists.return_value = True
        
        # Mock the import to fail
        def mock_import(name, *args, **kwargs):
            if name == 'llm':
                raise ImportError("No module named 'llm'")
            return original_import(name, *args, **kwargs)
        
        original_import = __builtins__['__import__']
        
        try:
            __builtins__['__import__'] = mock_import
            
            exporter = OrgmodeExporter()
            
            with pytest.raises(ImportError, match="llm library not installed"):
                exporter.export_journal_file_to_orgmode("journal.md", datetime(2025, 6, 2))
        finally:
            # Restore original import
            __builtins__['__import__'] = original_import
    
    def test_extract_code_blocks_with_code_fence(self):
        """Test extracting content between markdown code fences"""
        exporter = OrgmodeExporter()
        
        text_with_code = """Here's some explanation text.

```orgmode
* TODO Task 1
CLOCK: [2025-06-02 Sun 14:00]--[2025-06-02 Sun 15:00] =>  1:00
* DONE Task 2
```

And some more explanation after.
"""
        
        result = exporter._extract_code_blocks(text_with_code)
        expected = """* TODO Task 1
CLOCK: [2025-06-02 Sun 14:00]--[2025-06-02 Sun 15:00] =>  1:00
* DONE Task 2"""
        
        assert result == expected
    
    def test_extract_code_blocks_with_language_specified(self):
        """Test extracting code blocks when language is specified"""
        exporter = OrgmodeExporter()
        
        text_with_code = """Here's the result:

```org
* Meeting Notes
** Action Items
```

Done!"""
        
        result = exporter._extract_code_blocks(text_with_code)
        expected = """* Meeting Notes
** Action Items"""
        
        assert result == expected
    
    def test_extract_code_blocks_no_code_fence(self):
        """Test that full text is returned when no code fences are found"""
        exporter = OrgmodeExporter()
        
        text_without_code = """This is just regular text
with no code blocks at all.

It should be returned as-is."""
        
        result = exporter._extract_code_blocks(text_without_code)
        assert result == text_without_code
    
    def test_extract_code_blocks_multiple_fences_returns_first(self):
        """Test that only the first code block is returned when multiple exist"""
        exporter = OrgmodeExporter()
        
        text_with_multiple = """Here's the first block:

```
First code block
with multiple lines
```

And here's another:

```python
print("second block")
```"""
        
        result = exporter._extract_code_blocks(text_with_multiple)
        expected = """First code block
with multiple lines"""
        
        assert result == expected
    
    def test_extract_code_blocks_empty_code_fence(self):
        """Test extracting empty code blocks"""
        exporter = OrgmodeExporter()
        
        text_with_empty = """Empty code block:

```

```

Nothing there."""
        
        result = exporter._extract_code_blocks(text_with_empty)
        assert result == ""
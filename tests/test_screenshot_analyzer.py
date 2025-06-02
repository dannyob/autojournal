"""Tests for ScreenshotAnalyzer"""

import pytest
from unittest.mock import patch, AsyncMock
from autojournal.screenshot_analyzer import ScreenshotAnalyzer
from autojournal.models import Task, ActivityAnalysis


class TestScreenshotAnalyzer:
    def setup_method(self):
        self.analyzer = ScreenshotAnalyzer()
    
    def test_simple_app_analysis_productivity_apps(self):
        productivity_apps = [
            "VSCode", "Visual Studio Code", "vim", "emacs", "Terminal",
            "iTerm2", "PyCharm", "IntelliJ IDEA", "Sublime Text"
        ]
        
        for app in productivity_apps:
            assert self.analyzer._simple_app_analysis(app) is True
    
    def test_simple_app_analysis_distraction_apps(self):
        distraction_apps = [
            "Facebook", "Twitter", "Instagram", "YouTube", "Netflix",
            "TikTok", "Discord", "Spotify", "Steam", "Games"
        ]
        
        for app in distraction_apps:
            assert self.analyzer._simple_app_analysis(app) is False
    
    def test_simple_app_analysis_unknown_apps(self):
        # Unknown apps should default to on-task
        unknown_apps = ["Unknown App", "Custom Software", "Proprietary Tool"]
        
        for app in unknown_apps:
            assert self.analyzer._simple_app_analysis(app) is True
    
    def test_simple_app_analysis_case_insensitive(self):
        assert self.analyzer._simple_app_analysis("FACEBOOK") is False
        assert self.analyzer._simple_app_analysis("vscode") is True
        assert self.analyzer._simple_app_analysis("Visual Studio CODE") is True
    
    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_get_active_application_macos(self, mock_subprocess):
        with patch('platform.system', return_value='Darwin'):
            # Mock subprocess
            mock_process = AsyncMock()
            mock_process.communicate.return_value = ("Visual Studio Code\n", "")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            app = await self.analyzer._get_active_application()
            assert app == "Visual Studio Code"
    
    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_get_active_application_error(self, mock_subprocess):
        mock_subprocess.side_effect = Exception("Command failed")
        
        app = await self.analyzer._get_active_application()
        assert app == "Unknown"
    
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._run_llm_analysis')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._take_screenshot')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._get_active_application')
    @pytest.mark.asyncio
    async def test_analyze_current_activity(self, mock_get_app, mock_screenshot, mock_llm):
        # Setup mocks
        mock_screenshot.return_value = None  # No screenshot for test
        mock_get_app.return_value = "VSCode"
        
        # Mock LLM response
        mock_llm.return_value = {
            "description": "Writing Python code",
            "is_on_task": True,
            "progress_estimate": 75,
            "confidence": 0.9
        }
        
        task = Task("Write unit tests", 30)
        
        analysis = await self.analyzer.analyze_current_activity(task, [])
        
        assert isinstance(analysis, ActivityAnalysis)
        assert analysis.description == "Writing Python code"
        assert analysis.current_app == "VSCode"
        assert analysis.is_on_task is True
        assert analysis.progress_estimate == 75
        assert analysis.confidence == 0.9
    
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._run_llm_analysis')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._take_screenshot')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._get_active_application')
    @pytest.mark.asyncio
    async def test_analyze_current_activity_fallback(self, mock_get_app, mock_screenshot, mock_llm):
        # Setup mocks
        mock_screenshot.return_value = None
        mock_get_app.return_value = "Terminal"
        
        # Mock LLM failure
        mock_llm.side_effect = Exception("LLM failed")
        
        task = Task("Debug application", 45)
        
        analysis = await self.analyzer.analyze_current_activity(task, [])
        
        assert isinstance(analysis, ActivityAnalysis)
        assert analysis.current_app == "Terminal"
        assert analysis.is_on_task is True  # Terminal is productive
        assert analysis.confidence == 0.5
    
    @patch('platform.system')
    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_take_screenshot_macos(self, mock_subprocess, mock_system):
        mock_system.return_value = "Darwin"
        
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        result = await self.analyzer._take_screenshot()
        
        # Should have called screencapture
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert "screencapture" in args
        assert "-x" in args
        assert "-t" in args
        assert "png" in args
    
    @patch('platform.system')
    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_take_screenshot_error(self, mock_subprocess, mock_system):
        mock_system.return_value = "Darwin"
        mock_subprocess.side_effect = Exception("Screenshot failed")
        
        result = await self.analyzer._take_screenshot()
        
        assert result is None
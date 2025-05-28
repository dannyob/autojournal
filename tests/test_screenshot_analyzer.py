"""Tests for ScreenshotAnalyzer"""

import pytest
from unittest.mock import patch, MagicMock
import platform
from datetime import datetime
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
    
    @patch('subprocess.run')
    def test_get_active_application_macos(self, mock_run):
        with patch('platform.system', return_value='Darwin'):
            mock_run.return_value.stdout = "Visual Studio Code\n"
            mock_run.return_value.returncode = 0
            
            app = self.analyzer._get_active_application()
            assert app == "Visual Studio Code"
    
    @patch('subprocess.run')
    def test_get_active_application_error(self, mock_run):
        mock_run.side_effect = Exception("Command failed")
        
        app = self.analyzer._get_active_application()
        assert app == "Unknown"
    
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._take_screenshot')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._get_active_application')
    @patch('subprocess.run')
    @pytest.mark.asyncio
    async def test_analyze_current_activity(self, mock_run, mock_get_app, mock_screenshot):
        # Setup mocks
        mock_screenshot.return_value = None  # No screenshot for test
        mock_get_app.return_value = "VSCode"
        
        # Mock LLM response
        mock_run.return_value.stdout = """{
            "description": "Writing Python code",
            "is_on_task": true,
            "progress_estimate": 75,
            "confidence": 0.9
        }"""
        mock_run.return_value.returncode = 0
        
        task = Task("Write unit tests", 30)
        
        analysis = await self.analyzer.analyze_current_activity(task, [])
        
        assert isinstance(analysis, ActivityAnalysis)
        assert analysis.description == "Writing Python code"
        assert analysis.current_app == "VSCode"
        assert analysis.is_on_task is True
        assert analysis.progress_estimate == 75
        assert analysis.confidence == 0.9
    
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._take_screenshot')
    @patch('autojournal.screenshot_analyzer.ScreenshotAnalyzer._get_active_application')
    @patch('subprocess.run')
    @pytest.mark.asyncio
    async def test_analyze_current_activity_fallback(self, mock_run, mock_get_app, mock_screenshot):
        # Setup mocks
        mock_screenshot.return_value = None
        mock_get_app.return_value = "Terminal"
        
        # Mock LLM failure
        mock_run.side_effect = Exception("LLM failed")
        
        task = Task("Debug application", 45)
        
        analysis = await self.analyzer.analyze_current_activity(task, [])
        
        assert isinstance(analysis, ActivityAnalysis)
        assert analysis.current_app == "Terminal"
        assert analysis.is_on_task is True  # Terminal is productive
        assert analysis.confidence == 0.5
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_take_screenshot_macos(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        mock_run.return_value.returncode = 0
        
        result = self.analyzer._take_screenshot()
        
        # Should have called screencapture
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "screencapture" in args
        assert "-x" in args
        assert "-t" in args
        assert "png" in args
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_take_screenshot_error(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        mock_run.side_effect = Exception("Screenshot failed")
        
        result = self.analyzer._take_screenshot()
        
        assert result is None
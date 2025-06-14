"""Screenshot capture and AI analysis"""

import asyncio
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import platform

try:
    import llm
except ImportError:
    llm = None

from .models import Task, ActivityAnalysis, JournalEntry
from .config import get_model, get_prompt


class ScreenshotAnalyzer:
    """Captures screenshots and analyzes current activity using AI"""
    
    def __init__(self):
        self.screenshot_dir = Path.home() / ".autojournal" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def _take_screenshot(self) -> Optional[Path]:
        """Take a screenshot and return the file path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.screenshot_dir / f"screenshot_{timestamp}.png"
        
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                process = await asyncio.create_subprocess_exec(
                    "screencapture", "-x", "-t", "png", str(screenshot_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, "screencapture")
            elif system == "Linux":
                process = await asyncio.create_subprocess_exec(
                    "gnome-screenshot", "-f", str(screenshot_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, "gnome-screenshot")
            elif system == "Windows":
                # Use PowerShell for Windows
                ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$Screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($Screen.Left, $Screen.Top, 0, 0, $bitmap.Size)
$bitmap.Save('{screenshot_path}')
"""
                process = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", ps_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, "powershell")
            else:
                print(f"Unsupported platform: {system}")
                return None
                
            return screenshot_path
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to take screenshot: {e}")
            return None
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    async def _get_active_application(self) -> str:
        """Get the name of the currently active application"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                script = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                end tell
                return frontApp
                '''
                process = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    text=True
                )
                stdout, _ = await process.communicate()
                if process.returncode == 0:
                    return stdout.strip()
                else:
                    return "Unknown"
                
            elif system == "Linux":
                # Try different methods for Linux
                try:
                    process = await asyncio.create_subprocess_exec(
                        "xdotool", "getactivewindow", "getwindowname",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        text=True
                    )
                    stdout, _ = await process.communicate()
                    if process.returncode == 0:
                        return stdout.strip()
                except:
                    try:
                        process = await asyncio.create_subprocess_shell(
                            "xprop -id $(xprop -root _NET_ACTIVE_WINDOW | cut -d' ' -f5) WM_CLASS",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            text=True
                        )
                        stdout, _ = await process.communicate()
                        if process.returncode == 0:
                            return stdout.strip()
                    except:
                        pass
                return "Unknown"
                        
            elif system == "Windows":
                ps_script = '''
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                using System.Text;
                public class Win32 {
                    [DllImport("user32.dll")]
                    public static extern IntPtr GetForegroundWindow();
                    [DllImport("user32.dll")]
                    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
                }
"@
                $hwnd = [Win32]::GetForegroundWindow()
                $text = New-Object System.Text.StringBuilder(256)
                [Win32]::GetWindowText($hwnd, $text, $text.Capacity)
                $text.ToString()
                '''
                process = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", ps_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    text=True
                )
                stdout, _ = await process.communicate()
                if process.returncode == 0:
                    return stdout.strip()
                else:
                    return "Unknown"
            
        except Exception as e:
            print(f"Error getting active application: {e}")
            
        return "Unknown"
    
    async def analyze_current_activity(self, current_task: Optional[Task], 
                                     recent_entries: List[JournalEntry]) -> ActivityAnalysis:
        """Analyze current screen activity and determine if user is on-task"""
        
        # Take screenshot and get active app concurrently
        screenshot_task = asyncio.create_task(self._take_screenshot())
        active_app_task = asyncio.create_task(self._get_active_application())
        
        screenshot_path, active_app = await asyncio.gather(
            screenshot_task, active_app_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(screenshot_path, Exception):
            print(f"Screenshot failed: {screenshot_path}")
            screenshot_path = None
        if isinstance(active_app, Exception):
            print(f"Active app detection failed: {active_app}")
            active_app = "Unknown"
        
        # Prepare context for AI analysis
        task_context = ""
        if current_task:
            task_context = f"Current task: {current_task.description} (estimated {current_task.estimated_time_minutes} minutes)"
        
        recent_context = ""
        if recent_entries:
            recent_context = "Recent activity:\n"
            for entry in recent_entries[-3:]:  # Last 3 entries
                recent_context += f"- {entry.content}\n"
        
        # Get prompt from configuration based on whether we have a screenshot
        if screenshot_path and screenshot_path.exists():
            prompt_template = get_prompt("activity_analysis_vision")
        else:
            prompt_template = get_prompt("activity_analysis_text")
        
        # Format the prompt with context variables
        prompt = prompt_template.format(
            task_context=task_context,
            active_app=active_app,
            recent_context=recent_context
        )
        
        try:
            # Run LLM analysis in a thread to avoid blocking
            analysis_data = await asyncio.to_thread(self._run_llm_analysis, prompt, screenshot_path)
            
            return ActivityAnalysis(
                timestamp=datetime.now(),
                description=analysis_data['description'],
                current_app=active_app,
                is_on_task=analysis_data['is_on_task'],
                progress_estimate=analysis_data['progress_estimate'],
                confidence=analysis_data['confidence']
            )
            
        except Exception as e:
            print(f"Error analyzing activity: {e}")
            # Fallback analysis
            is_on_task = self._simple_app_analysis(active_app)
            return ActivityAnalysis(
                timestamp=datetime.now(),
                description=f"Using {active_app}",
                current_app=active_app,
                is_on_task=is_on_task,
                progress_estimate=0,
                confidence=0.5
            )
    
    def _simple_app_analysis(self, app_name: str) -> bool:
        """Simple heuristic to determine if app suggests on-task behavior"""
        app_lower = app_name.lower()
        
        # Common productivity apps
        productivity_apps = [
            'vscode', 'code', 'vim', 'emacs', 'sublime', 'atom', 'intellij',
            'pycharm', 'webstorm', 'terminal', 'iterm', 'cmd', 'powershell',
            'bash', 'finder', 'explorer', 'notes', 'notion', 'obsidian',
            'docs', 'word', 'excel', 'sheets', 'calendar'
        ]
        
        # Common distraction apps
        distraction_apps = [
            'facebook', 'twitter', 'instagram', 'tiktok', 'youtube',
            'netflix', 'spotify', 'discord', 'slack', 'whatsapp',
            'messages', 'mail', 'gmail', 'games', 'steam'
        ]
        
        for prod_app in productivity_apps:
            if prod_app in app_lower:
                return True
                
        for dist_app in distraction_apps:
            if dist_app in app_lower:
                return False
        
        # Default to on-task for unknown apps
        return True
    
    def _run_llm_analysis(self, prompt: str, screenshot_path: Optional[Path]) -> dict:
        """Run LLM analysis synchronously in a thread"""
        if llm is None:
            raise ImportError("llm library not available")
        
        model_name = get_model("activity_analysis")
        model = llm.get_model(model_name)
        
        # Check if we have a screenshot and if the model supports vision
        if screenshot_path and screenshot_path.exists():
            # Try to use vision model with screenshot
            try:
                # Create attachment with explicit MIME type
                attachment = llm.Attachment(type="image/png", path=str(screenshot_path))
                response = model.prompt(prompt, attachments=[attachment])
                response_text = response.text()
            except Exception as vision_error:
                print(f"Vision analysis failed: {vision_error}")
                # Fall back to text-only analysis
                response = model.prompt(prompt)
                response_text = response.text()
        else:
            # No screenshot available, use text-only analysis
            response = model.prompt(prompt)
            response_text = response.text()
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
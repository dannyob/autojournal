"""Cross-platform notification system for AutoJournal"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional
from enum import Enum

try:
    import plyer
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


class NotificationType(Enum):
    """Types of notifications"""
    OFF_TASK = "off_task"
    BREAK_REMINDER = "break_reminder"
    TASK_COMPLETE = "task_complete"
    SESSION_END = "session_end"


class NotificationManager:
    """Cross-platform notification manager for AutoJournal"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.system = platform.system()
        self.app_name = "AutoJournal"
        
        # Test notification capability on initialization
        self.notification_method = self._detect_notification_method()
    
    def _detect_notification_method(self) -> str:
        """Detect the best available notification method"""
        if not self.enabled:
            return "disabled"
        
        # Try plyer first (most cross-platform)
        if PLYER_AVAILABLE:
            try:
                # Check if plyer can import its notification module without actually sending
                # This avoids the pyobjus dependency issue on macOS
                from plyer import notification
                # Only use plyer if we're not on macOS (where osascript works better)
                if self.system != "Darwin":
                    # Test plyer with a dummy notification
                    plyer.notification.notify(
                        title="AutoJournal Test",
                        message="Testing notification system...",
                        timeout=1,
                        app_name=self.app_name
                    )
                    return "plyer"
            except Exception:
                pass
        
        # Platform-specific fallbacks
        if self.system == "Darwin":  # macOS
            if self._command_exists("osascript"):
                return "osascript"
        elif self.system == "Linux":
            if self._command_exists("notify-send"):
                return "notify-send"
            elif self._command_exists("zenity"):
                return "zenity"
        elif self.system == "Windows":
            if self._command_exists("powershell"):
                return "powershell"
        
        return "fallback"
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system"""
        try:
            subprocess.run([command], capture_output=True, check=False)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def notify(self, 
               title: str, 
               message: str, 
               notification_type: NotificationType = NotificationType.OFF_TASK,
               timeout: int = 5) -> bool:
        """Send a notification using the best available method"""
        
        if not self.enabled or self.notification_method == "disabled":
            return False
        
        # Get icon and urgency based on notification type
        icon, urgency = self._get_notification_style(notification_type)
        
        try:
            if self.notification_method == "plyer":
                return self._notify_plyer(title, message, timeout, icon)
            elif self.notification_method == "osascript":
                return self._notify_osascript(title, message)
            elif self.notification_method == "notify-send":
                return self._notify_linux(title, message, urgency, icon, timeout)
            elif self.notification_method == "zenity":
                return self._notify_zenity(title, message)
            elif self.notification_method == "powershell":
                return self._notify_windows(title, message)
            else:
                return self._notify_fallback(title, message)
        except Exception as e:
            print(f"Notification failed: {e}")
            return False
    
    def _get_notification_style(self, notification_type: NotificationType) -> tuple[str, str]:
        """Get icon and urgency level for notification type"""
        styles = {
            NotificationType.OFF_TASK: ("dialog-warning", "normal"),
            NotificationType.BREAK_REMINDER: ("dialog-information", "low"),
            NotificationType.TASK_COMPLETE: ("dialog-information", "low"),
            NotificationType.SESSION_END: ("dialog-information", "low")
        }
        return styles.get(notification_type, ("dialog-information", "normal"))
    
    def _notify_plyer(self, title: str, message: str, timeout: int, icon: str) -> bool:
        """Send notification using plyer library"""
        plyer.notification.notify(
            title=title,
            message=message,
            timeout=timeout,
            app_name=self.app_name,
            app_icon=icon
        )
        return True
    
    def _notify_osascript(self, title: str, message: str) -> bool:
        """Send notification using macOS osascript"""
        # For off-task notifications, use a brief alert that auto-dismisses
        # This ensures the user sees it even if notifications are disabled
        dialog_script = f'''
        display alert "{title}" message "{message}" as warning giving up after 3
        '''
        try:
            subprocess.run(["osascript", "-e", dialog_script], check=True)
            return True
        except Exception:
            # Fallback to simple dialog
            try:
                simple_script = f'''
                display dialog "{title}\\n{message}" buttons {{"Dismiss"}} default button "Dismiss" giving up after 3
                '''
                subprocess.run(["osascript", "-e", simple_script], check=True)
                return True
            except Exception:
                return False
    
    def _notify_linux(self, title: str, message: str, urgency: str, icon: str, timeout: int) -> bool:
        """Send notification using Linux notify-send"""
        cmd = [
            "notify-send",
            "--app-name", self.app_name,
            "--urgency", urgency,
            "--expire-time", str(timeout * 1000),  # notify-send uses milliseconds
            "--icon", icon,
            title,
            message
        ]
        subprocess.run(cmd, check=True)
        return True
    
    def _notify_zenity(self, title: str, message: str) -> bool:
        """Send notification using zenity (Linux fallback)"""
        cmd = ["zenity", "--notification", "--text", f"{title}: {message}"]
        subprocess.run(cmd, check=True)
        return True
    
    def _notify_windows(self, title: str, message: str) -> bool:
        """Send notification using Windows PowerShell"""
        ps_script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.BalloonTipTitle = "{title}"
        $notify.BalloonTipText = "{message}"
        $notify.BalloonTipIcon = "Info"
        $notify.Visible = $true
        $notify.ShowBalloonTip(5000)
        Start-Sleep -Seconds 1
        $notify.Visible = $false
        '''
        subprocess.run(["powershell", "-Command", ps_script], check=True)
        return True
    
    def _notify_fallback(self, title: str, message: str) -> bool:
        """Fallback notification method (terminal output)"""
        print(f"\n🔔 {self.app_name} Notification:")
        print(f"📌 {title}")
        print(f"💬 {message}")
        print("-" * 50)
        return True
    
    def notify_off_task(self, current_activity: str, expected_task: str) -> bool:
        """Send off-task notification"""
        title = "⚠️ Off-Task Detected"
        message = f"Currently: {current_activity}\nExpected: {expected_task}"
        return self.notify(title, message, NotificationType.OFF_TASK)
    
    def notify_break_reminder(self, work_duration: int) -> bool:
        """Send break reminder notification"""
        title = "🕐 Break Time"
        message = f"You've been working for {work_duration} minutes. Consider taking a break!"
        return self.notify(title, message, NotificationType.BREAK_REMINDER)
    
    def notify_task_complete(self, task_name: str) -> bool:
        """Send task completion notification"""
        title = "✅ Task Complete"
        message = f"Great work! You've completed: {task_name}"
        return self.notify(title, message, NotificationType.TASK_COMPLETE)
    
    def notify_session_end(self, duration: str, productivity_score: int) -> bool:
        """Send session end notification"""
        title = "🏁 Session Complete"
        message = f"Session duration: {duration}\nProductivity score: {productivity_score}/10"
        return self.notify(title, message, NotificationType.SESSION_END)
    
    def test_notifications(self) -> None:
        """Test all notification types"""
        print(f"Testing notifications using method: {self.notification_method}")
        
        tests = [
            ("Off-task test", "You're browsing social media instead of working", NotificationType.OFF_TASK),
            ("Break reminder test", "Time for a 5-minute break!", NotificationType.BREAK_REMINDER),
            ("Task complete test", "You finished the quarterly report", NotificationType.TASK_COMPLETE),
            ("Session end test", "Today's productivity session is complete", NotificationType.SESSION_END)
        ]
        
        for title, message, ntype in tests:
            print(f"Sending {ntype.value} notification...")
            success = self.notify(title, message, ntype)
            print(f"Result: {'✅ Success' if success else '❌ Failed'}")
            
            # Small delay between notifications
            import time
            time.sleep(2)


def install_notification_dependencies() -> None:
    """Install optional notification dependencies"""
    print("Installing notification dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "plyer"], check=True)
        print("✅ Installed plyer for cross-platform notifications")
    except subprocess.CalledProcessError:
        print("❌ Failed to install plyer")
        print("You can still use system-native notifications")


if __name__ == "__main__":
    # Test the notification system
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AutoJournal notification system")
    parser.add_argument("--install", action="store_true", help="Install notification dependencies")
    parser.add_argument("--test", action="store_true", help="Test all notification types")
    parser.add_argument("--method", help="Show detected notification method")
    
    args = parser.parse_args()
    
    if args.install:
        install_notification_dependencies()
    elif args.test:
        notifier = NotificationManager()
        notifier.test_notifications()
    elif args.method:
        notifier = NotificationManager()
        print(f"Detected notification method: {notifier.notification_method}")
    else:
        parser.print_help()
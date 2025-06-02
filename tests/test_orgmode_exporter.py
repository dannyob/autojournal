"""Tests for orgmode export functionality"""

from datetime import datetime, time
from autojournal.journal_manager import OrgmodeExporter


class TestOrgmodeExporter:
    """Test orgmode export functionality"""
    
    def test_parse_entry_content_task_start(self):
        """Test parsing task start entries"""
        exporter = OrgmodeExporter()
        timestamp = time(9, 30, 0)
        content = "🎯 Started task: Review code changes (estimated 30 min)"
        
        entry = exporter._parse_entry_content(timestamp, content)
        
        assert entry['type'] == 'task_start'
        assert entry['task_description'] == 'Review code changes'
        assert entry['timestamp'] == timestamp
    
    def test_parse_entry_content_activity_on_task(self):
        """Test parsing on-task activity entries"""
        exporter = OrgmodeExporter()
        timestamp = time(9, 35, 0)
        content = "✅ Reviewing pull request files | App: VS Code | Progress: 25% (85% confidence)"
        
        entry = exporter._parse_entry_content(timestamp, content)
        
        assert entry['type'] == 'activity'
        assert entry['is_on_task'] is True
        assert entry['app'] == 'VS Code'
        assert entry['progress'] == 25
    
    def test_parse_entry_content_activity_off_task(self):
        """Test parsing off-task activity entries"""
        exporter = OrgmodeExporter()
        timestamp = time(9, 40, 0)
        content = "⚠️ Browsing social media | App: Firefox | Progress: 25% (90% confidence)"
        
        entry = exporter._parse_entry_content(timestamp, content)
        
        assert entry['type'] == 'activity'
        assert entry['is_on_task'] is False
        assert entry['app'] == 'Firefox'
        assert entry['progress'] == 25
    
    def test_parse_entry_content_task_complete(self):
        """Test parsing task completion entries"""
        exporter = OrgmodeExporter()
        timestamp = time(10, 0, 0)
        content = "✅ Completed task: Review code changes"
        
        entry = exporter._parse_entry_content(timestamp, content)
        
        assert entry['type'] == 'task_complete'
        assert entry['task_description'] == 'Review code changes'
    
    def test_analyze_work_patterns_single_task(self):
        """Test analyzing work patterns for a single task"""
        exporter = OrgmodeExporter()
        
        entries = [
            {
                'type': 'task_start',
                'timestamp': time(9, 0, 0),
                'task_description': 'Write tests'
            },
            {
                'type': 'activity',
                'timestamp': time(9, 5, 0),
                'is_on_task': True,
                'app': 'VS Code',
                'content': 'Writing test code'
            },
            {
                'type': 'activity',
                'timestamp': time(9, 10, 0),
                'is_on_task': False,
                'app': 'Slack',
                'content': 'Checking messages'
            },
            {
                'type': 'task_complete',
                'timestamp': time(9, 30, 0),
                'task_description': 'Write tests'
            }
        ]
        
        work_chunks, distractions = exporter._analyze_work_patterns(entries)
        
        assert len(work_chunks) == 1
        assert work_chunks[0]['task'] == 'Write tests'
        assert work_chunks[0]['start_time'] == time(9, 0, 0)
        assert work_chunks[0]['end_time'] == time(9, 30, 0)
        assert len(work_chunks[0]['focused_periods']) == 1
        assert len(work_chunks[0]['distraction_periods']) == 1
        assert len(distractions) == 1
    
    def test_calculate_focused_time(self):
        """Test focused time calculation"""
        exporter = OrgmodeExporter()
        
        # 6 periods of 10 seconds each = 60 seconds = 1 minute
        focused_periods = [{'timestamp': time(9, i, 0)} for i in range(6)]
        
        total_minutes = exporter._calculate_focused_time(focused_periods)
        assert total_minutes == 1
    
    def test_summarize_distractions(self):
        """Test distraction summarization"""
        exporter = OrgmodeExporter()
        
        distractions = [
            {'app': 'Slack', 'content': 'Checking messages', 'timestamp': time(9, 5, 0)},
            {'app': 'Slack', 'content': 'Replying to DM', 'timestamp': time(9, 10, 0)},
            {'app': 'Firefox', 'content': 'Reading news', 'timestamp': time(9, 15, 0)}
        ]
        
        summary = exporter._summarize_distractions(distractions)
        
        assert len(summary) == 2
        assert len(summary['Slack']) == 2
        assert len(summary['Firefox']) == 1
    
    def test_generate_orgmode_content_basic(self):
        """Test basic orgmode content generation"""
        exporter = OrgmodeExporter()
        target_date = datetime(2025, 6, 2, 9, 0, 0)
        
        work_chunks = [{
            'task': 'Write documentation',
            'start_time': time(9, 0, 0),
            'end_time': time(10, 0, 0),
            'focused_periods': [{'timestamp': time(9, i, 0)} for i in range(6)]  # 1 minute
        }]
        
        distractions = [
            {'app': 'Slack', 'content': 'Checking messages', 'timestamp': time(9, 30, 0)}
        ]
        
        content = exporter._generate_orgmode_content(work_chunks, distractions, target_date)
        
        assert '<2025-06-02 Mon 09:00> Write documentation' in content
        assert 'CLOCK: [2025-06-02 Mon 09:00]--[2025-06-02 Mon 10:00] =>  00:01' in content
        assert ':TAG: work' in content
        assert '<2025-06-02 Mon 09:00> Other tasks and distractions' in content
        assert ':TAG: distraction' in content
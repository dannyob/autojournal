# AutoJournal Configuration Guide

AutoJournal uses a centralized configuration system to manage AI models and application settings.

## Configuration File

Configuration is stored in: `~/.autojournal/config.json`

## AI Models

AutoJournal uses different AI models for different purposes:

### Model Purposes

| Purpose | Default Model | Description |
|---------|---------------|-------------|
| `activity_analysis` | `claude-3.5-sonnet-latest` | Analyzes screenshots to determine if you're on-task |
| `goal_breakdown` | `gpt-4o-mini` | Breaks down high-level goals into actionable tasks |
| `session_summary` | `claude-3.5-sonnet-latest` | Generates session summaries and productivity insights |
| `fallback` | `gpt-3.5-turbo` | Used when primary models fail |

### Why These Models?

- **Claude 3.5 Sonnet**: Excellent at understanding context and nuanced analysis
- **GPT-4o Mini**: Fast and cost-effective for structured task generation
- **GPT-3.5 Turbo**: Reliable fallback option

## Configuration Commands

### View Current Configuration
```bash
python autojournal.py --config
```

### List Available Models
```bash
python autojournal.py --list-models
```

### Change AI Models
```bash
# Set activity analysis model
python autojournal.py --set-model activity_analysis gpt-4o

# Set goal breakdown model  
python autojournal.py --set-model goal_breakdown claude-3.5-sonnet-latest

# Set session summary model
python autojournal.py --set-model session_summary gpt-4o-mini

# Set fallback model
python autojournal.py --set-model fallback claude-3-haiku
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `screenshot_interval` | `10` | Seconds between screenshot captures |
| `max_screenshot_retries` | `3` | Number of retries for failed screenshots |
| `analysis_timeout` | `30` | Timeout for AI analysis calls (seconds) |
| `confidence_threshold` | `0.3` | Minimum confidence for AI decisions |
| `debug_logging` | `false` | Enable detailed debug logging |

## Configuration Examples

### High-Performance Setup (Costs More)
```bash
python autojournal.py --set-model activity_analysis gpt-4o
python autojournal.py --set-model goal_breakdown gpt-4o  
python autojournal.py --set-model session_summary gpt-4o
```

### Cost-Effective Setup
```bash
python autojournal.py --set-model activity_analysis gpt-4o-mini
python autojournal.py --set-model goal_breakdown gpt-3.5-turbo
python autojournal.py --set-model session_summary gpt-4o-mini
```

### Claude-Only Setup
```bash
python autojournal.py --set-model activity_analysis claude-3.5-sonnet-latest
python autojournal.py --set-model goal_breakdown claude-3.5-sonnet-latest
python autojournal.py --set-model session_summary claude-3.5-sonnet-latest
python autojournal.py --set-model fallback claude-3-haiku
```

## Configuration File Structure

```json
{
  "models": {
    "activity_analysis": "claude-3.5-sonnet-latest",
    "goal_breakdown": "gpt-4o-mini", 
    "session_summary": "claude-3.5-sonnet-latest",
    "fallback": "gpt-3.5-turbo"
  },
  "settings": {
    "screenshot_interval": 10,
    "max_screenshot_retries": 3,
    "analysis_timeout": 30,
    "confidence_threshold": 0.3,
    "debug_logging": false
  }
}
```

## Model Requirements

### For Activity Analysis
- Good at understanding context and visual descriptions
- Reliable JSON output formatting
- Fast response times (called every 10 seconds)

**Recommended**: Claude 3.5 Sonnet, GPT-4o, GPT-4o-mini

### For Goal Breakdown  
- Good at structured task generation
- Understands project planning concepts
- Cost-effective (called once per goal)

**Recommended**: GPT-4o-mini, Claude 3.5 Sonnet, GPT-3.5 Turbo

### For Session Summary
- Excellent at analysis and insights
- Good writing capabilities
- Understanding of productivity concepts

**Recommended**: Claude 3.5 Sonnet, GPT-4o

## Troubleshooting

### Model Not Found Error
If you get "Unknown model" errors:
1. Check available models: `python autojournal.py --list-models`
2. Ensure you have the required LLM plugins installed:
   - `llm-anthropic` for Claude models
   - OpenAI models work by default

### Cost Management
- Use GPT-4o-mini or GPT-3.5-turbo for frequent operations
- Use premium models (GPT-4o, Claude 3.5 Sonnet) for quality-critical tasks
- Monitor usage in your AI provider's dashboard

### Performance Tuning
- Decrease `screenshot_interval` for more frequent monitoring (higher cost)
- Increase `analysis_timeout` if models are slow
- Enable `debug_logging` to troubleshoot issues
# Meeting Agent AI Services Integration

## Overview

The Meeting Agent now integrates with **OpenAI's Whisper API** for transcription and **GPT-4** for meeting analysis. The system gracefully falls back to simulation when API keys are not available.

## Services Implemented

### 🎤 Transcription Service - OpenAI Whisper

**Primary Service**: OpenAI Whisper API
- **Model**: `whisper-1`
- **Features**: 
  - Multi-language support (50+ languages)
  - Timestamped segments
  - High accuracy speech-to-text
  - Audio file format support (MP3, MP4, M4A, WAV, etc.)

**Fallback**: Simulated transcription data when API key not available

### 🤖 Summary Service - OpenAI GPT-4

**Primary Service**: OpenAI GPT-4
- **Model**: `gpt-4`
- **Features**:
  - Meeting summarization
  - Key points extraction
  - Decision tracking
  - Action item identification with assignees and priorities

**Fallback**: Pre-defined summary templates when API key not available

## Configuration

### Environment Variables

Add these to your environment or `.env` file:

```bash
# Required for AI services
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: OpenAI organization (if you have one)
OPENAI_ORG_ID=org-your-organization-id
```

### Cost Considerations

**Whisper API Pricing** (as of 2024):
- $0.006 per minute of audio
- Example: 1-hour meeting = $0.36

**GPT-4 API Pricing** (as of 2024):
- Input: $0.03 per 1K tokens
- Output: $0.06 per 1K tokens
- Example: Meeting summary = ~$0.10-0.50 per meeting

## Technical Implementation

### Transcription Flow

1. **Recording Capture**: Browser automation captures meeting audio/video
2. **File Download**: System downloads recording from storage URL
3. **Whisper Processing**: Audio sent to OpenAI Whisper API
4. **Segment Processing**: Timestamps and text extracted
5. **Database Storage**: Segments saved to MongoDB with speaker identification

### Summary Generation Flow

1. **Transcription Input**: Full meeting transcription text
2. **GPT-4 Analysis**: Structured prompts for meeting analysis
3. **JSON Parsing**: Structured data extraction
4. **Action Items**: Separate GPT-4 call for task identification
5. **Database Storage**: Summary and action items saved to session

## Code Architecture

### TranscriptionService Class

```python
class TranscriptionService:
    def __init__(self):
        # Initialize OpenAI client
        openai.api_key = os.environ.get('OPENAI_API_KEY')
    
    def start_transcription(self, session):
        # Main transcription entry point
        
    def _transcribe_with_whisper(self, session_id, recording_url, metadata):
        # Download recording and process with Whisper
        
    def _process_whisper_response(self, session_id, transcript):
        # Convert Whisper output to our database format
```

### SummaryService Class

```python
class SummaryService:
    def __init__(self):
        # Initialize OpenAI client
        
    def generate_summary(self, session):
        # Main summary generation entry point
        
    def _generate_gpt4_summary(self, transcription, metadata):
        # Use GPT-4 for meeting summary
        
    def _extract_action_items_gpt4(self, transcription):
        # Use GPT-4 for action item extraction
```

## API Integration Details

### Whisper API Call

```python
transcript = openai.Audio.transcribe(
    model="whisper-1",
    file=audio_file,
    response_format="verbose_json",
    timestamp_granularities=["segment"],
    language=language  # e.g., 'en', 'es', 'fr'
)
```

### GPT-4 API Call

```python
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are an expert meeting analyst..."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3,
    max_tokens=1000
)
```

## Supported Audio Formats

Whisper supports these audio formats:
- MP3, MP4, MPEG, MPGA
- M4A, WAV, WEBM
- Maximum file size: 25 MB

## Language Support

Whisper supports 50+ languages including:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Russian (ru)
- Arabic (ar)

## Error Handling & Fallbacks

### Graceful Degradation

1. **No API Key**: Uses simulated data, system still functional
2. **API Failures**: Falls back to simulation, logs errors
3. **Invalid Audio**: Attempts processing, falls back on failure
4. **Rate Limits**: Implements retry logic with exponential backoff

### Monitoring

- All API calls are logged
- Success/failure rates tracked
- Cost monitoring (token usage)
- Performance metrics (processing time)

## Production Recommendations

### 1. API Key Security
```bash
# Use environment variables, never commit keys
export OPENAI_API_KEY=sk-...
```

### 2. Rate Limiting
- Implement request queuing
- Add retry logic with backoff
- Monitor API usage and costs

### 3. Audio Processing
- Compress audio before sending to Whisper
- Implement chunking for long recordings
- Add audio format validation

### 4. Speaker Diarization
For better speaker identification, consider:
- **Pyannote.audio** for speaker diarization
- **Azure Speaker Recognition** 
- **Custom speaker embedding models**

## Future Enhancements

### 1. Real-time Transcription
- **AssemblyAI Real-time API**
- **Google Cloud Speech Streaming**
- **Azure Real-time Speech**

### 2. Advanced AI Features
- **Sentiment Analysis**: Track meeting mood
- **Topic Modeling**: Identify discussion themes
- **Meeting Insights**: Participation analysis

### 3. Integration Improvements
- **Calendar Integration**: Auto-schedule transcription
- **CRM Integration**: Link to customer meetings
- **Slack/Teams Bots**: Automated meeting summaries

## Setup Instructions

1. **Get OpenAI API Key**:
   - Sign up at https://platform.openai.com/
   - Create API key in dashboard
   - Add billing information

2. **Install Dependencies**:
   ```bash
   pip install openai requests
   ```

3. **Set Environment Variable**:
   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   ```

4. **Test Integration**:
   ```bash
   python manage.py shell
   >>> from apps.meeting_agent.services import TranscriptionService
   >>> service = TranscriptionService()
   >>> # Test with audio file
   ```

## Cost Optimization Tips

1. **Audio Compression**: Reduce file sizes before API calls
2. **Selective Processing**: Only transcribe when requested
3. **Batch Processing**: Group multiple short recordings
4. **Quality Settings**: Use appropriate quality for use case
5. **Caching**: Store results to avoid re-processing

## Troubleshooting

### Common Issues

1. **API Key Issues**:
   - Verify key is set correctly
   - Check API key permissions
   - Ensure billing is set up

2. **Audio Format Issues**:
   - Convert to supported formats
   - Check file size limits (25 MB)
   - Validate audio quality

3. **Rate Limiting**:
   - Implement exponential backoff
   - Monitor API usage
   - Consider upgrading API tier

The system now uses real AI services for production-quality transcription and summarization while maintaining fallback functionality for development and testing!

# Design Document

## Overview

This design document outlines the implementation of OpenAI's gpt-4o-mini-transcribe model as a new transcription engine in the real-time transcription and translation application. The implementation will integrate seamlessly with the existing transcription architecture while providing access to OpenAI's high-quality, cost-effective transcription capabilities.

The design follows the existing pattern used by Google and Whisper transcription engines, ensuring consistency and maintainability. The OpenAI transcription engine will support real-time audio processing, multi-language transcription, and automatic language detection.

## Architecture

### High-Level Architecture

The OpenAI transcription integration follows the existing transcription engine pattern:

```
Audio Input → AudioTranscriber → OpenAI API → Transcription Result → Translation Pipeline
```

### Component Integration

1. **Configuration Layer**: Extends the existing configuration system to include OpenAI API key management and engine selection
2. **Language Support**: Updates the transcription language mapping to include OpenAI-specific language codes
3. **Transcription Engine**: Implements OpenAI API integration within the existing AudioTranscriber framework
4. **Error Handling**: Provides robust error handling and fallback mechanisms for API failures
5. **Authentication**: Securely manages OpenAI API keys with validation and error reporting

## Components and Interfaces

### 1. Configuration Extensions

**File**: `src-python/config.py`

New configuration properties:
- `OPENAI_API_KEY`: Stores the OpenAI API key securely
- Updates to `SELECTABLE_TRANSCRIPTION_ENGINE_STATUS` to include OpenAI engine availability

**Interface**:
```python
@property
@json_serializable('OPENAI_API_KEY')
def OPENAI_API_KEY(self):
    return self._OPENAI_API_KEY

@OPENAI_API_KEY.setter
def OPENAI_API_KEY(self, value):
    if isinstance(value, str):
        self._OPENAI_API_KEY = value
        self.saveConfig(inspect.currentframe().f_code.co_name, value)
```

### 2. Language Mapping Updates

**File**: `src-python/models/transcription/transcription_languages.py`

Extends the existing `transcription_lang` dictionary to include OpenAI language mappings:

```python
# Example addition to existing language entries
"English": {
    "United States": {
        "Google": "en-US",
        "Whisper": "en",
        "OpenAI": "en"
    },
    # ... other countries
},
```

### 3. OpenAI Transcription Module

**New File**: `src-python/models/transcription/transcription_openai.py`

Core OpenAI integration module providing:
- API client initialization and management
- Audio format conversion for OpenAI API compatibility
- Request/response handling with proper error management
- Rate limiting and retry logic

**Key Classes**:
```python
class OpenAITranscriber:
    def __init__(self, api_key: str):
        # Initialize OpenAI client
        
    def transcribe_audio(self, audio_data: bytes, language: str = None) -> dict:
        # Send audio to OpenAI API and return transcription
        
    def validate_api_key(self) -> bool:
        # Validate API key with OpenAI
```

### 4. AudioTranscriber Integration

**File**: `src-python/models/transcription/transcription_transcriber.py`

Extends the existing `AudioTranscriber` class to support OpenAI transcription:

```python
# New case in transcribeAudioQueue method
case "OpenAI":
    if self.openai_transcriber:
        for language, country in zip(languages, countries):
            try:
                openai_lang = transcription_lang[language][country]["OpenAI"]
                result = self.openai_transcriber.transcribe_audio(
                    audio_data, 
                    language=openai_lang
                )
                confidences.append({
                    "confidence": result.get("confidence", 0.9),
                    "text": result.get("text", ""),
                    "language": language
                })
            except Exception as e:
                # Handle API errors gracefully
                pass
```

### 5. Controller Updates

**File**: `src-python/controller.py`

Updates to support OpenAI engine configuration and status management:
- API key validation endpoints
- Engine availability checking
- Error reporting for API issues

## Data Models

### OpenAI API Request Format

```python
{
    "model": "gpt-4o-mini-transcribe",
    "audio": "<base64_encoded_audio>",
    "language": "en",  # Optional language hint
    "response_format": "json"
}
```

### OpenAI API Response Format

```python
{
    "text": "Transcribed text content",
    "language": "en",
    "confidence": 0.95,
    "duration": 2.5
}
```

### Internal Transcription Result Format

Maintains compatibility with existing transcription result format:

```python
{
    "confidence": float,  # 0.0 to 1.0
    "text": str,         # Transcribed text
    "language": str      # Detected/specified language
}
```

## Error Handling

### API Error Categories

1. **Authentication Errors**
   - Invalid API key
   - Expired API key
   - Insufficient permissions

2. **Rate Limiting**
   - Request rate exceeded
   - Token limit exceeded
   - Concurrent request limit

3. **Network Errors**
   - Connection timeout
   - Network unavailable
   - DNS resolution failure

4. **Audio Processing Errors**
   - Unsupported audio format
   - Audio file too large
   - Audio quality issues

### Error Handling Strategy

```python
class OpenAITranscriptionError(Exception):
    def __init__(self, error_type: str, message: str, retry_after: int = None):
        self.error_type = error_type
        self.message = message
        self.retry_after = retry_after

def handle_openai_error(error):
    if error.status_code == 401:
        # Authentication error - disable engine
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["OpenAI"] = False
        return OpenAITranscriptionError("auth", "Invalid API key")
    elif error.status_code == 429:
        # Rate limiting - implement backoff
        retry_after = error.headers.get("Retry-After", 60)
        return OpenAITranscriptionError("rate_limit", "Rate limit exceeded", retry_after)
    # ... other error types
```

### Fallback Mechanisms

1. **Graceful Degradation**: When OpenAI API fails, log the error and return empty result
2. **Engine Switching**: Option to automatically fall back to Google/Whisper engines
3. **Retry Logic**: Exponential backoff for transient failures
4. **User Notification**: Clear error messages in the UI for configuration issues

## Testing Strategy

### Unit Tests

1. **OpenAI Module Tests**
   - API client initialization
   - Audio format conversion
   - Request/response handling
   - Error handling scenarios

2. **Integration Tests**
   - AudioTranscriber with OpenAI engine
   - Configuration management
   - Language mapping validation

3. **Mock Testing**
   - OpenAI API responses
   - Network failure scenarios
   - Rate limiting behavior

### Test Data

- Sample audio files in various formats
- Mock API responses for different scenarios
- Error response samples for testing error handling

### Performance Testing

- Latency measurements for API calls
- Memory usage during audio processing
- Concurrent request handling

## Security Considerations

### API Key Management

1. **Storage**: API keys stored in encrypted configuration
2. **Transmission**: HTTPS-only communication with OpenAI API
3. **Validation**: Regular API key validation to detect expiration
4. **Logging**: Ensure API keys are never logged or exposed

### Audio Data Privacy

1. **Transmission**: Audio data sent securely to OpenAI API
2. **Retention**: Follow OpenAI's data retention policies
3. **Compliance**: Ensure compliance with privacy regulations

## Implementation Notes

### Audio Format Requirements

OpenAI API supports various audio formats. The implementation will:
- Convert audio to supported formats (MP3, WAV, M4A, etc.)
- Handle sample rate conversion if needed
- Manage audio chunk sizes for optimal API performance

### Language Detection

OpenAI supports automatic language detection:
- When no language is specified, use automatic detection
- When multiple languages are configured, try each language
- Return detected language information with transcription results

### Rate Limiting Strategy

Implement intelligent rate limiting:
- Track API usage and remaining quota
- Implement exponential backoff for rate limit errors
- Queue requests during high-traffic periods
- Provide user feedback on rate limit status
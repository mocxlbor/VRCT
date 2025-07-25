import json
import base64
import time
from typing import Optional, Dict, Any
import requests
from io import BytesIO
import wave
from utils import errorLogging

class OpenAITranscriptionError(Exception):
    """Custom exception for OpenAI transcription errors"""
    def __init__(self, error_type: str, message: str, retry_after: Optional[int] = None):
        self.error_type = error_type
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)

class OpenAITranscriber:
    """OpenAI transcription client for gpt-4o-mini-transcribe model"""
    
    def __init__(self, api_key: str):
        """
        Initialize OpenAI transcriber
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini-transcribe"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
    def validate_api_key(self) -> bool:
        """
        Validate the OpenAI API key
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Test API key with a simple request to models endpoint
            response = self.session.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception as e:
            errorLogging()
            return False
    
    def _prepare_audio_data(self, audio_data: bytes, sample_rate: int, sample_width: int, channels: int) -> str:
        """
        Prepare audio data for OpenAI API
        
        Args:
            audio_data: Raw audio bytes
            sample_rate: Audio sample rate
            sample_width: Audio sample width
            channels: Number of audio channels
            
        Returns:
            str: Base64 encoded audio data
        """
        try:
            # Create WAV format audio data
            temp_file = BytesIO()
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)
            
            temp_file.seek(0)
            audio_bytes = temp_file.read()
            
            # Encode to base64
            return base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as e:
            errorLogging()
            raise OpenAITranscriptionError("audio_processing", f"Failed to prepare audio data: {str(e)}")
    
    def transcribe_audio(self, audio_data: bytes, sample_rate: int, sample_width: int, 
                        channels: int, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI API
        
        Args:
            audio_data: Raw audio bytes
            sample_rate: Audio sample rate
            sample_width: Audio sample width
            channels: Number of audio channels
            language: Optional language code for transcription
            
        Returns:
            Dict containing transcription result with keys: text, language, confidence
        """
        try:
            # Prepare audio data
            encoded_audio = self._prepare_audio_data(audio_data, sample_rate, sample_width, channels)
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "audio": encoded_audio,
                "response_format": "json"
            }
            
            # Add language if specified
            if language:
                payload["language"] = language
            
            # Make API request
            response = self.session.post(
                f"{self.base_url}/audio/transcriptions",
                json=payload,
                timeout=30
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get("text", ""),
                    "language": result.get("language", language or "auto"),
                    "confidence": 0.9  # OpenAI doesn't provide confidence scores, use default
                }
            else:
                self._handle_api_error(response)
                
        except requests.exceptions.RequestException as e:
            errorLogging()
            raise OpenAITranscriptionError("network", f"Network error: {str(e)}")
        except Exception as e:
            errorLogging()
            raise OpenAITranscriptionError("unknown", f"Transcription failed: {str(e)}")
    
    def _handle_api_error(self, response: requests.Response):
        """
        Handle API error responses
        
        Args:
            response: HTTP response object
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown API error")
        except:
            error_message = f"HTTP {response.status_code}: {response.text}"
        
        if response.status_code == 401:
            raise OpenAITranscriptionError("auth", f"Authentication failed: {error_message}")
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise OpenAITranscriptionError("rate_limit", f"Rate limit exceeded: {error_message}", retry_after)
        elif response.status_code == 400:
            raise OpenAITranscriptionError("bad_request", f"Bad request: {error_message}")
        elif response.status_code >= 500:
            raise OpenAITranscriptionError("server_error", f"Server error: {error_message}")
        else:
            raise OpenAITranscriptionError("api_error", f"API error: {error_message}")

def check_openai_api_key(api_key: str) -> bool:
    """
    Check if OpenAI API key is valid
    
    Args:
        api_key: OpenAI API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    try:
        transcriber = OpenAITranscriber(api_key)
        return transcriber.validate_api_key()
    except Exception:
        errorLogging()
        return False
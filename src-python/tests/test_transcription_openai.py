import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from io import BytesIO
import wave

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.transcription.transcription_openai import (
    OpenAITranscriber, 
    OpenAITranscriptionError, 
    check_openai_api_key
)

class TestOpenAITranscriber(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "sk-test-api-key-12345"
        self.transcriber = OpenAITranscriber(self.api_key)
        
        # Sample audio data
        self.sample_rate = 16000
        self.sample_width = 2
        self.channels = 1
        self.audio_data = b'\x00\x01' * 1000  # Mock audio data
        
    def test_init(self):
        """Test OpenAITranscriber initialization"""
        self.assertEqual(self.transcriber.api_key, self.api_key)
        self.assertEqual(self.transcriber.model, "gpt-4o-mini-transcribe")
        self.assertEqual(self.transcriber.base_url, "https://api.openai.com/v1")
        self.assertIn("Authorization", self.transcriber.session.headers)
        
    @patch('requests.Session.get')
    def test_validate_api_key_success(self, mock_get):
        """Test successful API key validation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.transcriber.validate_api_key()
        self.assertTrue(result)
        mock_get.assert_called_once_with("https://api.openai.com/v1/models")
        
    @patch('requests.Session.get')
    def test_validate_api_key_failure(self, mock_get):
        """Test failed API key validation"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = self.transcriber.validate_api_key()
        self.assertFalse(result)
        
    @patch('requests.Session.get')
    def test_validate_api_key_exception(self, mock_get):
        """Test API key validation with exception"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.transcriber.validate_api_key()
        self.assertFalse(result)
        
    def test_prepare_audio_data(self):
        """Test audio data preparation"""
        encoded_audio = self.transcriber._prepare_audio_data(
            self.audio_data, self.sample_rate, self.sample_width, self.channels
        )
        
        # Verify it's base64 encoded
        self.assertIsInstance(encoded_audio, str)
        
        # Verify we can decode it back
        decoded = base64.b64decode(encoded_audio)
        self.assertIsInstance(decoded, bytes)
        
    def test_prepare_audio_data_exception(self):
        """Test audio data preparation with invalid data"""
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber._prepare_audio_data(
                None, self.sample_rate, self.sample_width, self.channels
            )
        self.assertEqual(context.exception.error_type, "audio_processing")
        
    @patch('requests.Session.post')
    def test_transcribe_audio_success(self, mock_post):
        """Test successful audio transcription"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Hello world",
            "language": "en"
        }
        mock_post.return_value = mock_response
        
        result = self.transcriber.transcribe_audio(
            self.audio_data, self.sample_rate, self.sample_width, self.channels
        )
        
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["confidence"], 0.9)
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.openai.com/v1/audio/transcriptions")
        
    @patch('requests.Session.post')
    def test_transcribe_audio_with_language(self, mock_post):
        """Test audio transcription with specified language"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Hola mundo",
            "language": "es"
        }
        mock_post.return_value = mock_response
        
        result = self.transcriber.transcribe_audio(
            self.audio_data, self.sample_rate, self.sample_width, self.channels, language="es"
        )
        
        self.assertEqual(result["text"], "Hola mundo")
        self.assertEqual(result["language"], "es")
        
        # Verify language was passed in request
        call_args = mock_post.call_args
        self.assertIn('data', call_args.kwargs)
        payload = call_args.kwargs['data']
        self.assertEqual(payload['language'], 'es')
    @patch('requests.Session.post')
    def test_transcribe_audio_auth_error(self, mock_post):
        """Test transcription with authentication error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key"}
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber.transcribe_audio(
                self.audio_data, self.sample_rate, self.sample_width, self.channels
            )
        
        self.assertEqual(context.exception.error_type, "auth")
        self.assertIn("Authentication failed", str(context.exception))
        
    @patch('requests.Session.post')
    def test_transcribe_audio_rate_limit_error(self, mock_post):
        """Test transcription with rate limit error"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber.transcribe_audio(
                self.audio_data, self.sample_rate, self.sample_width, self.channels
            )
        
        self.assertEqual(context.exception.error_type, "rate_limit")
        self.assertEqual(context.exception.retry_after, 60)
        
    @patch('requests.Session.post')
    def test_transcribe_audio_server_error(self, mock_post):
        """Test transcription with server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "error": {"message": "Internal server error"}
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber.transcribe_audio(
                self.audio_data, self.sample_rate, self.sample_width, self.channels
            )
        
        self.assertEqual(context.exception.error_type, "server_error")
        
    @patch('requests.Session.post')
    def test_transcribe_audio_network_error(self, mock_post):
        """Test transcription with network error"""
        mock_post.side_effect = Exception("Network timeout")
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber.transcribe_audio(
                self.audio_data, self.sample_rate, self.sample_width, self.channels
            )
        
        self.assertEqual(context.exception.error_type, "network")
        
    def test_handle_api_error_bad_request(self):
        """Test API error handling for bad request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Bad request"}
        }
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber._handle_api_error(mock_response)
        
        self.assertEqual(context.exception.error_type, "bad_request")
        
    def test_handle_api_error_json_parse_error(self):
        """Test API error handling when JSON parsing fails"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = Exception("JSON parse error")
        mock_response.text = "Bad request text"
        
        with self.assertRaises(OpenAITranscriptionError) as context:
            self.transcriber._handle_api_error(mock_response)
        
        self.assertEqual(context.exception.error_type, "bad_request")
        self.assertIn("HTTP 400", str(context.exception))


class TestOpenAITranscriptionError(unittest.TestCase):
    
    def test_error_creation(self):
        """Test OpenAITranscriptionError creation"""
        error = OpenAITranscriptionError("auth", "Invalid API key", 60)
        
        self.assertEqual(error.error_type, "auth")
        self.assertEqual(error.message, "Invalid API key")
        self.assertEqual(error.retry_after, 60)
        self.assertEqual(str(error), "Invalid API key")
        
    def test_error_without_retry_after(self):
        """Test OpenAITranscriptionError without retry_after"""
        error = OpenAITranscriptionError("network", "Connection failed")
        
        self.assertEqual(error.error_type, "network")
        self.assertEqual(error.message, "Connection failed")
        self.assertIsNone(error.retry_after)


class TestCheckOpenAIApiKey(unittest.TestCase):
    
    @patch('models.transcription.transcription_openai.OpenAITranscriber')
    def test_check_valid_api_key(self, mock_transcriber_class):
        """Test checking valid API key"""
        mock_transcriber = Mock()
        mock_transcriber.validate_api_key.return_value = True
        mock_transcriber_class.return_value = mock_transcriber
        
        result = check_openai_api_key("sk-valid-key")
        self.assertTrue(result)
        
    @patch('models.transcription.transcription_openai.OpenAITranscriber')
    def test_check_invalid_api_key(self, mock_transcriber_class):
        """Test checking invalid API key"""
        mock_transcriber = Mock()
        mock_transcriber.validate_api_key.return_value = False
        mock_transcriber_class.return_value = mock_transcriber
        
        result = check_openai_api_key("invalid-key")
        self.assertFalse(result)
        
    def test_check_empty_api_key(self):
        """Test checking empty API key"""
        result = check_openai_api_key("")
        self.assertFalse(result)
        
    def test_check_none_api_key(self):
        """Test checking None API key"""
        result = check_openai_api_key(None)
        self.assertFalse(result)
        
    def test_check_non_string_api_key(self):
        """Test checking non-string API key"""
        result = check_openai_api_key(12345)
        self.assertFalse(result)
        
    @patch('models.transcription.transcription_openai.OpenAITranscriber')
    def test_check_api_key_exception(self, mock_transcriber_class):
        """Test checking API key with exception"""
        mock_transcriber_class.side_effect = Exception("Connection error")
        
        result = check_openai_api_key("sk-test-key")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
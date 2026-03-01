"""Voice interface component."""
import uuid
import boto3
from botocore.exceptions import ClientError

from ..models.voice import TranscriptionResult, VoiceQueryResult
from ..models.enums import SupportedLanguage
from ..models.query import Citation
from ..config import load_config
from .query_engine import QueryEngine


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""
    pass


class VoiceInterface:
    """Handles multilingual voice input and output."""
    
    LANGUAGE_CODES = {
        SupportedLanguage.HINDI: 'hi-IN',
        SupportedLanguage.TELUGU: 'te-IN',
        SupportedLanguage.TAMIL: 'ta-IN',
        SupportedLanguage.ENGLISH: 'en-IN'
    }
    
    def __init__(self):
        self.config = load_config()
        self.transcribe_client = boto3.client('transcribe', region_name=self.config.region)
        self.translate_client = boto3.client('translate', region_name=self.config.region)
        self.polly_client = boto3.client('polly', region_name=self.config.region)
        self.s3_client = boto3.client('s3', region_name=self.config.region)
        self.query_engine = QueryEngine()
    
    async def transcribe_audio(self, audio_bytes: bytes, language: SupportedLanguage) -> TranscriptionResult:
        """
        Transcribe audio to text using AWS Transcribe.
        
        Args:
            audio_bytes: Audio file content (WAV, MP3, or FLAC)
            language: Expected language of the audio
            
        Returns:
            TranscriptionResult with text and confidence
            
        Raises:
            TranscriptionError: If audio quality too poor or service unavailable
        """
        try:
            # Upload audio to S3 for Transcribe
            job_name = f"transcribe-{uuid.uuid4()}"
            audio_key = f"audio/transcribe/{job_name}.mp3"
            
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=audio_key,
                Body=audio_bytes
            )
            
            # Start transcription job
            language_code = self.LANGUAGE_CODES[language]
            
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': f"s3://{self.config.s3_bucket}/{audio_key}"},
                MediaFormat='mp3',
                LanguageCode=language_code
            )
            
            # Wait for job completion
            import time
            while True:
                status = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                job_status = status['TranscriptionJob']['TranscriptionJobStatus']
                
                if job_status == 'COMPLETED':
                    transcript = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    # Fetch transcript
                    import requests
                    transcript_data = requests.get(transcript).json()
                    text = transcript_data['results']['transcripts'][0]['transcript']
                    
                    # Calculate average confidence
                    items = transcript_data['results'].get('items', [])
                    confidences = [float(item.get('alternatives', [{}])[0].get('confidence', 0.0)) 
                                 for item in items if 'confidence' in item.get('alternatives', [{}])[0]]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                    
                    return TranscriptionResult(
                        text=text,
                        language=language,
                        confidence=avg_confidence
                    )
                    
                elif job_status == 'FAILED':
                    raise TranscriptionError("Transcription job failed. Please try again with clearer audio.")
                
                time.sleep(2)
                
        except ClientError as e:
            raise TranscriptionError(f"Failed to transcribe audio: {str(e)}")
    
    async def translate_to_english(self, text: str, source_language: SupportedLanguage) -> str:
        """Translate regional language text to English using Amazon Translate."""
        if source_language == SupportedLanguage.ENGLISH:
            return text
        
        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode=source_language.value,
                TargetLanguageCode='en'
            )
            return response['TranslatedText']
        except ClientError as e:
            raise Exception(f"Translation failed: {str(e)}")
    
    async def translate_from_english(self, text: str, target_language: SupportedLanguage) -> str:
        """Translate English text to regional language using Amazon Translate."""
        if target_language == SupportedLanguage.ENGLISH:
            return text
        
        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode='en',
                TargetLanguageCode=target_language.value
            )
            return response['TranslatedText']
        except ClientError as e:
            raise Exception(f"Translation failed: {str(e)}")
    
    async def synthesize_speech(self, text: str, language: SupportedLanguage) -> bytes:
        """
        Convert text to speech using AWS Polly.

        Voice mapping:
        - Hindi/Telugu/Tamil: Aditi (standard only — neural not supported)
        - English: Joanna (neural supported)
        """
        voice_map = {
            SupportedLanguage.HINDI: ('Aditi', 'standard'),
            SupportedLanguage.TELUGU: ('Aditi', 'standard'),
            SupportedLanguage.TAMIL: ('Aditi', 'standard'),
            SupportedLanguage.ENGLISH: ('Joanna', 'neural'),
        }

        try:
            voice_id, engine = voice_map[language]
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine=engine,
            )
            
            audio_bytes = response['AudioStream'].read()
            return audio_bytes
            
        except ClientError as e:
            raise Exception(f"Speech synthesis failed: {str(e)}")
    
    async def process_voice_query(self, audio_bytes: bytes, language: SupportedLanguage) -> VoiceQueryResult:
        """
        End-to-end voice query processing.
        
        Pipeline:
        1. Transcribe audio to text
        2. Translate to English (if not English)
        3. Query the Knowledge Base
        4. Translate response to user's language
        5. Synthesize speech
        """
        # Step 1: Transcribe audio
        transcription = await self.transcribe_audio(audio_bytes, language)
        
        # Step 2: Translate to English
        english_query = await self.translate_to_english(transcription.text, language)
        
        # Step 3: Query Knowledge Base
        query_result = await self.query_engine.query(english_query, language='en')
        
        # Step 4: Translate response back to user's language
        translated_answer = await self.translate_from_english(query_result.answer, language)
        
        # Step 5: Synthesize speech
        try:
            audio_response = await self.synthesize_speech(translated_answer, language)
            
            # Store audio in S3
            audio_key = f"audio/{query_result.query_id}/response.mp3"
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=audio_key,
                Body=audio_response,
                ContentType='audio/mpeg'
            )
            
            audio_url = f"s3://{self.config.s3_bucket}/{audio_key}"
            
        except Exception as e:
            # Fallback: return text response if synthesis fails
            audio_url = ""
        
        return VoiceQueryResult(
            transcribed_text=transcription.text,
            translated_query=english_query,
            answer_text=query_result.answer,
            translated_answer=translated_answer,
            audio_url=audio_url,
            citations=query_result.citations
        )

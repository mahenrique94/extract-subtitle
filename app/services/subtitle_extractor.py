import os
import whisper
from datetime import datetime
from app import db
from app.models import SubtitleExtraction
from app.config.languages import SUPPORTED_LANGUAGES, get_whisper_model
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class SubtitleExtractor:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        logger.info(f"Initializing SubtitleExtractor with upload folder: {upload_folder}")
        logger.info("Loading Whisper model...")
        self.model = whisper.load_model("large")
        logger.info("Whisper model loaded successfully")
        os.makedirs(upload_folder, exist_ok=True)

    def save_file(self, file, extraction_id):
        logger.info(f"Saving file: {file.filename}")
        try:
            # Update progress to 5% - Starting file save
            extraction = SubtitleExtraction.query.get(extraction_id)
            extraction.progress = 5
            db.session.commit()

            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.upload_folder, unique_filename)
            
            # Update progress to 10% - File saved
            file.save(file_path)
            extraction.progress = 10
            db.session.commit()
            
            logger.info(f"File saved as: {unique_filename}")
            return unique_filename, file_path
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise

    def extract_subtitles(self, file_path, extraction_id):
        logger.info(f"Starting subtitle extraction for {file_path}")
        try:
            # Update progress to 15% - Starting transcription
            extraction = SubtitleExtraction.query.get(extraction_id)
            if not extraction:
                raise Exception(f"Extraction {extraction_id} not found")
            
            extraction.status = 'processing'
            extraction.progress = 15
            db.session.commit()

            # Update progress to 20% - Model loaded and ready
            extraction.progress = 20
            db.session.commit()

            # Transcribe the audio - let Whisper detect the language automatically
            logger.info("Starting transcription...")
            result = self.model.transcribe(
                file_path,
                task="transcribe",  # Use transcribe to keep original language
                verbose=True,
                word_timestamps=True
            )
            logger.info("Transcription completed successfully")
            
            # Get detected language from result
            detected_language = result.get('language', 'unknown')
            logger.info(f"Detected language: {detected_language}")

            # Update progress to 60% - Transcription complete
            extraction.progress = 60
            db.session.commit()

            # Generate SRT filename
            srt_filename = os.path.splitext(os.path.basename(file_path))[0] + '.srt'
            srt_path = os.path.join(self.upload_folder, srt_filename)
            logger.info(f"Generating SRT file: {srt_filename}")

            # Write SRT file
            with open(srt_path, 'w', encoding='utf-8') as f:
                total_segments = len(result['segments'])
                for i, segment in enumerate(result['segments'], start=1):
                    start = self._format_timestamp(segment['start'])
                    end = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                    
                    # Update progress based on segments processed (60-95%)
                    progress = 60 + (i / total_segments * 35)
                    extraction.progress = progress
                    db.session.commit()

            # Update progress to 95% - SRT file generated
            extraction.progress = 95
            db.session.commit()

            logger.info("SRT file generated successfully")
            return srt_filename, detected_language

        except Exception as e:
            logger.error(f"Error in extract_subtitles: {str(e)}")
            # Update extraction status to failed
            extraction = SubtitleExtraction.query.get(extraction_id)
            if extraction:
                extraction.status = 'failed'
                extraction.error_message = str(e)
                db.session.commit()
            raise Exception(f"Error extracting subtitles: {str(e)}")

    def _format_timestamp(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

    def process_extraction(self, extraction_id):
        logger.info(f"Starting processing for extraction ID: {extraction_id}")
        extraction = SubtitleExtraction.query.get(extraction_id)
        if not extraction:
            logger.error(f"Extraction {extraction_id} not found")
            return

        try:
            logger.info(f"Updating extraction {extraction_id} status to processing")
            extraction.status = 'processing'
            extraction.progress = 0
            db.session.commit()

            file_path = os.path.join(self.upload_folder, extraction.original_filename)
            logger.info(f"Processing file: {file_path}")
            srt_filename, detected_language = self.extract_subtitles(file_path, extraction_id)

            logger.info(f"Extraction completed successfully. SRT file: {srt_filename}, Detected language: {detected_language}")
            extraction.srt_filename = srt_filename
            extraction.status = 'completed'
            extraction.progress = 100
            extraction.completed_at = datetime.utcnow()
            db.session.commit()

        except Exception as e:
            logger.error(f"Error processing extraction {extraction_id}: {str(e)}")
            extraction.status = 'failed'
            extraction.error_message = str(e)
            db.session.commit() 
from deep_translator import GoogleTranslator
import re
import logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

class SubtitleTranslator:
    # Language code mapping for common variations
    LANGUAGE_MAP = {
        'pt-BR': 'pt',
        'pt_BR': 'pt',
        'zh-CN': 'zh',
        'zh_CN': 'zh',
        'zh-TW': 'zh',
        'zh_TW': 'zh',
        'en-US': 'en',
        'en_US': 'en',
        'en-GB': 'en',
        'en_GB': 'en',
    }
    
    def __init__(self):
        self.translator = GoogleTranslator()
        self.max_chunk_length = 5000  # Maximum characters per translation request
        
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language code to a standard format."""
        if not lang_code:
            return 'en'
            
        # Convert to lowercase and replace hyphens with underscores
        normalized = lang_code.lower().replace('-', '_')
        
        # Check if we have a mapping for this code
        return self.LANGUAGE_MAP.get(normalized, normalized)
        
    def _validate_language_code(self, lang_code: str) -> bool:
        """Validate if the language code is supported."""
        try:
            # Try to translate a simple test string to validate the language code
            self.translator.translate('test', target=lang_code)
            return True
        except Exception as e:
            logger.error(f"Invalid language code {lang_code}: {str(e)}")
            return False
            
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect the language of the given text."""
        try:
            detected = self.translator.detect(text)
            return self._normalize_language_code(detected)
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return None
            
    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks that respect sentence boundaries."""
        # Split by newlines first to preserve subtitle formatting
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            if current_length + line_length > self.max_chunk_length:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks
        
    def translate_srt(self, content: str, target_lang: str) -> Tuple[str, Optional[str]]:
        """
        Translate SRT content to target language while preserving timing and formatting.
        Returns a tuple of (translated_content, detected_source_lang)
        """
        try:
            # Normalize and validate target language
            target_lang = self._normalize_language_code(target_lang)
            if not self._validate_language_code(target_lang):
                raise ValueError(f"Unsupported target language: {target_lang}")
            
            # Detect source language from the first non-empty text block
            source_lang = None
            for block in re.split(r'\n\s*\n', content.strip()):
                lines = block.split('\n')
                if len(lines) >= 3:
                    text = '\n'.join(lines[2:]).strip()
                    if text:
                        source_lang = self._detect_language(text)
                        break
            
            # If source language is same as target, return original content
            if source_lang and source_lang == target_lang:
                return content, source_lang
            
            # Split content into subtitle blocks
            blocks = re.split(r'\n\s*\n', content.strip())
            translated_blocks = []
            
            for block in blocks:
                lines = block.split('\n')
                if len(lines) < 3:  # Skip invalid blocks
                    continue
                    
                # Keep the first line (subtitle number) and second line (timing) unchanged
                translated_blocks.append(lines[0])  # Subtitle number
                translated_blocks.append(lines[1])  # Timing
                
                # Get the text lines
                text_lines = lines[2:]
                text_to_translate = '\n'.join(text_lines)
                
                if text_to_translate.strip():
                    try:
                        # Split text into chunks if needed
                        chunks = self._chunk_text(text_to_translate)
                        translated_chunks = []
                        
                        for chunk in chunks:
                            # Translate each chunk
                            translated_chunk = self.translator.translate(
                                chunk,
                                target=target_lang
                            )
                            translated_chunks.append(translated_chunk)
                        
                        # Combine translated chunks
                        translated_text = '\n'.join(translated_chunks)
                        
                        # Split translated text back into lines
                        translated_lines = translated_text.split('\n')
                        translated_blocks.extend(translated_lines)
                    except Exception as e:
                        logger.error(f"Error translating text: {str(e)}")
                        translated_blocks.extend(text_lines)  # Keep original on error
                else:
                    translated_blocks.extend(text_lines)
                
                # Add empty line between blocks
                translated_blocks.append('')
            
            # Join blocks and ensure proper formatting
            translated_content = '\n'.join(translated_blocks).strip() + '\n'
            return translated_content, source_lang
            
        except Exception as e:
            logger.error(f"Error in translate_srt: {str(e)}")
            raise 
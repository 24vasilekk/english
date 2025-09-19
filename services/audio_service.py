import asyncio
import aiofiles
import logging
from typing import Optional
from gtts import gTTS
from io import BytesIO
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.cache_dir = Path("audio_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.audio_cache = {}
    
    async def generate_pronunciation(self, text: str, language: str = "en") -> Optional[bytes]:
        """Генерация аудио произношения текста"""
        if not config.AUDIO_ENABLED:
            return None
        
        try:
            # Проверяем кэш в памяти
            cache_key = f"{text}_{language}"
            if cache_key in self.audio_cache:
                return self.audio_cache[cache_key]
            
            # Проверяем файловый кэш
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            if cache_file.exists():
                async with aiofiles.open(cache_file, 'rb') as f:
                    audio_data = await f.read()
                    self.audio_cache[cache_key] = audio_data
                    return audio_data
            
            # Генерируем новое аудио
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None, self._generate_tts, text, language
            )
            
            if audio_data:
                # Сохраняем в кэш
                self.audio_cache[cache_key] = audio_data
                
                # Сохраняем в файл
                async with aiofiles.open(cache_file, 'wb') as f:
                    await f.write(audio_data)
                
                logger.info(f"Generated audio for text: {text}")
                return audio_data
            
        except Exception as e:
            logger.error(f"Error generating audio for text '{text}': {e}")
        
        return None
    
    def _generate_tts(self, text: str, language: str) -> Optional[bytes]:
        """Синхронная генерация TTS"""
        try:
            tts = gTTS(text=text, lang=language, slow=False)
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            return audio_buffer.getvalue()
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
    
    async def clear_cache(self, older_than_days: int = 7) -> None:
        """Очистка старого кэша"""
        try:
            import time
            current_time = time.time()
            
            for cache_file in self.cache_dir.glob("*.mp3"):
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > (older_than_days * 24 * 3600):
                    cache_file.unlink()
                    logger.info(f"Removed old cache file: {cache_file}")
        
        except Exception as e:
            logger.error(f"Error clearing audio cache: {e}")
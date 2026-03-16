import whisper
from logger import get_logger

log = get_logger("WhisperSTT")


class WhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        log.info("Loading Whisper model (%s)", model_size)
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_file) -> str:
        log.info("Transcribing audio")
        result = self.model.transcribe(
            str(audio_file),
            fp16=False,
            temperature=0,
        )
        return result.get("text", "").strip()
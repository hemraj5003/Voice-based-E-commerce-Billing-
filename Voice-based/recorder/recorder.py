import time
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

from config import (
    AUDIO_FILE,
    SAMPLE_RATE,
    CHANNELS,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_SECONDS,
)
from logger import get_logger

log = get_logger("Recorder")


def record() -> None:
    """
    Record until silence is detected or max time reached.
    """
    log.info("Voice detection started... Speak now")

    audio_chunks = []
    silence_start = None
    start_time = time.time()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=1024,
    ) as stream:
        while True:
            data, _ = stream.read(1024)
            audio_chunks.append(data.copy())

            volume = np.abs(data).mean()

            if volume > SILENCE_THRESHOLD:
                silence_start = None
            else:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= SILENCE_DURATION:
                    log.info("Silence detected, stopping recording")
                    break

            if time.time() - start_time >= MAX_RECORD_SECONDS:
                log.info("Max record limit reached")
                break

    audio = np.concatenate(audio_chunks, axis=0)
    write(AUDIO_FILE, SAMPLE_RATE, audio)
    log.info("Recording saved to %s", AUDIO_FILE)
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model
import time

openwakeword.utils.download_models()
model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=1280
)

print("\n--- SAY 'HEY JARVIS' NOW ---")
start_time = time.time()
max_score = 0.0
try:
    while time.time() - start_time < 10:
        data = stream.read(1280, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(audio_data)
        score = prediction.get("hey_jarvis", 0.0)
        if score > max_score:
            max_score = score
        if score > 0.1:
            print(f"!!! WAKE DETECTED !!! Score: {score:.4f}")
        else:
            print(f"Score: {score:.4f}")
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    print(f"\nMax Score Recorded: {max_score:.4f}")
    stream.stop_stream()
    stream.close()
    p.terminate()

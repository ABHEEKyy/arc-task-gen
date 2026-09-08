import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model
import time

openwakeword.utils.download_models()
model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

p = pyaudio.PyAudio()
print("=== AUDIO INPUT DEVICES ===")
default_index = None
try:
    default_info = p.get_default_input_device_info()
    default_index = default_info.get("index")
    print(f"Default Input Device: #{default_index} - {default_info.get('name')}")
except Exception as e:
    print(f"Error getting default input device: {e}")

for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if dev.get("maxInputChannels", 0) > 0:
        print(f"Device #{i}: {dev.get('name')} (Max Channels: {dev.get('maxInputChannels')})")

print("\n--- LISTENING FOR AUDIO (Say 'Hey Jarvis' now) ---")
print("Printing live audio RMS volume and 'hey_jarvis' score every 0.2s...\n")

stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=1280
)

start_time = time.time()
try:
    while time.time() - start_time < 15:
        data = stream.read(1280, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        rms = float(np.sqrt(np.mean(audio_data.astype(np.float32)**2)))
        prediction = model.predict(audio_data)
        score = prediction.get("hey_jarvis", 0.0)
        
        bar = "#" * int(min(rms / 100, 30))
        print(f"RMS Volume: {rms:6.1f} | [{bar:<30}] | Hey Jarvis Score: {score:.4f}")
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()

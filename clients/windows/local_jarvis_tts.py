"""Local low-latency Coqui XTTS v2 TTS engine for Paul Bettany / J.A.R.V.I.S. voice synthesis.
"""

import os
import numpy as np
import sounddevice as sd
import torch

REFERENCE_WAV = "jarvis_reference.wav"
SAMPLE_RATE = 24000


class LocalJarvisTTS:
    def __init__(self, reference_path: str = REFERENCE_WAV) -> None:
        if not os.path.exists(reference_path):
            print(f"[Note]: Reference audio file '{reference_path}' not found!")
            print("Using fallback speaker synthesis until 'jarvis_reference.wav' is placed in workspace.")
            self.model = None
            return

        print("[Init]: Initializing Coqui XTTS v2 on GPU...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device != "cuda":
            print("[Warning]: CUDA not detected! Voice generation will run on CPU.")

        try:
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import Xtts
            from TTS.utils.manage import ModelManager

            model_path = ModelManager().download_model("tts_models/multilingual/multi-dataset/xtts_v2")
            config = XttsConfig()
            config.load_json(os.path.join(model_path, "config.json"))
            self.model = Xtts.init_from_config(config)
            self.model.load_checkpoint(config, checkpoint_dir=model_path, use_deepspeed=False)
            self.model.to(self.device)

            print("[Init]: Computing Paul Bettany speaker latents...")
            self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(
                audio_path=[reference_path]
            )
            print("[Init]: J.A.R.V.I.S. XTTS v2 voice model ready.\n")
        except Exception as e:
            print(f"[Error]: Failed to load local XTTS v2 model: {e}")
            self.model = None

    def speak_stream(self, text: str) -> None:
        """Generates and plays audio streaming in real-time chunks via sounddevice."""
        if not text.strip() or self.model is None:
            return

        try:
            stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32")
            stream.start()

            chunks = self.model.inference_stream(
                text=text,
                language="en",
                gpt_cond_latent=self.gpt_cond_latent,
                speaker_embedding=self.speaker_embedding,
                enable_text_splitting=True,
                stream_chunk_size=20,
            )

            for chunk in chunks:
                audio_np = chunk.cpu().numpy().astype(np.float32)
                stream.write(audio_np)

            stream.stop()
            stream.close()
        except Exception as e:
            print(f"[Error]: Local XTTS Streaming error: {e}")


if __name__ == "__main__":
    jarvis = LocalJarvisTTS()
    if jarvis.model is not None:
        jarvis.speak_stream(
            "At your service, Sir. All systems are fully functional and running locally on your graphics processor."
        )

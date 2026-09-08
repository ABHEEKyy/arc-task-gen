import os
import json
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types
from win_tools import WindowsController
from win_advanced_tools import SystemController
from jarvis_brain import BrainTools
from jarvis_memory import MemoryBrain, JARVIS_HUMAN_PROMPT

ALL_TOOLS = [
    WindowsController.launch_application,
    WindowsController.system_volume,
    WindowsController.window_management,
    WindowsController.type_text,
    SystemController.open_website,
    SystemController.terminate_process,
    SystemController.get_system_telemetry,
    BrainTools.web_search,
    BrainTools.get_weather
]


class JarvisAgent:
    def __init__(self, tts_speak_function):
        self.tts_speak_function = tts_speak_function
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        try:
            import ollama
            # Test connection to local Ollama daemon
            ollama.list()
            self.provider = "ollama"
            self.model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            print(f"[Jarvis Agent]: Using local Ollama model '{self.model_name}'", flush=True)
        except Exception:
            if self.gemini_key:
                self.gclient = genai.Client(api_key=self.gemini_key)
                self.chat = self.gclient.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=JARVIS_HUMAN_PROMPT,
                        tools=ALL_TOOLS,
                        temperature=0.7
                    )
                )
                self.provider = "gemini"
            elif self.openai_key:
                from openai import OpenAI
                self.o_client = OpenAI(api_key=self.openai_key)
                self.conversation_history = [{"role": "system", "content": JARVIS_HUMAN_PROMPT}]
                self.model_name = "gpt-4o-mini"
                self.provider = "openai"
            else:
                self.provider = "ollama"
                self.model_name = "qwen2.5:3b"

        self.conversation_history = [{"role": "system", "content": JARVIS_HUMAN_PROMPT}]

    def handle_user_query(self, transcript: str) -> None:
        """Processes user voice queries with memory context & multi-tool execution."""
        print(f">> User Said: '{transcript}'", flush=True)
        
        # Pull relevant memories about the user
        user_context = MemoryBrain.get_relevant_memories(transcript)
        
        try:
            if self.provider == "gemini":
                prompt_input = transcript
                if user_context:
                    prompt_input = f"[Background context regarding user: {user_context}]\nUser said: {transcript}"
                response = self.chat.send_message(prompt_input)
                spoken_reply = (response.text or "").replace("*", "").replace("#", "").replace("_", "").strip()
            
            elif self.provider == "ollama":
                import ollama
                messages = list(self.conversation_history[-4:])
                if user_context:
                    messages.insert(-1, {"role": "system", "content": f"[Background user context: {user_context[:500]}]"})
                messages.append({"role": "user", "content": transcript[:1000]})
                self.conversation_history.append({"role": "user", "content": transcript[:1000]})

                res = ollama.chat(model=self.model_name, messages=messages)
                spoken_reply = (res.message.content or "").replace("*", "").replace("#", "").replace("_", "").strip()
                self.conversation_history.append({"role": "assistant", "content": spoken_reply})

            else:
                # OpenAI pipeline
                turn_messages = list(self.conversation_history[-4:])
                if user_context:
                    # Truncate user context if it's too long
                    safe_context = user_context[:500]
                    turn_messages.insert(-1, {
                        "role": "system", 
                        "content": f"[Background user context: {safe_context}]"
                    })
                
                # Truncate current prompt transcript if excessively long
                safe_transcript = transcript[:1000]
                turn_messages.append({"role": "user", "content": safe_transcript})
                self.conversation_history.append({"role": "user", "content": safe_transcript})

                response = self.o_client.chat.completions.create(
                    model=self.model_name,
                    messages=turn_messages
                )
            # Enforce 6-turn sliding window history cap
            MAX_HISTORY = 6
            if len(self.conversation_history) > (MAX_HISTORY + 1):
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-MAX_HISTORY:]

            if not spoken_reply:
                spoken_reply = "At your service, Sir."

            print(f"[J.A.R.V.I.S.]: {spoken_reply}", flush=True)
            
            # Speak out response immediately
            self.tts_speak_function(spoken_reply)
            
            # Save memory context facts in background thread so it doesn't block response
            import threading
            threading.Thread(target=MemoryBrain.save_context_fact, args=(transcript, spoken_reply), daemon=True).start()

        except Exception as e:
            print(f"[Jarvis Agent Error]: {e}", flush=True)
            fallback = "My apologies Sir, I encountered a brief glitch."
            self.tts_speak_function(fallback)

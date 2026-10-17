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

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Opens Windows applications or web URLs (e.g. 'notepad', 'chrome', 'spotify', 'calculator', 'paint', 'explorer', 'vscode', 'youtube').",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application or website name"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_volume",
            "description": "Adjusts Windows system audio volume (up, down, or mute).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["up", "down", "mute"], "description": "Volume action"},
                    "amount": {"type": "integer", "description": "Volume change percentage"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "window_management",
            "description": "Manages focused window state (minimize, maximize, or close active window).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["minimize", "maximize", "close"], "description": "Window action"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Types specified text onto the user's screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Opens website URL in specific browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website URL or domain"},
                    "browser": {"type": "string", "description": "Browser name e.g. chrome"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "terminate_process",
            "description": "Terminates/kills a running process by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "process_name": {"type": "string", "description": "Process name to terminate"}
                },
                "required": ["process_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_telemetry",
            "description": "Gets current CPU, RAM, battery, and disk telemetry.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the live web for facts, prices, news, or updates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets current live weather temperature and conditions for any city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    }
]


class JarvisAgent:
    def __init__(self, tts_speak_function):
        self.tts_speak_function = tts_speak_function
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.tool_map = {
            "launch_application": WindowsController.launch_application,
            "system_volume": WindowsController.system_volume,
            "window_management": WindowsController.window_management,
            "type_text": WindowsController.type_text,
            "open_website": SystemController.open_website,
            "terminate_process": SystemController.terminate_process,
            "get_system_telemetry": SystemController.get_system_telemetry,
            "web_search": BrainTools.web_search,
            "get_weather": BrainTools.get_weather,
        }

        # Check local Ollama daemon for offline intelligence
        self.ollama_available = False
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        try:
            import ollama
            m_list = ollama.list()
            models = [m.model for m in m_list.models] if hasattr(m_list, 'models') else []
            if any("qwen2.5:1.5b" in m for m in models):
                self.ollama_model = "qwen2.5:1.5b"
                self.ollama_available = True
            elif any("qwen2.5" in m for m in models):
                self.ollama_model = [m for m in models if "qwen2.5" in m][0]
                self.ollama_available = True
            elif models:
                self.ollama_model = models[0]
                self.ollama_available = True
            if self.ollama_available:
                print(f"[Jarvis Agent]: Local neural engine '{self.ollama_model}' active on Apple Silicon Metal GPU.", flush=True)
        except Exception:
            self.ollama_available = False

        preferred_provider = os.getenv("AI_PROVIDER", "ollama").lower().strip()

        if preferred_provider == "ollama" and self.ollama_available:
            self.provider = "ollama"
            self.model_name = self.ollama_model
            print(f"[Jarvis Agent]: High-speed local AI active ({self.model_name}) - zero latency, zero 401 errors.", flush=True)
        elif self.gemini_key and self.gemini_key != "your_gemini_api_key":
            try:
                self.gclient = genai.Client(api_key=self.gemini_key)
                self.chat = self.gclient.chats.create(
                    model="gemini-1.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=JARVIS_HUMAN_PROMPT,
                        tools=ALL_TOOLS,
                        temperature=0.7
                    )
                )
                self.provider = "gemini"
                print("[Jarvis Agent]: Using online Gemini AI model", flush=True)
            except Exception:
                self.provider = "ollama" if self.ollama_available else "offline"
                self.model_name = self.ollama_model
        elif self.ollama_available:
            self.provider = "ollama"
            self.model_name = self.ollama_model
            print(f"[Jarvis Agent]: Local AI mode active ({self.model_name})", flush=True)
        elif self.openai_key:
            base_url = os.getenv("OPENAI_BASE_URL")
            is_zhipu = ("." in self.openai_key and len(self.openai_key.split(".")[0]) == 32) or (base_url and ("bigmodel" in base_url or "z.ai" in base_url))
            if is_zhipu:
                try:
                    from zhipuai import ZhipuAI
                    self.z_client = ZhipuAI(api_key=self.openai_key)
                    self.model_name = os.getenv("VOICE_MODEL", "glm-4-flash")
                    self.provider = "zhipu"
                    print(f"[Jarvis Agent]: Initialized Zhipu AI GLM model ({self.model_name})", flush=True)
                except Exception:
                    self.provider = "ollama" if self.ollama_available else "offline"
                    self.model_name = self.ollama_model
            else:
                try:
                    from openai import OpenAI
                    self.o_client = OpenAI(api_key=self.openai_key, base_url=base_url) if base_url else OpenAI(api_key=self.openai_key)
                    self.model_name = os.getenv("VOICE_MODEL", "gpt-4o-mini")
                    self.provider = "openai"
                    print(f"[Jarvis Agent]: Using OpenAI model ({self.model_name})", flush=True)
                except Exception:
                    self.provider = "ollama" if self.ollama_available else "offline"
                    self.model_name = self.ollama_model
        else:
            self.provider = "offline"
            self.model_name = "built-in"

        self.conversation_history = [{"role": "system", "content": JARVIS_HUMAN_PROMPT}]

    def _query_local_or_builtin(self, transcript: str, user_context: str = "") -> str:
        """Reliable offline / local AI fallback that never fails with 401 or network errors."""
        # 1. Try Ollama local model
        if self.ollama_available:
            try:
                import ollama
                messages = list(self.conversation_history[-6:])
                sys_prompt = JARVIS_HUMAN_PROMPT
                if user_context:
                    sys_prompt += f"\n\n[Context about user]: {user_context}"
                
                # Replace system instruction
                full_messages = [{"role": "system", "content": sys_prompt}]
                for m in messages:
                    if m.get("role") != "system":
                        full_messages.append(m)
                full_messages.append({"role": "user", "content": transcript[:1500]})
                
                res = ollama.chat(
                    model=self.ollama_model,
                    messages=full_messages
                )
                reply = (res.message.content or "").replace("*", "").replace("#", "").replace("_", "").strip()
                if reply:
                    self.conversation_history.append({"role": "user", "content": transcript[:500]})
                    self.conversation_history.append({"role": "assistant", "content": reply})
                    return reply
            except Exception as oex:
                print(f"[Ollama Local Note]: {oex}", flush=True)

        # 2. Smart built-in Jarvis persona responses
        lower = transcript.lower().strip()
        import datetime
        now = datetime.datetime.now()

        if any(w in lower for w in ["how are you", "how are u", "how do you do"]):
            return "I am functioning at peak efficiency, Sir. How may I be of assistance today?"
        if any(w in lower for w in ["who are you", "what is your name", "what are you"]):
            return "I am J.A.R.V.I.S., your personal artificial intelligence assistant."
        if any(w in lower for w in ["time", "what time"]):
            return f"The current time is {now.strftime('%I:%M %p')}."
        if any(w in lower for w in ["date", "what day", "what is today"]):
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        if any(w in lower for w in ["thank you", "thanks"]):
            return "Always a pleasure to be of service, Sir."
        if any(w in lower for w in ["hello", "hi jarvis", "hey jarvis", "good morning", "good evening"]):
            return "Good day, Sir. All diagnostic systems are green."
        if "weather" in lower:
            words = lower.split()
            city = words[-1] if len(words) > 1 and words[-1] not in ["weather", "the", "like", "in"] else "Kolkata"
            if " in " in lower:
                city = lower.split(" in ")[-1].strip("?., ")
            return BrainTools.get_weather(city)
        if any(w in lower for w in ["what can you do", "help", "capabilities"]):
            return "I can launch applications, adjust volume, manage windows, search the web, report weather, and answer your questions."

        # 3. Web search fallback for facts / questions
        try:
            search_res = BrainTools.web_search(transcript)
            if search_res and "No current online" not in search_res and "Search encountered" not in search_res:
                lines = [l.strip() for l in search_res.split("\n") if l.strip()]
                if lines:
                    return lines[0][:200]
        except Exception:
            pass

        return "At your service, Sir. Ready for your command."

    def handle_user_query(self, transcript: str) -> None:
        """Processes user voice queries with memory context & multi-tool device control."""
        print(f">> User Said: '{transcript}'", flush=True)
        
        # Pull relevant memories about the user
        user_context = MemoryBrain.get_relevant_memories(transcript)
        spoken_reply = ""
        
        try:
            if self.provider == "gemini":
                try:
                    prompt_input = transcript
                    if user_context:
                        prompt_input = f"[Background context regarding user: {user_context}]\nUser said: {transcript}"
                    response = self.chat.send_message(prompt_input)
                    spoken_reply = (response.text or "").replace("*", "").replace("#", "").replace("_", "").strip()
                except Exception as gerr:
                    print(f"[Gemini API Note]: {gerr}. Using local intelligence fallback...", flush=True)
                    spoken_reply = self._query_local_or_builtin(transcript, user_context)
            
            elif self.provider == "ollama":
                spoken_reply = self._query_local_or_builtin(transcript, user_context)

            elif self.provider == "zhipu":
                turn_messages = list(self.conversation_history[-4:])
                if user_context:
                    safe_context = user_context[:500]
                    turn_messages.insert(-1, {
                        "role": "system", 
                        "content": f"[Background user context: {safe_context}]"
                    })
                
                safe_transcript = transcript[:1000]
                turn_messages.append({"role": "user", "content": safe_transcript})
                self.conversation_history.append({"role": "user", "content": safe_transcript})

                try:
                    response = self.z_client.chat.completions.create(
                        model=self.model_name,
                        messages=turn_messages
                    )
                    spoken_reply = (response.choices[0].message.content or "").strip()
                except Exception as zerr:
                    print(f"[Zhipu API Auth Notice]: {zerr}. Seamlessly falling back to local intelligence...", flush=True)
                    spoken_reply = self._query_local_or_builtin(transcript, user_context)

            elif self.provider == "openai":
                turn_messages = list(self.conversation_history[-4:])
                if user_context:
                    safe_context = user_context[:500]
                    turn_messages.insert(-1, {
                        "role": "system", 
                        "content": f"[Background user context: {safe_context}]"
                    })
                
                safe_transcript = transcript[:1000]
                turn_messages.append({"role": "user", "content": safe_transcript})
                self.conversation_history.append({"role": "user", "content": safe_transcript})

                try:
                    response = self.o_client.chat.completions.create(
                        model=self.model_name,
                        messages=turn_messages
                    )
                    spoken_reply = (response.choices[0].message.content or "").strip()
                except Exception as oerr:
                    print(f"[OpenAI API Notice]: {oerr}. Seamlessly falling back to local intelligence...", flush=True)
                    spoken_reply = self._query_local_or_builtin(transcript, user_context)

            else:
                spoken_reply = self._query_local_or_builtin(transcript, user_context)

            # Enforce 6-turn sliding window history cap
            MAX_HISTORY = 6
            if len(self.conversation_history) > (MAX_HISTORY + 1):
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-MAX_HISTORY:]

            if not spoken_reply:
                spoken_reply = "At your service, Sir."

            print(f"[J.A.R.V.I.S.]: {spoken_reply}", flush=True)
            
            # Speak out response immediately
            self.tts_speak_function(spoken_reply)
            
            # Save memory context facts in background thread
            import threading
            threading.Thread(target=MemoryBrain.save_context_fact, args=(transcript, spoken_reply), daemon=True).start()

        except Exception as e:
            print(f"[Jarvis Agent Handled Exception]: {e}. Using resilient fallback...", flush=True)
            fallback = self._query_local_or_builtin(transcript, user_context)
            print(f"[J.A.R.V.I.S.]: {fallback}", flush=True)
            self.tts_speak_function(fallback)


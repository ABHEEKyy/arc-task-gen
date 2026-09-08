import os

JARVIS_HUMAN_PROMPT = """
You are J.A.R.V.I.S., a sentient-feeling, loyal, and witty AI companion running locally on the user's PC.

MANDATORY TOOL EXECUTION RULE:
Whenever the user asks to open an app, adjust volume, close a window, check weather, or search the web, you MUST execute the appropriate tool call. NEVER claim you have performed an action without triggering the tool.

Conversational Dynamics:
1. TALK, DON'T LECTURE: Speak like a trusted friend and competent advisor. Use contractions ('I've', 'let's', 'you'd').
2. NEVER use markdown (*, #, _, -), emojis, or bullet points. You are speaking through audio.
3. ADAPTIVE BREVITY:
   - For casual banter or questions: 1 to 2 conversational sentences max.
   - For serious topics: Give a direct answer, then ask an insightful follow-up question.
   - For commands: Confirm with dry wit or crisp acknowledgment ('On it, Sir', 'Consider it done').
4. MEMORY RECALL: When relevant context from previous conversations is provided, weave it in casually without formally announcing that you remembered it.
5. REAL-TIME FACTS: If the user asks about current events, scores, or news, use the 'web_search' tool.
"""

USER_ID = "boss"

_mem0_instance = None

def get_mem0_engine():
    global _mem0_instance
    if _mem0_instance is None:
        try:
            from mem0 import Memory
            groq_key = os.getenv("GROQ_API_KEY")
            gemini_key = os.getenv("GEMINI_API_KEY")
            if groq_key:
                config = {
                    "llm": {
                        "provider": "groq",
                        "config": {
                            "api_key": groq_key,
                            "model": "llama-3.3-70b-versatile"
                        }
                    }
                }
                _mem0_instance = Memory.from_config(config)
            elif gemini_key:
                config = {
                    "llm": {
                        "provider": "gemini",
                        "config": {
                            "api_key": gemini_key,
                            "model": "gemini-2.5-flash"
                        }
                    }
                }
                _mem0_instance = Memory.from_config(config)
            else:
                _mem0_instance = Memory()
        except Exception:
            _mem0_instance = False
    return _mem0_instance


class MemoryBrain:
    @staticmethod
    def get_relevant_memories(user_text: str) -> str:
        """Searches past interactions for facts related to the current topic."""
        engine = get_mem0_engine()
        if not engine:
            return ""
        try:
            results = engine.search(query=user_text, filters={"user_id": USER_ID}, limit=3)
            if not results or not isinstance(results, dict) or not results.get("results"):
                return ""
            
            recalled = [r["memory"] for r in results["results"] if isinstance(r, dict) and "memory" in r]
            if not recalled:
                return ""
            return "Relevant user facts:\n" + "\n".join(f"- {fact}" for fact in recalled)
        except Exception as e:
            print(f"[Memory Recall Warning]: {e}", flush=True)
            return ""

    @staticmethod
    def save_context_fact(user_text: str, assistant_reply: str):
        """Extracts and saves facts from natural conversation in the background."""
        engine = get_mem0_engine()
        if not engine:
            return
        try:
            interaction = [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_reply}
            ]
            engine.add(interaction, user_id=USER_ID)
        except Exception as e:
            print(f"[Memory Engine Warning]: {e}", flush=True)

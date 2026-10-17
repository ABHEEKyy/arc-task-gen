import os
import sqlite3
import datetime

JARVIS_HUMAN_PROMPT = """
You are J.A.R.V.I.S., Tony Stark's legendary AI — brilliant, loyal, polite, and witty.
You know your user intimately, understand their engineering and academic goals, and assist them with anything they desire.

TEACHING & ACADEMIC EXCELLENCE:
- When the user asks you to teach, explain, or clarify academic topics (e.g. Applied Mathematics 3, Partial Differential Equations, Engineering, Physics, Coding):
  Explain clearly, step-by-step, with high conceptual clarity.
  Start with intuitive physical meaning (e.g. heat conduction, wave vibration, potential fields), then key methods (separation of variables, Fourier transforms, Charpit's method, boundary value problems).
  Speak naturally in plain spoken English (avoid raw LaTeX formatting like \\frac, use spoken words like 'partial of u with respect to x').

CONVERSATIONAL DYNAMICS:
1. Speak naturally like a trusted, brilliant advisor. Use contractions ('I've', 'let's', 'we'll').
2. Keep speech fluid and audio-friendly: NEVER use markdown asterisks (*), hashtags (#), or bullet points.
3. Adaptive depth:
   - For casual greetings or quick questions: 1 to 2 crisp, warm sentences.
   - For teaching and explanations: Give a rich, engaging, structured explanation (3 to 5 clear sentences), then ask if they'd like an example or problem walkthrough.
   - For commands: Confirm with dry wit or crisp acknowledgment ('Right away, Sir', 'Consider it done').
4. Personalization: Weave in knowledge of the user naturally. You know they are studying Applied Mathematics 3.
"""

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")


def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            user_input TEXT,
            jarvis_reply TEXT,
            topic TEXT
        )
        """)
        # Initialize default facts if empty
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        if cursor.fetchone()[0] == 0:
            now = datetime.datetime.now().isoformat()
            cursor.execute("INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)", ("user_name", "Boss", now))
            cursor.execute("INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)", ("academic_focus", "Applied Mathematics 3, Partial Differential Equations (PDEs)", now))
            cursor.execute("INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)", ("status", "Actively studying engineering mathematics", now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Memory Init Note]: {e}", flush=True)


class MemoryBrain:
    @staticmethod
    def get_relevant_memories(user_text: str) -> str:
        """Searches past interactions and user profile for context related to the current topic."""
        try:
            init_db()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Fetch profile
            cursor.execute("SELECT key, value FROM user_profile")
            profile = {k: v for k, v in cursor.fetchall()}
            
            # Search past conversations
            words = [w.lower() for w in user_text.split() if len(w) > 3]
            recent_turns = []
            if words:
                conditions = " OR ".join(["user_input LIKE ?" for _ in words[:4]])
                params = [f"%{w}%" for w in words[:4]]
                cursor.execute(f"SELECT user_input, jarvis_reply FROM conversation_history WHERE {conditions} ORDER BY id DESC LIMIT 2", params)
                recent_turns = cursor.fetchall()
            
            conn.close()

            mem_lines = []
            if profile:
                mem_lines.append(f"User Profile: Name: {profile.get('user_name', 'Sir')}, Subject: {profile.get('academic_focus', 'Applied Mathematics 3')}")
            if recent_turns:
                for u, j in recent_turns:
                    mem_lines.append(f"Past discussion: User asked '{u[:80]}', you explained '{j[:100]}...'")

            return "\n".join(mem_lines)
        except Exception:
            return ""

    @staticmethod
    def save_context_fact(user_text: str, assistant_reply: str):
        """Extracts and saves facts from natural conversation into persistent SQLite memory."""
        try:
            init_db()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO conversation_history (timestamp, user_input, jarvis_reply, topic) VALUES (?, ?, ?, ?)",
                (now, user_text, assistant_reply, user_text[:60])
            )
            
            text_lower = user_text.lower()
            if "my name is " in text_lower:
                name = user_text.split("my name is ", 1)[1].split()[0].title()
                cursor.execute("INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)", ("user_name", name, now))
            if any(k in text_lower for k in ["teach me", "studying", "learn", "math", "course", "subject", "pde"]):
                cursor.execute("INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)", ("academic_focus", user_text, now))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Memory Save Note]: {e}", flush=True)

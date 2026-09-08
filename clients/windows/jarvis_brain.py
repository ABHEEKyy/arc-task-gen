import json
import requests

class BrainTools:
    @staticmethod
    def web_search(query: str) -> str:
        """Searches the live web for recent news, scores, facts, and updates."""
        try:
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=3))
            except Exception:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=3))

            if not results:
                return "No current online results found."
            snippets = [f"{r['title']}: {r.get('body', '')}" for r in results]
            return "\n".join(snippets)
        except Exception as e:
            return f"Search encountered an issue: {str(e)}"

    @staticmethod
    def get_weather(city: str) -> str:
        """Fetches current real-time temperature and conditions for any city."""
        try:
            geo = requests.get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            ).json()
            if not geo.get("results"):
                return f"Could not find coordinates for {city}."
            loc = geo["results"][0]
            lat, lon, name = loc["latitude"], loc["longitude"], loc["name"]
            
            w = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            ).json()
            curr = w.get("current_weather", {})
            temp_c = curr.get("temperature")
            wind = curr.get("windspeed")
            return f"Current temperature in {name} is {temp_c}°C with wind speeds around {wind} km/h."
        except Exception as e:
            return f"Weather lookup failed: {str(e)}"

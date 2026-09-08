"""Small, voice-friendly real-time web and weather lookups."""

from __future__ import annotations

from urllib.parse import quote

import requests

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

REQUEST_TIMEOUT = 8
WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "thunderstorms with hail",
}


class RealtimeTools:
    @staticmethod
    def web_search(query: str) -> str:
        """Return a few current web snippets without exposing raw URLs to speech."""
        if not query.strip():
            return "A search query is required."
        try:
            with DDGS() as search:
                results = list(search.text(query.strip(), max_results=3))
            if not results:
                return "No web results found."
            summaries = []
            for result in results:
                title = result.get("title", "Untitled")
                body = result.get("body", "No summary available")
                summaries.append(f"{title}: {body}")
            return "\n".join(summaries)
        except Exception as error:
            return f"Web search error: {error}"

    @staticmethod
    def get_weather(city: str) -> str:
        """Return current conditions and today's high and low from Open-Meteo."""
        if not city.strip():
            return "A city is required."
        try:
            geo_response = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city.strip(), "count": 1, "language": "en", "format": "json"},
                timeout=REQUEST_TIMEOUT,
            )
            geo_response.raise_for_status()
            locations = geo_response.json().get("results", [])
            if not locations:
                return f"Could not locate {city}."
            location = locations[0]
            forecast_response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
                timeout=REQUEST_TIMEOUT,
            )
            forecast_response.raise_for_status()
            forecast = forecast_response.json()
            current = forecast["current"]
            daily = forecast["daily"]
            condition = WEATHER_CODES.get(current.get("weather_code"), "mixed conditions")
            name = location.get("name", city)
            region = location.get("country", "")
            return (
                f"In {name}, {region}, it is {current['temperature_2m']:.0f} degrees Fahrenheit and {condition}, "
                f"with {current['relative_humidity_2m']} percent humidity and wind at {current['wind_speed_10m']:.0f} miles per hour. "
                f"Today's high is {daily['temperature_2m_max'][0]:.0f} and low is {daily['temperature_2m_min'][0]:.0f}."
            )
        except (KeyError, TypeError, ValueError, requests.RequestException) as error:
            return f"Weather lookup error: {error}"
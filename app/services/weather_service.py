import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(city: str) -> dict:
    """
    Fetch current weather using Open-Meteo (no API key required).
    Step 1: Geocode city name → lat/lon
    Step 2: Fetch weather from coordinates
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1: Geocode
        geo_resp = await client.get(GEOCODING_URL, params={"name": city, "count": 1, "language": "vi"})
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            raise ValueError(f"City '{city}' not found")

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        country = location.get("country", "")
        city_name = location.get("name", city)

        # Step 2: Fetch weather
        weather_resp = await client.get(WEATHER_URL, params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "timezone": "auto",
        })
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

    current = weather_data["current"]

    return {
        "city": city_name,
        "country": country,
        "temperature": current["temperature_2m"],
        "feels_like": current["apparent_temperature"],
        "humidity": current["relative_humidity_2m"],
        "description": _weather_code_to_description(current["weather_code"]),
        "wind_speed": current["wind_speed_10m"],
    }


def _weather_code_to_description(code: int) -> str:
    codes = {
        0: "Trời quang",
        1: "Chủ yếu quang đãng", 2: "Có mây rải rác", 3: "Nhiều mây",
        45: "Sương mù", 48: "Sương mù có băng",
        51: "Mưa phùn nhẹ", 53: "Mưa phùn vừa", 55: "Mưa phùn dày",
        61: "Mưa nhẹ", 63: "Mưa vừa", 65: "Mưa to",
        71: "Tuyết nhẹ", 73: "Tuyết vừa", 75: "Tuyết dày",
        80: "Mưa rào nhẹ", 81: "Mưa rào vừa", 82: "Mưa rào to",
        95: "Dông", 96: "Dông có mưa đá nhẹ", 99: "Dông có mưa đá to",
    }
    return codes.get(code, f"Mã thời tiết: {code}")

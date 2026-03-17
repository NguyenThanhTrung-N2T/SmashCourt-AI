from app.models.weather_schemas import WeatherResponse
from app.services.weather_service import get_weather
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/weather/{city}", response_model=WeatherResponse)
async def weather(city: str):
    """
    Get current weather for a city.
    Example: /api/v1/weather/Hanoi
    """
    try:
        return await get_weather(city)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

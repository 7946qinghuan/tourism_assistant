"""
WeatherProvider - 天气查询工具
支持中英文地址输入，自动地理编码，返回 Pydantic 定义的天气数据结构
"""

from datetime import date, datetime, timedelta

import requests
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer
from pydantic import BaseModel, Field


class Temperature(BaseModel):
    """温度类"""

    max: float = Field(..., description="最高气温 (°C)")
    min: float = Field(..., description="最低气温 (°C)")
    mean: float = Field(..., description="平均气温 (°C)")
    apparent_max: float = Field(..., description="体感最高温度 (°C)")
    apparent_min: float = Field(..., description="体感最低温度 (°C)")


class Precipitation(BaseModel):
    """水分与降水类"""

    probability_max: float | None = Field(None, description="最大降水概率 (0~100%)")
    hours: float = Field(..., description="降水时长 (小时)")
    snowfall_sum: float = Field(..., description="降雪量 (cm)")
    shortwave_radiation_sum: float = Field(..., description="太阳短波辐射总量 (MJ/m²)")


class SunLight(BaseModel):
    """日出日落与光照类"""

    sunrise: str = Field(..., description="日出时间 (ISO8601)")
    sunset: str = Field(..., description="日落时间 (ISO8601)")
    daylight_duration: float = Field(..., description="白昼时长 (秒)")
    uv_index_max: float = Field(..., description="最大紫外线指数")


class Wind(BaseModel):
    """风与压力类"""

    speed_max: float = Field(..., description="最大风速 (km/h)")
    gusts_max: float = Field(..., description="最大阵风 (km/h)")
    direction_dominant: float = Field(..., description="主导风向 (0~360°)")


class DailyWeather(BaseModel):
    """单日天气信息"""

    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    weather_desc: str = Field(..., description="天气描述（中文）")
    weather_code: int = Field(..., description="WMO 天气代码")
    temperature: Temperature
    precipitation: Precipitation
    sun_light: SunLight
    wind: Wind


class WeatherResult(BaseModel):
    """完整查询结果"""

    location: str = Field(..., description="查询地址")
    latitude: float
    longitude: float
    timezone: str
    start_date: str
    end_date: str
    daily: list[DailyWeather]


def geocode(address: str) -> dict:
    """
    将中英文地址转换为经纬度坐标
    使用 Open-Meteo 免费 Geocoding API（支持中英文城市名）
    返回: {"name": ..., "lat": ..., "lon": ..., "timezone": ...}
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": address,
        "count": 1,
        "language": "zh",  # 返回中文地名（不影响搜索语言）
        "format": "json",
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results")
    if not results:
        raise ValueError(f"无法解析地址：{address}，请检查拼写或尝试更具体的地名")

    r = results[0]
    return {
        "name": r.get("name", address),
        "lat": r["latitude"],
        "lon": r["longitude"],
        "timezone": r.get("timezone", "Asia/Shanghai"),
    }


WMO_DESC = {
    0: "晴朗",
    1: "大部晴朗",
    2: "晴间多云",
    3: "阴天",
    45: "雾",
    48: "雾凇",
    51: "轻微毛毛雨",
    53: "中等毛毛雨",
    55: "浓密毛毛雨",
    56: "轻微冻毛毛雨",
    57: "浓密冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻微冻雨",
    67: "大量冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷阵雨",
    96: "伴有小冰雹的雷阵雨",
    99: "伴有大冰雹的雷阵雨",
}


def get_weather_desc(code: int) -> str:
    return WMO_DESC.get(code, f"未知天气({code})")


@MCPServer()
class OpenMeteoWeatherToolkit(BaseToolkit):
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    MAX_FORECAST_DAYS = 16

    def fetch_forecast(
        self,
        address: str,
        start_date_str: str,
        end_date_str: str,
    ) -> WeatherResult:
        """
        查询天气预报

        :param address:        中文或英文地址，如 "成都"、"Tokyo"、"New York"
        :param start_date_str: 开始日期，格式 "YYYY-MM-DD"（不早于今天）
        :param end_date_str:   结束日期，格式 "YYYY-MM-DD"（最多今天起16天内）
        :return:               WeatherResult Pydantic 对象
        :raises ValueError:    地址解析失败 / 日期范围非法
        :raises RuntimeError:  API 请求失败
        """
        # ── 步骤1：地理编码 ──
        geo = geocode(address)

        # ── 步骤2：日期范围校验 & 截断 ──
        today = date.today()
        max_end = today + timedelta(days=self.MAX_FORECAST_DAYS - 1)

        req_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        req_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if req_start > req_end:
            raise ValueError("开始日期不能晚于结束日期")

        final_start = max(today, req_start)
        final_end = min(max_end, req_end)

        if final_start > final_end:
            raise ValueError(
                f"日期超出可查询范围（今天：{today}，最远可查：{max_end}）"
            )

        # ── 步骤3：调用 Open-Meteo Forecast API ──
        params = {
            "latitude": geo["lat"],
            "longitude": geo["lon"],
            "start_date": final_start.isoformat(),
            "end_date": final_end.isoformat(),
            "timezone": geo["timezone"],
            "daily": [
                # 温度
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "apparent_temperature_max",
                "apparent_temperature_min",
                # 降水
                "precipitation_probability_max",
                "precipitation_hours",
                "snowfall_sum",
                "shortwave_radiation_sum",
                # 日出日落
                "sunrise",
                "sunset",
                "daylight_duration",
                "uv_index_max",
                # 风
                "windspeed_10m_max",
                "windgusts_10m_max",
                "winddirection_10m_dominant",
                # 天气代码
                "weathercode",
            ],
        }

        try:
            resp = requests.get(self.FORECAST_URL, params=params, timeout=15)
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"天气 API 请求失败：{e}") from e

        # ── 步骤4：解析并组装 Pydantic 对象 ──
        d = raw.get("daily", {})
        days = []
        for i, date_str in enumerate(d.get("time", [])):
            days.append(
                DailyWeather(
                    date=date_str,
                    weather_code=d["weathercode"][i],
                    weather_desc=get_weather_desc(d["weathercode"][i]),
                    temperature=Temperature(
                        max=d["temperature_2m_max"][i],
                        min=d["temperature_2m_min"][i],
                        mean=d["temperature_2m_mean"][i],
                        apparent_max=d["apparent_temperature_max"][i],
                        apparent_min=d["apparent_temperature_min"][i],
                    ),
                    precipitation=Precipitation(
                        probability_max=d.get("precipitation_probability_max", [None])[
                            i
                        ],
                        hours=d["precipitation_hours"][i],
                        snowfall_sum=d["snowfall_sum"][i],
                        shortwave_radiation_sum=d["shortwave_radiation_sum"][i],
                    ),
                    sun_light=SunLight(
                        sunrise=d["sunrise"][i],
                        sunset=d["sunset"][i],
                        daylight_duration=d["daylight_duration"][i],
                        uv_index_max=d["uv_index_max"][i],
                    ),
                    wind=Wind(
                        speed_max=d["windspeed_10m_max"][i],
                        gusts_max=d["windgusts_10m_max"][i],
                        direction_dominant=d["winddirection_10m_dominant"][i],
                    ),
                )
            )

        return WeatherResult(
            location=geo["name"],
            latitude=geo["lat"],
            longitude=geo["lon"],
            timezone=geo["timezone"],
            start_date=final_start.isoformat(),
            end_date=final_end.isoformat(),
            daily=days,
        )

    def get_tools(self) -> list[FunctionTool]:
        return [
            FunctionTool(self.fetch_forecast),
        ]

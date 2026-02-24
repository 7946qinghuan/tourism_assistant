from pydantic import BaseModel, Field

from ..toolkits.open_meteo_weather_toolkit import WeatherResult


class TripRequest(BaseModel):
    """旅行规划请求"""

    city: str = Field(..., description="目的地城市", examples=["北京"])
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", examples=["2025-06-01"])
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD", examples=["2025-06-03"])
    travel_days: int = Field(..., description="旅行天数", ge=1, le=30, examples=[3])
    transportation: str = Field(..., description="交通方式", examples=["公共交通"])
    accommodation: str = Field(..., description="住宿偏好", examples=["经济型酒店"])
    preferences: list[str] = Field(default=[], description="旅行偏好标签", examples=["历史文化", "美食"])
    free_text_input: str | None = Field(default="", description="额外要求", examples=["希望多安排一些博物馆"])

    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京",
                "start_date": "2025-06-01",
                "end_date": "2025-06-03",
                "travel_days": 3,
                "transportation": "公共交通",
                "accommodation": "经济型酒店",
                "preferences": ["历史文化", "美食"],
                "free_text_input": "希望多安排一些博物馆",
            }
        }


class AttractionSearchdata(BaseModel):
    id: str = Field(description="景点ID")
    name: str = Field(description="单个景点名称")
    address: str = Field(description="单个景点地址")
    photo_url: str = Field(description="单个景点照片URL")
    typecode: str = Field(description="景点类型编码")


class AttractionSearchResponse(BaseModel):
    attractions: list[AttractionSearchdata] = Field(description="多个景点搜索结果")


class WeatherSearchdata(BaseModel):
    data: str = Field(description="当前日期")
    weak: str = Field(description="当前日期对应的星期数")
    dayweather: str = Field(description="当前日期白天的天气描述")
    nightweather: str = Field(description="当前日期晚上的天气描述")
    daytemp_float: float = Field(description="当前日期白天的温度")
    nighttemp_float: float = Field(description="当前日期晚上的温度")
    daywind: str = Field(description="当前日期白天的风力方向")
    nightwind: str = Field(description="当前日期晚上的风力方向")
    daypower: str = Field(description="当前日期白天的风力大小")
    nightpower: str = Field(description="当前日期晚上的风力大小")


class WeatherSearchResponse(BaseModel):
    weather: list[WeatherSearchdata] = Field(description="多个日期天气搜索结果")


class HotelSearchdata(BaseModel):
    id: str = Field(description="酒店ID")
    name: str = Field(description="酒店名称")
    address: str = Field(description="酒店地址")
    photo_url: str = Field(description="酒店照片URL")
    typecode: str = Field(description="酒店类型编码")


class HotelSearchResponse(BaseModel):
    hotels: list[HotelSearchdata] = Field(description="多个酒店搜索结果")


class TripPlanStep(BaseModel):
    """旅行规划步骤"""

    date: int = Field(description="行程日期")
    day_index: int = Field(description="行程日期索引")
    description: str = Field(description="行程描述")
    transportation: str = Field(description="交通方式")
    accommodation: str = Field(description="住宿类型")
    hotel: HotelSearchdata = Field(description="住宿酒店")
    attractions: list[AttractionSearchdata] = Field(description="景点信息列表")


class TripPlanResponse(BaseModel):
    """旅行规划响应"""

    city: str = Field(description="目的地城市")
    start_date: str = Field(description="开始日期 YYYY-MM-DD")
    end_date: str = Field(description="结束日期 YYYY-MM-DD")
    weather_info: WeatherResult = Field(description="天气信息")
    hotel_info: list[HotelSearchdata] = Field(description="酒店信息")
    attraction_info: list[AttractionSearchdata] = Field(description="景点信息")
    trip_plan: list[TripPlanStep] = Field(description="旅行规划步骤")
    extra_info: str = Field(description="额外补充信息")

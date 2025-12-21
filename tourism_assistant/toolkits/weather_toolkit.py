import json
import os
from typing import cast

import httpx
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv(verbose=True, override=True)


class WeatherLives(BaseModel):
    """实时天气模型（对应 forecasts=False 时的 lives 字段）"""

    province: str = Field(description="省份")
    city: str = Field(description="城市名")
    adcode: str = Field(description="行政区划代码")
    weather: str = Field(description="天气状况")
    temperature: int = Field(description="温度（整数）")
    winddirection: str = Field(description="风向")
    windpower: str = Field(description="风力")
    humidity: int = Field(description="湿度（整数）")
    reporttime: str = Field(description="数据发布时间")
    temperature_float: float = Field(description="温度（浮点型）")
    humidity_float: float = Field(description="湿度（浮点型）")

    def __str__(self):
        return (
            f"=========================================\n"
            f"🌡️ {self.province}省{self.city} 实时天气\n"
            f"📍 行政区划代码：{self.adcode}\n"
            f"⏰ 更新时间：{self.reporttime}\n"
            f"=========================================\n"
            f"  🌤️ 天气：{self.weather}\n"
            f"  🌡️ 温度：{self.temperature}°C\n"
            f"  🌬️ 风向：{self.winddirection}\n"
            f"  💨 风力：{self.windpower}级\n"
            f"  💧 湿度：{self.humidity}%\n"
        )


class Casts(BaseModel):
    """单天预报模型（对应 forecasts=True 时的 casts 子字段）"""

    date: str = Field(description="预报日期（格式：YYYY-MM-DD）")
    week: int = Field(description="星期（1=周一，7=周日）")  # API 返回字符串，Pydantic 自动转 int
    dayweather: str = Field(description="白天天气")
    nightweather: str = Field(description="夜间天气")
    daytemp: int = Field(description="白天温度（整数）")  # API 返回字符串，自动转 int
    nighttemp: int = Field(description="夜间温度（整数）")
    daywind: str = Field(description="白天风向")
    nightwind: str = Field(description="夜间风向")
    daypower: str = Field(description="白天风力")
    nightpower: str = Field(description="夜间风力")
    daytemp_float: float = Field(description="白天温度（浮点型）")
    nighttemp_float: float = Field(description="夜间温度（浮点型）")

    def __str__(self):
        # 星期数字转中文（1→一，2→二...）
        week_map = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}
        return (
            f"📅 日期：{self.date}（周{week_map.get(self.week, self.week)}）\n"
            f"  🌞 白天：{self.dayweather} | 温度：{self.daytemp}°C | 风向：{self.daywind} | 风力：{self.daypower}\n"
            f"  🌙 夜间：{self.nightweather} | 温度：{self.nighttemp}°C | 风向：{self.nightwind} | 风力：{self.nightpower}\n"
        )


class WeatherForecast(BaseModel):
    """预报天气模型（对应 forecasts=True 时的 forecasts 字段）"""

    province: str = Field(description="省份")
    city: str = Field(description="城市名")
    adcode: str = Field(description="行政区划代码")
    reporttime: str = Field(description="预报发布时间")
    casts: list[Casts] = Field(description="未来4天预报列表")  # 嵌套 Casts 模型列表

    def __str__(self):
        # 拼接所有单天预报的字符串
        casts_str = "\n".join(str(cast) for cast in self.casts)
        return (
            f"=========================================\n"
            f"🌤️ {self.province}省{self.city} 未来4天天气预报\n"
            f"📍 行政区划代码：{self.adcode}\n"
            f"⏰ 发布时间：{self.reporttime}\n"
            f"=========================================\n"
            f"{casts_str}"
        )


@MCPServer()
class WeatherQueryToolkit(BaseToolkit):
    r"""
    A toolkit for querying weather information from the Gaode Weather API.
    """

    def __init__(
        self,
        timeout: int = 60,
    ):
        """
        Initializes the WeatherQueryToolkit with the specified timeout.

        Args:
            timeout (int, optional): The timeout duration for HTTP requests in seconds. Defaults to 60.
        """
        self.timeout = timeout
        self.base_url = os.getenv("GAODEWEATHER_WEATHER_BASE_URL")
        if not self.base_url:
            raise ValueError(
                "环境变量中未找到 `GAODEWEATHER_WEATHER_BASE_URL`（高德天气 API 基础 URL）。\n"
                "请在 .env 文件中添加 GAODEWEATHER_WEATHER_BASE_URL 环境变量。\n"
                "GAODEWEATHER_WEATHER_BASE_URL=https://restapi.amap.com/v3/weather/weatherInfo"
            )

        self.api_key = os.getenv("GAODEWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "环境变量中未找到 `GAODEWEATHER_API_KEY`（高德天气 API 密钥）。\n"
                "获取步骤如下：\n"
                "1. 访问高德开放平台 API 密钥创建页面：https://lbs.amap.com/api/webservice/create-project-and-key \n"
                "2. 需先注册并登录高德开放平台账号（支持手机号/第三方账号登录）；\n"
                "3. 进入【应用管理】，点击页面右上角【创建新应用】，填写表单即可创建新的应用。\n"
                "4. 进入【应用管理】，在我的应用中选择需要创建 Key 的应用，点击【添加 Key】，表单中的服务平台选择【Web 服务】。\n"
                "5. 创建成功后，可获取 Key 和安全密钥。"
            )
        self.client = httpx.Client(timeout=self.timeout)

    async def close(self):
        """关闭 httpx.AsyncClient 客户端"""
        self.client.close()

    def _build_weather_api_request_params(self, city: str, extensions: str, output: str) -> dict:
        params = {
            "key": self.api_key,
            "city": city,
            "extensions": extensions,
            "output": output,
        }
        return params

    def _parse_weather_response(
        self, response_json: dict, forecasts: bool
    ) -> WeatherLives | WeatherForecast:  # 修改返回类型：支持两种模型
        status = response_json.get("status")
        info = response_json.get("info", "无错误信息")
        if status != "1":
            raise ValueError(f"高德天气 API 调用失败：状态码 {status}，错误信息：{info}")

        try:
            if forecasts:
                # 分支1：处理预报数据（forecasts=True）
                forecasts_data_list = response_json.get("forecasts")
                if not isinstance(forecasts_data_list, list) or not forecasts_data_list:
                    raise ValueError(f"API 未返回有效的 'forecasts' 列表，原始响应：{response_json}")
                forecasts_data = forecasts_data_list[0]  # 取第一个预报（通常一个城市对应一条）
                return WeatherForecast.model_validate(forecasts_data)  # 解析为预报模型

            else:
                # 分支2：处理实时数据（forecasts=False，保持原有逻辑并完善）
                lives_data_list = response_json.get("lives")
                if not isinstance(lives_data_list, list) or not lives_data_list:
                    raise ValueError(f"API 未返回有效的 'lives' 列表，原始响应：{response_json}")
                lives_data = lives_data_list[0]
                return WeatherLives.model_validate(lives_data)  # 解析为实时天气模型

        except ValidationError as e:
            # 优化错误信息：明确是哪种数据解析失败
            data_type = "预报" if forecasts else "实时"
            raw_data = forecasts_data if forecasts else lives_data
            error_details = e.errors()
            raise RuntimeError(
                f"{data_type}天气数据解析失败：字段校验不通过。\n错误详情：{error_details}\n原始数据：{raw_data}"
            ) from e  # 保留原始异常栈，便于调试

    def fetch_weather_from_api(
        self, city: str, extensions: str = "base", output: str = "JSON"
    ) -> WeatherLives | WeatherForecast:
        r"""
            Fetches weather data from the Gaode Weather API for the specified city.

        Args:
            city (str): The name of the city to fetch weather data for.例如："成都"
            extensions (str, optional): The type of weather data to fetch.
                Defaults to "base".
                Value Explanation:
                - "base": Obtain real-time weather information. This is applicable when users inquire about "the current weather" or "the present weather" and other immediate weather conditions.
                - "all": Obtain the weather forecast for the next 4 days (including today), applicable to user inquiries such as "recent weather", "weather in the coming days", "weather forecast", etc.
            output (str, optional): The format of the API response. Defaults to "JSON".
                Options are: "JSON", "XML".

        Returns:
            Union[WeatherLives, WeatherForecast]: The parsed weather data, either
                a WeatherLives object for real-time data or a WeatherForecast object
                for forecast data.

        Raises:
            ValueError: If the API response status is not "1" (success).
            RuntimeError: If there are issues with the HTTP request, JSON parsing,
                or data validation.
        """
        params = self._build_weather_api_request_params(city, extensions, output)
        forecasts = bool(extensions == "all")
        try:
            response = self.client.get(cast(str, self.base_url), params=params)
            response.raise_for_status()
            response_json = response.json()
            return self._parse_weather_response(response_json, forecasts)

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP 请求失败：{e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"网络请求出错：{e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析 API 响应 JSON 失败：{e}") from e

    def get_realtime_weather(self, city: str) -> WeatherLives:
        r"""
        Gets the real-time (current) weather for a specific city.
        Use this function when the user asks for the weather "now", "currently",
        "today", or any other immediate weather condition.

        Args:
            city (str): **It must be the standard Chinese name**. For example: "北京" or "成都".**English (such as "Beijing") or pinyin (such as "Chengdu") is invalid**.

        Returns:
            WeatherLives: An object containing the live weather details.
        """
        weather_data = self.fetch_weather_from_api(city, extensions="base")
        if not isinstance(weather_data, WeatherLives):
            raise TypeError(f"API Error: Expected WeatherLives object for 'base' extension, got {type(weather_data)}")
        return weather_data

    def get_weather_forecast(self, city: str) -> WeatherForecast:
        r"""
        Gets the 4-day weather forecast (including today) for a specific city.
        Use this function when the user asks for the weather "in the future",
        "in the next few days", "forecast", or "later".

        Args:
            city (str): **It must be the standard Chinese name**. For example: "上海" or "成都".**English (such as "Shanghai") or pinyin (such as "Chengdu") is invalid**.

        Returns:
            WeatherForecast: An object containing the 4-day weather forecast.
        """
        weather_data = self.fetch_weather_from_api(city, extensions="all")
        if not isinstance(weather_data, WeatherForecast):
            raise TypeError(f"API Error: Expected WeatherForecast object for 'all' extension, got {type(weather_data)}")
        return weather_data

    def get_tools(self) -> list[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.get_realtime_weather),
            FunctionTool(self.get_weather_forecast),
        ]

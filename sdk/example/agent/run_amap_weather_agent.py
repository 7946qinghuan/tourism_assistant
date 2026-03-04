import asyncio
import os

from camel.responses import ChatAgentResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tourism_assistant.agent import LRUAgentManager, ModelProvider
from tourism_assistant.prompts import WEATHER_AGENT_PROMPT
from tourism_assistant.toolkits import MCPManager

load_dotenv(override=True, verbose=True)
mcp_manager = MCPManager(os.getenv("AMAP_MCP_TOOL_CONFIG_PATH"))
model_provider = ModelProvider()
model_stream = model_provider.create_model(
    model_name=os.getenv("LLM_BASE_NAME"),
    url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_BASE_API_KEY"),
    model_config_dict={"temperature": 0.1, "stream": False},
)

cache_agent_manager = LRUAgentManager(model_stream)


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


async def test_async_non_streaming_agent():
    await mcp_manager.connect()
    try:
        mcp_tools = mcp_manager.get_tools()
        agent_id = "test_agent_04"
        cache_agent_manager.register_agent(
            agent_id, system_message=WEATHER_AGENT_PROMPT, tools=mcp_tools
        )
        user_message = "搜索成都的天气"

        print(f"User: {user_message}\n")
        print("Assistant Full Response:\n")
        origin_res = await cache_agent_manager.acall_agent(
            agent_id,
            user_message,
        )
        if isinstance(origin_res, ChatAgentResponse):
            print(origin_res.msgs[0].content)
            format_message = f"请你根据以下天气信息,返回一个包含天气描述、温度和风力的列表: {origin_res.msgs[0].content}"
            print("Format Response:\n")
            res = await cache_agent_manager.acall_agent(
                agent_id, format_message, response_format=WeatherSearchResponse
            )
            if isinstance(res, ChatAgentResponse):
                print(res.msgs[0].content)

    finally:
        await mcp_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(test_async_non_streaming_agent())

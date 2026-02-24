import asyncio
import os

from camel.responses import ChatAgentResponse
from dotenv import load_dotenv
from tourism_assistant.agent import LRUAgentManager, ModelProvider
from tourism_assistant.prompts import WEATHER_AGENT_PROMPT
from tourism_assistant.toolkits import OpenMeteoWeatherToolkit, WeatherResult

load_dotenv(override=True, verbose=True)
model_provider = ModelProvider()
model_stream = model_provider.create_model(
    model_name=os.getenv("LLM_BASE_NAME"),
    url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_BASE_API_KEY"),
    model_config_dict={"temperature": 0.1, "stream": False},
)

cache_agent_manager = LRUAgentManager(model_stream)


async def test_async_non_streaming_agent():
    weather_tool = [*OpenMeteoWeatherToolkit().get_tools()]
    agent_id = "test_agent_04"
    cache_agent_manager.register_agent(
        agent_id, system_message=WEATHER_AGENT_PROMPT, tools=weather_tool
    )
    user_message = "搜索成都2026年2月21日到2026年2月25日的天气"

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
            agent_id, format_message, response_format=WeatherResult
        )
        if isinstance(res, ChatAgentResponse):
            print(res.msgs[0].content)


if __name__ == "__main__":
    asyncio.run(test_async_non_streaming_agent())

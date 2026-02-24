import asyncio
import os

from camel.responses import ChatAgentResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from tourism_assistant.agent import LRUAgentManager, ModelProvider
from tourism_assistant.prompts import HOTEL_AGENT_PROMPT
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


class HotelSearchdata(BaseModel):
    id: str = Field(description="酒店ID")
    name: str = Field(description="酒店名称")
    address: str = Field(description="酒店地址")
    photo_url: str = Field(description="酒店照片URL")
    typecode: str = Field(description="酒店类型编码")


class HotelSearchResponse(BaseModel):
    hotels: list[HotelSearchdata] = Field(description="多个酒店搜索结果")


async def test_async_non_streaming_agent():
    await mcp_manager.connect()
    try:
        mcp_tools = mcp_manager.get_tools()
        agent_id = "test_agent_04"
        cache_agent_manager.register_agent(agent_id, system_message=HOTEL_AGENT_PROMPT, tools=mcp_tools)
        user_message = "搜索成都的高性价比酒店"

        print(f"User: {user_message}\n")
        print("Assistant Full Response:\n")
        origin_res = await cache_agent_manager.acall_agent(
            agent_id,
            user_message,
        )
        if isinstance(origin_res, ChatAgentResponse):
            print(origin_res.msgs[0].content)
            format_message = (
                f"请你根据以下酒店信息,返回一个包含酒店名称、地址和照片URL的列表: {origin_res.msgs[0].content}"
            )
            print("Format Response:\n")
            res = await cache_agent_manager.acall_agent(agent_id, format_message, response_format=HotelSearchResponse)
            if isinstance(res, ChatAgentResponse):
                print(res.msgs[0].content)

    finally:
        await mcp_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(test_async_non_streaming_agent())

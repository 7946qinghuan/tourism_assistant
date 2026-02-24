import asyncio
import os

from camel.responses import ChatAgentResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from tourism_assistant.agent import LRUAgentManager, ModelProvider
from tourism_assistant.prompts import ATTRACTION_AGENT_PROMPT
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


class AttractionSearchdata(BaseModel):
    id: str = Field(description="景点ID")
    name: str = Field(description="单个景点名称")
    address: str = Field(description="单个景点地址")
    photo_url: str = Field(description="单个景点照片URL")
    typecode: str = Field(description="景点类型编码")


class AttractionSearchResponse(BaseModel):
    attractions: list[AttractionSearchdata] = Field(description="多个景点搜索结果")


async def test_async_non_streaming_agent():
    await mcp_manager.connect()
    try:
        mcp_tools = mcp_manager.get_tools()
        agent_id = "test_agent_04"
        cache_agent_manager.register_agent(agent_id, system_message=ATTRACTION_AGENT_PROMPT, tools=mcp_tools)
        user_message = "搜索成都的古镇"

        print(f"User: {user_message}\n")
        print("Assistant Full Response:\n")
        origin_res = await cache_agent_manager.acall_agent(
            agent_id,
            user_message,
        )
        if isinstance(origin_res, ChatAgentResponse):
            print(origin_res.msgs[0].content)
            format_message = f"根据以下景点信息,返回一个包含景点名称、地址和照片URL的列表: {origin_res.msgs[0].content}"
            print("Format Response:\n")
            res = await cache_agent_manager.acall_agent(
                agent_id, format_message, response_format=AttractionSearchResponse
            )
            if isinstance(res, ChatAgentResponse):
                print(res.msgs[0].content)

    finally:
        await mcp_manager.disconnect()


async def test_async_streaming_agent():
    await mcp_manager.connect()
    try:
        mcp_tools = mcp_manager.get_tools()
        agent_id = "test_agent_04"
        cache_agent_manager.register_agent(agent_id, system_message=ATTRACTION_AGENT_PROMPT, tools=mcp_tools)
        message = "搜索成都的古镇"

        print(f"User: {message}\n")
        print("Assistant Streaming Response:\n")
        res = await cache_agent_manager.acall_agent(agent_id, message)
        if not isinstance(res, ChatAgentResponse):
            current_full_response = ""
            current_chunk_content = ""
            last_full_response = ""
            async for chunk in res:
                if chunk.msgs:
                    current_full_response = chunk.msgs[0].content
                    current_chunk_content = current_full_response[len(last_full_response) :]
                    last_full_response = current_full_response
                    print(current_chunk_content, end="", flush=True)
    finally:
        await mcp_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(test_async_non_streaming_agent())
    # asyncio.run(test_async_streaming_agent())

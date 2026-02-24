import asyncio
import os

from camel.responses import ChatAgentResponse
from dotenv import load_dotenv
from tourism_assistant.agent import LRUAgentManager, ModelProvider, TTLAgentManager

load_dotenv(override=True, verbose=True)

model_provider = ModelProvider()
model_stream = model_provider.create_model(
    model_name=os.getenv("LLM_BASE_NAME"),
    url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_BASE_API_KEY"),
    model_config_dict={"temperature": 0.1, "stream": True},
)
model_non_stream = model_provider.create_model(
    model_name=os.getenv("LLM_BASE_NAME"),
    url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_BASE_API_KEY"),
    model_config_dict={"temperature": 0.1, "stream": False},
)

ttl_agent_manager = TTLAgentManager(model_non_stream)
cache_agent_manager = LRUAgentManager(model_stream)


def test_non_streaming_agent():
    agent_id = "test_agent_01"
    ttl_agent_manager.register_agent(agent_id, system_message="你是一个智能助手")
    message = "模仿李煜的风格，写一首七言律诗"
    ttl_agent_manager.call_agent(agent_id, message)
    print(f"User: {message}\n")
    print("Assistant Full Response:\n")
    res = ttl_agent_manager.call_agent(agent_id, message)
    if isinstance(res, ChatAgentResponse):
        print(res.msgs[0].content)


def test_streaming_agent():
    agent_id = "test_agent_02"
    cache_agent_manager.register_agent(agent_id, system_message="你是一个智能助手")
    message = "模仿李煜的风格，写一首七言律诗"

    print(f"User: {message}\n")
    print("Assistant Streaming Response:\n")
    res = cache_agent_manager.call_agent(agent_id, message)
    if not isinstance(res, ChatAgentResponse):
        current_full_response = ""
        current_chunk_content = ""
        last_full_response = ""
        for chunk in res:
            if chunk.msgs:
                current_full_response = chunk.msgs[0].content
                current_chunk_content = current_full_response[len(last_full_response) :]
                last_full_response = current_full_response
                print(current_chunk_content, end="", flush=True)


async def test_async_non_streaming_agent():
    agent_id = "test_agent_03"
    ttl_agent_manager.register_agent(agent_id, system_message="你是一个智能助手")
    message = "模仿李煜的风格，写一首七言律诗"

    print(f"User: {message}\n")
    print("Assistant Full Response:\n")
    res = await ttl_agent_manager.acall_agent(agent_id, message)
    if isinstance(res, ChatAgentResponse):
        print(res.msgs[0].content)


async def test_async_streaming_agent():
    agent_id = "test_agent_04"
    cache_agent_manager.register_agent(agent_id, system_message="你是一个智能助手")
    message = "模仿李煜的风格，写一首七言律诗"

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


if __name__ == "__main__":
    # test_non_streaming_agent()
    # test_streaming_agent()
    asyncio.run(test_async_non_streaming_agent())
    asyncio.run(test_async_streaming_agent())

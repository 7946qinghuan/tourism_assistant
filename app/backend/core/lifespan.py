from contextlib import asynccontextmanager

from fastapi import FastAPI
from tourism_assistant.agent import LRUAgentManager, ModelProvider
from tourism_assistant.toolkits import MCPManager

from app.backend.core.config import Settings
from app.backend.services import UnsplashService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Initializes and cleans up resources like model backends and managers.
    """
    settings = Settings()

    model_provider = ModelProvider()
    model = model_provider.create_model(
        model_name=settings.llm_base_name,
        url=settings.llm_base_url,
        api_key=settings.llm_base_api_key,
        model_config_dict=settings.llm_model_config_dict,
    )

    agent_manager = LRUAgentManager(model=model)

    mcp_manager = MCPManager(settings.amap_mcp_tool_config_path)
    await mcp_manager.connect()
    mcp_tools = mcp_manager.get_tools()

    unsplash_service = UnsplashService()

    app.state.agent_manager = agent_manager
    app.state.mcp_manager = mcp_manager
    app.state.mcp_tools = mcp_tools
    app.state.unsplash_service = unsplash_service
    app.state.settings = settings

    try:
        yield
    finally:
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.disconnect()

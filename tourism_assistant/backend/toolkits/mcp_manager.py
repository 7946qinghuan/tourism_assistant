from typing import Optional

from camel.toolkits import FunctionTool, MCPToolkit
from loguru import logger

from tourism_assistant.backend.core.config import Settings

settings = Settings()


class MCPManager:
    _instance: Optional["MCPManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str | None = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        if config_path is None:
            raise ValueError("config_path must be provided")

        self.config_path = config_path
        self.toolkit: MCPToolkit | None = None
        self._initialized = True
        self._is_connected = False

    async def connect(self):
        """Asynchronously connect to all configured MCP servers."""
        if self._is_connected:
            return

        try:
            logger.info(f"Initializing MCPToolkit from {self.config_path}")
            self.toolkit = MCPToolkit(config_path=self.config_path)
            await self.toolkit.connect()
            self._is_connected = True
            logger.info("MCPToolkit connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect MCPToolkit: {e}")
            raise

    async def disconnect(self):
        """Close all MCP connections."""
        if self.toolkit and self._is_connected:
            await self.toolkit.disconnect()
            self._is_connected = False
            logger.info("MCPToolkit disconnected.")

    def get_tools(self) -> list[FunctionTool]:
        """
        Retrieve all available MCP tools.
        Note: Ensure connect() has been called and awaited before calling this method.
        """
        if not self._is_connected or self.toolkit is None:
            logger.warning("MCPManager is not connected. Returning empty tool list. Please call await connect() first.")
            return []

        logger.info(f"Retrieving {len(self.toolkit.get_tools())} MCP tools.")
        return self.toolkit.get_tools()


mcp_manager = MCPManager(settings.mcp_tool_config_path)

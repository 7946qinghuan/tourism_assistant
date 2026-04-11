import os
from dataclasses import dataclass, field  # 导入 field

from dotenv import load_dotenv

load_dotenv(override=True, verbose=True)


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Tourism Assistant")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")

    llm_base_name: str | None = os.getenv("LLM_BASE_NAME")
    llm_base_url: str | None = os.getenv("LLM_BASE_URL")
    llm_base_api_key: str | None = os.getenv("LLM_BASE_API_KEY")

    # 使用 field 和 default_factory 来处理可变对象
    llm_model_config_dict: dict = field(
        default_factory=lambda: {
            "temperature": 0.1,
            "stream": False,
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False},
            },
        }
    )

    amap_mcp_tool_config_path: str | None = os.getenv("AMAP_MCP_TOOL_CONFIG_PATH")

    amap_api_key_js: str | None = os.getenv("AMAP_MAPS_API_KEY_JS")
    amap_security_js_code: str | None = os.getenv("AMAP_MAPS_SECURITY_JS_CODE")

    unsplash_access_key: str | None = os.getenv("UNSPLASH_ACCESS_KEY")
    unsplash_secret_key: str | None = os.getenv("UNSPLASH_SECRET_KEY")

    # Server settings
    TOURISM_HOST: str = os.getenv("TOURISM_HOST", "127.0.0.1")
    TOURISM_PORT: int = int(os.getenv("TOURISM_PORT", 8000))

    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 这是 dataclass 初始化后的钩子
    def __post_init__(self):
        print("llm_base_name:", self.llm_base_name)
        print("llm_base_url:", self.llm_base_url)
        print("llm_base_api_key:", self.llm_base_api_key)
        print("amap_mcp_tool_config_path:", self.amap_mcp_tool_config_path)
        print(f"Running on host: {self.TOURISM_HOST} and port: {self.TOURISM_PORT}")
        print("amap_api_key_js:", self.amap_api_key_js)
        print("amap_security_js_code:", self.amap_security_js_code)

    def get_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

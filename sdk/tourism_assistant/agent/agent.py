import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import AsyncGenerator, Callable, Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import wraps

from camel.agents import ChatAgent
from camel.agents.chat_agent import (
    AsyncStreamingChatAgentResponse,
    StreamingChatAgentResponse,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.models.base_model import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.types import ModelPlatformType
from pydantic import BaseModel


def locked(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


@dataclass
class AgentEntry:
    agent: ChatAgent
    last_accessed: datetime
    instance_lock: threading.Lock = field(default_factory=threading.Lock)


class BaseAgentManager(ABC):
    def __init__(self, model: BaseModelBackend):
        self.model = model
        self._lock = threading.RLock()

    def _create_agent(self, system_message, **kwargs) -> ChatAgent:
        return ChatAgent(model=self.model, system_message=system_message, **kwargs)

    @abstractmethod
    def register_agent(
        self, agent_id: str, system_message: BaseMessage | str | None = None, **kwargs
    ):
        pass

    @abstractmethod
    def get_agent_entry(self, agent_id: str) -> AgentEntry:
        pass

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        pass

    @abstractmethod
    def list_agent_ids(self) -> list[str]:
        pass

    @staticmethod
    async def _wrap_async_stream(response):
        async for chunk in response:
            yield chunk

    @staticmethod
    def _wrap_sync_stream(response):
        yield from response

    def call_agent(
        self,
        agent_id: str,
        message: str,
        response_format: type[BaseModel] | None = None,
    ) -> ChatAgentResponse | Generator[ChatAgentResponse, None, None]:
        try:
            entry = self.get_agent_entry(agent_id)
            with entry.instance_lock:
                response = entry.agent.step(message, response_format=response_format)
                if isinstance(response, StreamingChatAgentResponse):
                    return self._wrap_sync_stream(response)
                return response
        except Exception as e:
            raise RuntimeError(f"Agent[{agent_id}] call failed") from e

    async def acall_agent(
        self,
        agent_id: str,
        message: str,
        response_format: type[BaseModel] | None = None,
    ) -> ChatAgentResponse | AsyncGenerator[ChatAgentResponse, None]:
        try:
            entry = self.get_agent_entry(agent_id)
            with entry.instance_lock:
                response = await entry.agent.astep(
                    message, response_format=response_format
                )
                if isinstance(response, AsyncStreamingChatAgentResponse):
                    return self._wrap_async_stream(response)
                return response
        except Exception as e:
            raise RuntimeError(f"Agent[{agent_id}] call failed") from e


class TTLAgentManager(BaseAgentManager):
    def __init__(self, model: BaseModelBackend, ttl_seconds: int = 3600):
        super().__init__(model)
        self._container: dict[str, AgentEntry] = {}
        self.ttl_seconds = ttl_seconds
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    @locked
    def register_agent(
        self, agent_id: str, system_message: BaseMessage | str | None = None, **kwargs
    ):
        if agent_id in self._container:
            raise ValueError(f"Agent {agent_id} already exists")
        agent = self._create_agent(system_message, **kwargs)
        self._container[agent_id] = AgentEntry(
            agent=agent, last_accessed=datetime.now(UTC)
        )

    @locked
    def get_agent_entry(self, agent_id: str) -> AgentEntry:
        if agent_id not in self._container:
            raise KeyError(f"Agent {agent_id} not found")
        entry = self._container[agent_id]
        entry.last_accessed = datetime.now(UTC)
        return entry

    @locked
    def delete_agent(self, agent_id: str) -> bool:
        return self._container.pop(agent_id, None) is not None

    @locked
    def list_agent_ids(self) -> list[str]:
        return list(self._container.keys())

    def _do_cleanup(self):
        now = datetime.now(UTC)
        with self._lock:
            expired = [
                k
                for k, v in self._container.items()
                if now - v.last_accessed > timedelta(seconds=self.ttl_seconds)
            ]
            for k in expired:
                del self._container[k]

    def _cleanup_loop(self):
        while True:
            time.sleep(60)
            self._do_cleanup()


class LRUAgentManager(BaseAgentManager):
    def __init__(self, model: BaseModelBackend, max_capacity: int = 100):
        super().__init__(model)
        self._container: OrderedDict[str, AgentEntry] = OrderedDict()
        self.max_capacity = max_capacity

    @locked
    def register_agent(
        self, agent_id: str, system_message: BaseMessage | str | None = None, **kwargs
    ):
        if agent_id in self._container:
            self._container.move_to_end(agent_id)
            return

        if len(self._container) >= self.max_capacity:
            # last=False 表示 FIFO，弹出最早插入/移动的条目
            old_id, _ = self._container.popitem(last=False)
            # 这里可以根据需要添加日志：logger.info(f"LRU: Evicted agent {old_id}")

        agent = self._create_agent(system_message, **kwargs)
        self._container[agent_id] = AgentEntry(
            agent=agent, last_accessed=datetime.now(UTC)
        )

    @locked
    def get_agent_entry(self, agent_id: str) -> AgentEntry:
        if agent_id not in self._container:
            raise KeyError(f"Agent {agent_id} not found")

        entry = self._container[agent_id]
        entry.last_accessed = datetime.now(UTC)
        self._container.move_to_end(agent_id)

        return entry

    @locked
    def delete_agent(self, agent_id: str) -> bool:
        return self._container.pop(agent_id, None) is not None

    @locked
    def list_agent_ids(self) -> list[str]:
        return list(self._container.keys())

    @locked
    def clear(self):
        self._container.clear()


class ModelProvider:
    def __init__(self):
        self._factory = ModelFactory()

    def create_model(
        self, model_name, url, api_key, model_config_dict=None, **kwargs
    ) -> BaseModelBackend:
        if model_config_dict is None:
            model_config_dict = {"temperature": 0.1, "stream": True}

        return self._factory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=model_name,
            url=url,
            api_key=api_key,
            model_config_dict=model_config_dict,
            **kwargs,
        )

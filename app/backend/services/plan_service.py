import json

from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool
from loguru import logger
from tourism_assistant.agent import BaseAgentManager
from tourism_assistant.prompts import (
    ATTRACTION_AGENT_PROMPT,
    HOTEL_AGENT_PROMPT,
    PLANNER_AGENT_PROMPT,
    PLANNER_QUERY_PROMPT,
    WEATHER_AGENT_PROMPT,
)
from tourism_assistant.toolkits import OpenMeteoWeatherToolkit, WeatherResult

from ..models.api import TripPlan, TripRequest
from ..models.services import (
    AttractionResult,
    AttractionSearchdata,
    HotelResult,
    HotelSearchdata,
)


class PlanTripService:
    def __init__(self, agent_manager: BaseAgentManager, mcp_tools: list[FunctionTool]):
        self.agent_manager = agent_manager
        self.agent_info = {
            "attraction_agent": {"prompt": ATTRACTION_AGENT_PROMPT, "tools": mcp_tools},
            "weather_agent": {
                "prompt": WEATHER_AGENT_PROMPT,
                "tools": OpenMeteoWeatherToolkit().get_tools(),
            },
            "hotel_agent": {"prompt": HOTEL_AGENT_PROMPT, "tools": mcp_tools},
            "planner_agent": {"prompt": PLANNER_AGENT_PROMPT, "tools": []},
        }

    def prepare_agent(self):
        if len(self.agent_manager.list_agent_ids()) == 0:
            for agent_id, info in self.agent_info.items():
                self.agent_manager.register_agent(
                    agent_id=agent_id,
                    system_message=info["prompt"],
                    tools=info["tools"],
                )
        else:
            agent_ids = self.agent_manager.list_agent_ids()
            logger.info(f"Agents already prepared: {agent_ids}")

    def clear_agent(self):
        for agent_id in self.agent_info:
            self.agent_manager.delete_agent(agent_id)

    @staticmethod
    def _parse_json_from_llm_response(response_content: str) -> dict | None:
        """
        Parses a JSON string from an LLM response that is typically formatted as:
        ```json
        {...}
        ```
        """
        try:
            start_delimiter = "```json"
            end_delimiter = "```"
            start_index = response_content.find(start_delimiter)
            end_index = response_content.rfind(end_delimiter)

            if start_index == -1 or end_index == -1 or start_index >= end_index:
                logger.warning("JSON start or end delimiters not found in response.")
                return None

            json_str = response_content[
                start_index + len(start_delimiter) : end_index
            ].strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from response: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON parsing: {e}")
            return None

    def _build_attraction_query(self, request: TripRequest) -> list[str]:
        query_list = []
        for preference in request.preferences:
            query_list.append(f"搜索{request.city}的{preference}景点")
        return query_list

    async def call_attraction_agent(
        self, request: TripRequest
    ) -> list[AttractionSearchdata] | None:
        attraction_query_list = self._build_attraction_query(request)

        res_list = []

        for query in attraction_query_list:
            text_response = await self.agent_manager.acall_agent(
                agent_id="attraction_agent", message=query
            )
            if isinstance(text_response, ChatAgentResponse):
                logger.debug(
                    f"Attraction Agent Response: \n{text_response.msgs[0].content}"
                )
                try:
                    parsed_content = self._parse_json_from_llm_response(
                        text_response.msgs[0].content
                    )
                    if not isinstance(parsed_content, dict):
                        raise TypeError(
                            f"The response content is not a JSON dictionary: {type(parsed_content)}"
                        )

                    response_data = AttractionResult(**parsed_content)
                    res_list.extend(response_data.attractions)

                except ValueError as ve:
                    error_msg = f"Failed to create AttractionResult instance: {str(ve)}"
                    logger.error(error_msg, exc_info=True)
                    raise ValueError(error_msg) from ve

                except Exception as e:
                    error_msg = f"Failed to process AttractionResult instance: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    raise RuntimeError(error_msg) from e

            return res_list

    def _build_weather_query(self, request: TripRequest) -> str:
        return f"搜索{request.city}从{request.start_date}到{request.end_date}的天气"

    async def call_weather_agent(self, request: TripRequest) -> WeatherResult | None:
        weather_query = self._build_weather_query(request)
        text_response = await self.agent_manager.acall_agent(
            agent_id="weather_agent", message=weather_query
        )

        if isinstance(text_response, ChatAgentResponse):
            logger.debug(f"Weather Agent Response: \n{text_response.msgs[0].content}")
            try:
                parsed_content = self._parse_json_from_llm_response(
                    text_response.msgs[0].content
                )
                if not isinstance(parsed_content, dict):
                    raise TypeError(
                        f"The response content is not a JSON dictionary: {type(parsed_content)}"
                    )

                response_data = WeatherResult(**parsed_content)
                return response_data

            except ValueError as ve:
                error_msg = f"Failed to create WeatherResult instance: {str(ve)}"
                logger.error(error_msg, exc_info=True)
                raise ValueError(error_msg) from ve

            except Exception as e:
                error_msg = f"Failed to process WeatherResult instance: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e
        return None

    def _build_hotel_query(self, request: TripRequest) -> str:
        return f"搜索{request.city}的{request.accommodation}酒店"

    async def call_hotel_agent(
        self, request: TripRequest
    ) -> list[HotelSearchdata] | None:
        hotel_query = self._build_hotel_query(request)
        text_response = await self.agent_manager.acall_agent(
            agent_id="hotel_agent", message=hotel_query
        )

        if isinstance(text_response, ChatAgentResponse):
            logger.debug(f"Hotel Agent Response: \n{text_response.msgs[0].content}")
            try:
                parsed_content = self._parse_json_from_llm_response(
                    text_response.msgs[0].content
                )
                if not isinstance(parsed_content, dict):
                    raise TypeError(
                        f"The response content is not a JSON dictionary: {type(parsed_content)}"
                    )

                response_data = HotelResult(**parsed_content)
                return response_data.hotels

            except ValueError as ve:
                error_msg = f"Failed to create HotelResult instance: {str(ve)}"
                logger.error(error_msg, exc_info=True)
                raise ValueError(error_msg) from ve

            except Exception as e:
                error_msg = f"Failed to process HotelResult instance: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e
        return None

    def _build_trip_plan(
        self,
        request: TripRequest,
        attraction_res: list[AttractionSearchdata] | None,
        weather_res: WeatherResult | None,
        hotel_res: list[HotelSearchdata] | None,
    ) -> str:
        plan_query = PLANNER_QUERY_PROMPT.render(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            travel_days=request.travel_days,
            transportation=request.transportation,
            accommodation=request.accommodation,
            preferences=request.preferences if request.preferences else "无",
            attractions=attraction_res if attraction_res else "无",
            weather=weather_res if weather_res else "无",
            hotels=hotel_res if hotel_res else "无",
            free_text_input=request.free_text_input
            if request.free_text_input
            else "无",
        )
        return plan_query

    async def call_planner_agent(
        self,
        request: TripRequest,
        attraction_res: list[AttractionSearchdata] | None,
        weather_res: WeatherResult | None,
        hotel_res: list[HotelSearchdata] | None,
    ) -> TripPlan | None:
        plan_query = self._build_trip_plan(
            request, attraction_res, weather_res, hotel_res
        )
        text_response = await self.agent_manager.acall_agent(
            agent_id="planner_agent", message=plan_query
        )

        if isinstance(text_response, ChatAgentResponse):
            logger.debug(f"Planner Agent Response: \n{text_response.msgs[0].content}")
            try:
                parsed_content = self._parse_json_from_llm_response(
                    text_response.msgs[0].content
                )
                if not isinstance(parsed_content, dict):
                    raise TypeError(
                        f"The response content is not a JSON dictionary: {type(parsed_content)}"
                    )

                response_data = TripPlan(**parsed_content)
                return response_data

            except ValueError as ve:
                error_msg = f"Failed to create WeatherResult instance: {str(ve)}"
                logger.error(error_msg, exc_info=True)
                raise ValueError(error_msg) from ve

            except Exception as e:
                error_msg = f"Failed to process WeatherResult instance: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e
        return None

import asyncio
import os

from tourism_assistant.agent import LRUAgentManager, ModelProvider

from app.backend.models.api import TripRequest
from app.backend.services.plan_service import PlanTripService


async def test_plan_trip():
    from dotenv import load_dotenv

    load_dotenv(override=True, verbose=True)

    from tourism_assistant.toolkits import MCPManager

    mcp_manager = MCPManager(os.getenv("AMAP_MCP_TOOL_CONFIG_PATH"))

    request = TripRequest(
        city="成都",
        start_date="2026-03-01",
        end_date="2026-03-08",
        travel_days=7,
        transportation="flight",
        accommodation="hotel",
        preferences=[
            "博物馆",
            "古镇",
        ],
    )

    model_provider = ModelProvider()
    model = model_provider.create_model(
        model_name=os.getenv("LLM_BASE_NAME"),
        url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_BASE_API_KEY"),
        model_config_dict={"temperature": 0.1, "stream": False},
    )
    agent_manager = LRUAgentManager(model)
    await mcp_manager.connect()
    try:
        mcp_tools = mcp_manager.get_tools()
        plan_service = PlanTripService(agent_manager=agent_manager, mcp_tools=mcp_tools)
        plan_service.prepare_agent()
        task_list = []
        task_list.append(
            asyncio.create_task(plan_service.call_attraction_agent(request))
        )
        task_list.append(asyncio.create_task(plan_service.call_weather_agent(request)))
        task_list.append(asyncio.create_task(plan_service.call_hotel_agent(request)))
        attraction_res, weather_res, hotel_res = await asyncio.gather(*task_list)
        trip_plan = await plan_service.call_planner_agent(
            request, attraction_res, weather_res, hotel_res
        )
        print(trip_plan)

        # weather_res = await plan_service.call_weather_agent(request)
        # print(weather_res)
        # attraction_res = await plan_service.call_attraction_agent(request)
        # print(attraction_res)
        # hotel_res = await plan_service.call_hotel_agent(request)
        # print(hotel_res)

    finally:
        await mcp_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(test_plan_trip())

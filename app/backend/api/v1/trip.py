import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from mcp.types import CallToolResult, TextContent
from tourism_assistant.toolkits.mcp_manager import MCPManager

from app.backend.models.api import Location, TripPlan, TripPlanResponse, TripRequest
from app.backend.services.plan_service import PlanTripService

router = APIRouter(prefix="/trip", tags=["旅行规划"])


async def get_locations(trip_plan: TripPlan, mcp_manager: MCPManager):
    for day in trip_plan.days:
        hotel = day.hotel
        if hotel:
            address = hotel.address
            result = await mcp_manager.call_tool(
                tool_name="maps_geo", tool_args={"address": address}
            )
            if result and isinstance(result, CallToolResult):
                if result.content and isinstance(result.content[0], TextContent):
                    tool_result = json.loads(result.content[0].text).get("return")[0]
                    location = tool_result.get("location")
                    longitude, latitude = location.split(",")
                    if longitude and latitude:
                        hotel.location = Location(
                            longitude=float(longitude), latitude=float(latitude)
                        )
                    logger.info(
                        f"Hotel {hotel.name} for {address} has new location: {location}"
                    )

        if day.attractions:
            for attraction in day.attractions:
                address = attraction.address
                result = await mcp_manager.call_tool(
                    tool_name="maps_geo", tool_args={"address": address}
                )
                if result and isinstance(result, CallToolResult):
                    if result.content and isinstance(result.content[0], TextContent):
                        tool_result = json.loads(result.content[0].text).get("return")[
                            0
                        ]
                        location = tool_result.get("location")
                        longitude, latitude = location.split(",")
                        if longitude and latitude:
                            attraction.location = Location(
                                longitude=float(longitude), latitude=float(latitude)
                            )
                        logger.info(
                            f"Attraction {attraction.name} for {address} has new location: {location}"
                        )

    return trip_plan


@router.post(
    path="/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划",
)
async def plan_trip(trip_request: TripRequest, request: Request):
    """
    Receives a trip request, orchestrates various agents to gather information,
    and returns a complete travel plan.
    """
    logger.info(f"Received trip planning request for city: {trip_request.city}")

    agent_manager = request.app.state.agent_manager
    mcp_manager = request.app.state.mcp_manager
    mcp_tools = request.app.state.mcp_tools

    plan_service = PlanTripService(agent_manager=agent_manager, mcp_tools=mcp_tools)

    try:
        plan_service.prepare_agent()

        attraction_task = asyncio.create_task(
            plan_service.call_attraction_agent(trip_request)
        )
        weather_task = asyncio.create_task(
            plan_service.call_weather_agent(trip_request)
        )
        hotel_task = asyncio.create_task(plan_service.call_hotel_agent(trip_request))

        attraction_res, weather_res, hotel_res = await asyncio.gather(
            attraction_task, weather_task, hotel_task
        )

        logger.info("Successfully gathered information from all agents.")

        trip_plan = await plan_service.call_planner_agent(
            trip_request, attraction_res, weather_res, hotel_res
        )

        if trip_plan is None:
            logger.warning("Planner agent did not return a trip plan.")
            return TripPlanResponse(
                success=False,
                message="Planner agent did not return a trip plan.",
                data=None,
            )

        logger.success("Successfully generated trip plan.")
        trip_plan = await get_locations(trip_plan, mcp_manager)
        return TripPlanResponse(
            success=True, message="Plan generated successfully.", data=trip_plan
        )

    except Exception as e:
        logger.error(f"An error occurred during trip planning: {e}")
        return TripPlanResponse(
            success=False,
            message="An unexpected error occurred while planning the trip.",
            data=None,
        )
    finally:
        # Clean up agents after the request is complete
        plan_service.clear_agent()
        logger.info("Cleaned up agents.")


@router.get("/health", summary="健康检查", description="检查旅行规划服务是否正常")
async def health_check(request: Request):
    """健康检查"""
    try:
        agent_manager = request.app.state.agent_manager
        mcp_tools = request.app.state.mcp_tools

        return {
            "status": "healthy",
            "service": "trip-planner",
            "agents_count": len(agent_manager.list_agent_ids()),
            "tools_count": len(mcp_tools),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}") from e

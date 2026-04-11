import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from mcp.types import CallToolResult, TextContent
from tourism_assistant.toolkits.mcp_manager import MCPManager

from app.backend.models.api import Location, TripPlan, TripPlanResponse, TripRequest
from app.backend.services.plan_service import PlanTripService

router = APIRouter(prefix="/trip", tags=["旅行规划"])


# 中国坐标范围校验：经度 73-135，纬度 3-54
VALID_LONGITUDE_RANGE = (73, 135)
VALID_LATITUDE_RANGE = (3, 54)


def _is_valid_china_coordinate(longitude: float, latitude: float) -> bool:
    """校验坐标是否在中国范围内"""
    return (
        VALID_LONGITUDE_RANGE[0] <= longitude <= VALID_LONGITUDE_RANGE[1]
        and VALID_LATITUDE_RANGE[0] <= latitude <= VALID_LATITUDE_RANGE[1]
    )


async def _fetch_single_location(
    mcp_manager: MCPManager, name: str, address: str, item_type: str
) -> tuple[str, str, tuple[float, float] | None]:
    """
    获取单个地点的坐标
    Returns: (name, address, (longitude, latitude) or None)
    """
    try:
        result = await mcp_manager.call_tool(
            tool_name="maps_geo", tool_args={"address": address}
        )
        if not result or not isinstance(result, CallToolResult):
            return name, address, None

        if not result.content or not isinstance(result.content[0], TextContent):
            return name, address, None

        tool_result = json.loads(result.content[0].text).get("return")[0]
        location = tool_result.get("location")
        if not location:
            logger.warning(f"No location found for {item_type} {name}")
            return name, address, None

        longitude, latitude = location.split(",")
        if not longitude or not latitude:
            return name, address, None

        lon_float = float(longitude)
        lat_float = float(latitude)

        # 校验坐标是否在中国范围内
        if not _is_valid_china_coordinate(lon_float, lat_float):
            logger.warning(
                f"Invalid China coordinate for {item_type} {name}: ({lon_float}, {lat_float})"
            )
            return name, address, None

        return name, address, (lon_float, lat_float)

    except (json.JSONDecodeError, TypeError, IndexError, ValueError) as e:
        logger.warning(f"Failed to fetch location for {item_type} {name}: {e}")
        return name, address, None


async def get_locations(trip_plan: TripPlan, mcp_manager: MCPManager):
    """
    并行获取所有地点的坐标
    """
    tasks = []

    # 收集所有需要查询的任务
    for day in trip_plan.days:
        if day.hotel:
            tasks.append(
                _fetch_single_location(
                    mcp_manager, day.hotel.name, day.hotel.address, "Hotel"
                )
            )

        if day.attractions:
            for attraction in day.attractions:
                # 使用名称搜索比地址更准确
                tasks.append(
                    _fetch_single_location(
                        mcp_manager, attraction.name, attraction.name, "Attraction"
                    )
                )

    # 并行执行所有任务
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构建名称到坐标的映射
        location_map: dict[str, tuple[float, float]] = {}
        for _, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Task failed with exception: {result}")
                continue
            name, _, coords = result
            if coords:
                location_map[name] = coords

        # 应用坐标到对应的对象
        for day in trip_plan.days:
            if day.hotel and day.hotel.name in location_map:
                coords = location_map[day.hotel.name]
                day.hotel.location = Location(longitude=coords[0], latitude=coords[1])
                logger.info(
                    f"Hotel {day.hotel.name} has new location: {coords[0]},{coords[1]}"
                )

            if day.attractions:
                for attraction in day.attractions:
                    if attraction.name in location_map:
                        coords = location_map[attraction.name]
                        attraction.location = Location(
                            longitude=coords[0], latitude=coords[1]
                        )
                        logger.info(
                            f"Attraction {attraction.name} has new location: {coords[0]},{coords[1]}"
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

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get(
    "/keys",
    summary="获取高德地图API Key和Security JS Code",
    description="获取前端使用高德地图所需的API Key和Security JS Code",
)
async def get_amap_keys(request: Request):
    """
    获取高德地图JS API Key和Security JS Code
    """
    settings = request.app.state.settings
    if not settings.amap_api_key_js or not settings.amap_security_js_code:
        raise HTTPException(
            status_code=500, detail="高德地图API Key或Security JS Code未配置"
        )
    return {
        "amap_api_key_js": settings.amap_api_key_js,
        "amap_security_js_code": settings.amap_security_js_code,
    }


@router.get(
    "/photo", summary="获取景点图片", description="根据景点名称从Unsplash获取图片"
)
async def get_attraction_photo(name: str, request: Request):
    """
    获取景点图片

    Args:
        name: 景点名称

    Returns:
        图片URL
    """
    try:
        unsplash_service = request.app.state.unsplash_service

        photo_url = unsplash_service.get_photo_url(f"{name} China landmark")

        if not photo_url:
            photo_url = unsplash_service.get_photo_url(name)

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {"name": name, "photo_url": photo_url},
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"获取景点图片失败: {str(e)}"
        ) from e


@router.get("/health", summary="健康检查", description="检查地图服务是否正常")
async def health_check(request: Request):
    """
    健康检查
    """
    settings = request.app.state.settings
    if not settings.amap_api_key_js or not settings.amap_security_js_code:
        raise HTTPException(
            status_code=500, detail="高德地图API Key或Security JS Code未配置"
        )
    return {
        "status": "healthy",
        "service": "map-service",
        "amap_api_key_js": "amap_api_key_js is set",  # pragma: allowlist secret
        "amap_security_js_code": "amap_security_js_code is set",  # pragma: allowlist secret
    }

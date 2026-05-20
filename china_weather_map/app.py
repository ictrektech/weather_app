# -*- coding: utf-8 -*-
"""中国地图天气查询 - FastAPI 主应用"""

import os
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from weather_service import fetch_weather, is_suspect_input
from city_codes import is_valid_city, get_province_adcode, get_province_cities

app = FastAPI(title="中国地图天气查询", version="1.0.0")

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 挂载静态文件
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/api/weather")
async def get_weather(city: str = Query(None, description="城市名称")):
    """
    查询城市天气

    - city 参数必填，且必须在城市白名单中
    - 防止 SSRF：城市名只能从内置映射查询
    """
    # 检查 city 参数是否存在
    if city is None or city.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"error": "缺少 city 参数"}
        )

    city = city.strip()

    # SSRF 防护：检查可疑输入
    if is_suspect_input(city):
        return JSONResponse(
            status_code=400,
            content={"error": "无效的城市名"}
        )

    # 白名单校验
    if not is_valid_city(city):
        return JSONResponse(
            status_code=400,
            content={"error": f"不支持的城市: {city}"}
        )

    # 查询天气
    try:
        result = await fetch_weather(city)
        return JSONResponse(content=result)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"服务错误: {str(e)}"}
        )


@app.get("/api/province/geojson")
async def get_province_geojson(province: str = Query(None, description="省份简称")):
    """
    获取省份下钻地图 GeoJSON 数据
    从阿里云 DataV 获取地级市边界数据
    """
    if province is None or province.strip() == "":
        return JSONResponse(status_code=400, content={"error": "缺少 province 参数"})

    province = province.strip()

    if is_suspect_input(province):
        return JSONResponse(status_code=400, content={"error": "无效的省份名"})

    adcode = get_province_adcode(province)
    if not adcode:
        return JSONResponse(status_code=400, content={"error": f"不支持的省份: {province}"})

    try:
        import httpx
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=502,
                    content={"error": "获取省份地图数据失败"}
                )
            return JSONResponse(content=resp.json())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"获取省份地图数据失败: {str(e)}"}
        )


@app.get("/api/province/cities")
async def get_province_cities_api(province: str = Query(None, description="省份简称")):
    """获取省份下辖城市列表"""
    if province is None or province.strip() == "":
        return JSONResponse(status_code=400, content={"error": "缺少 province 参数"})

    province = province.strip()

    if is_suspect_input(province):
        return JSONResponse(status_code=400, content={"error": "无效的省份名"})

    cities = get_province_cities(province)
    if not cities:
        return JSONResponse(status_code=400, content={"error": f"不支持的省份: {province}"})

    return JSONResponse(content={"province": province, "cities": cities})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7878)

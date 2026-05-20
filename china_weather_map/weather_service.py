# -*- coding: utf-8 -*-
"""天气查询服务 - 从中国天气网获取天气数据"""

import httpx
from city_codes import get_city_code, is_valid_city

# 中国天气网公开接口（社区维护）
WEATHER_API_URL = "http://t.weather.itboy.net/api/weather/city/{code}"
# 详情页 URL 模板
DETAIL_URL_TEMPLATE = "http://www.weather.com.cn/weather1d/{code}.shtml"

# 请求超时设置
TIMEOUT = 10.0


def is_suspect_input(city: str) -> bool:
    """检查输入是否可疑（可能是 SSRF 攻击）"""
    suspicious_patterns = [
        "http", "://", "@", "/", "\\", ".com", ".net", ".org",
        ".cn", ".io", "%", "&", "=", "?", "#", ";", "|",
        "`", "$", "(", ")", "{", "}", "[", "]", "<", ">",
        "ftp", "ssh", "telnet", "file", "data",
    ]
    city_lower = city.lower()
    return any(p in city_lower for p in suspicious_patterns)


async def fetch_weather(city: str) -> dict:
    """
    查询城市天气

    Args:
        city: 城市名称

    Returns:
        dict: 天气信息，包含 city, weather, temp, wind, humidity, detail_url, city_code

    Raises:
        ValueError: 城市名无效
    """
    # 输入校验
    if not city or not city.strip():
        raise ValueError("城市名不能为空")

    city = city.strip()

    # SSRF 防护：检查可疑输入
    if is_suspect_input(city):
        raise ValueError("无效的城市名")

    # 白名单校验
    if not is_valid_city(city):
        raise ValueError(f"不支持的城市: {city}")

    # 获取城市代码
    city_code = get_city_code(city)
    if not city_code:
        raise ValueError(f"未找到城市代码: {city}")

    # 请求天气数据
    url = WEATHER_API_URL.format(code=city_code)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.RequestError as e:
        raise ValueError(f"天气数据请求失败: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"天气服务返回错误: {e.response.status_code}")

    # 解析天气数据
    return _parse_weather_data(data, city, city_code)


def _parse_weather_data(data: dict, city: str, city_code: str) -> dict:
    """解析中国天气网返回的数据"""
    result = {
        "city": city,
        "city_code": city_code,
        "detail_url": DETAIL_URL_TEMPLATE.format(code=city_code),
        "weather": "未知",
        "temp": "未知",
        "wind": "未知",
        "humidity": "未知",
    }

    try:
        # itboy API 数据结构
        if "data" in data:
            weather_data = data["data"]

            # 获取昨日数据作为参考
            yesterday = weather_data.get("yesterday", {})
            forecast = weather_data.get("forecast", [])

            if forecast and len(forecast) > 0:
                today = forecast[0]
                result["weather"] = today.get("type", "未知")
                high = today.get("high", "")
                low = today.get("low", "")
                # 提取温度数字
                high_temp = high.replace("高温 ", "").replace("℃", "")
                low_temp = low.replace("低温 ", "").replace("℃", "")
                if high_temp and low_temp:
                    result["temp"] = f"{low_temp}~{high_temp}℃"
                elif high_temp:
                    result["temp"] = f"{high_temp}℃"

                fx = today.get("fx", "")
                fl = today.get("fl", "")
                if fx and fl:
                    result["wind"] = f"{fx} {fl}"
                elif fx:
                    result["wind"] = fx

            # 湿度
            humidity = weather_data.get("shidu", "")
            if humidity:
                result["humidity"] = humidity

            # 实时温度
            wendu = weather_data.get("wendu", "")
            if wendu:
                result["temp"] = f"{wendu}℃"

        # 如果有 cityInfo，使用实际城市名
        if "cityInfo" in data and "city" in data["cityInfo"]:
            actual_city = data["cityInfo"]["city"]
            if actual_city:
                result["city"] = actual_city

    except (KeyError, IndexError, TypeError):
        pass

    return result

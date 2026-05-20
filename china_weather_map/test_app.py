# -*- coding: utf-8 -*-
"""自动化测试 - 中国地图天气查询"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app import app
from city_codes import get_city_code, is_valid_city, CITY_CODE_MAP
from weather_service import is_suspect_input

client = TestClient(app)


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestIndexEndpoint:
    """首页端点测试"""

    def test_index_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "中国地图天气查询" in response.text


class TestWeatherEndpoint:
    """天气查询端点测试"""

    def test_weather_missing_city_param(self):
        """缺少 city 参数应返回 400"""
        response = client.get("/api/weather")
        assert response.status_code == 400

    def test_weather_empty_city_param(self):
        """空 city 参数应返回 400"""
        response = client.get("/api/weather?city=")
        assert response.status_code == 400

    def test_weather_suspect_url_input(self):
        """SSRF 攻击输入应返回 400"""
        response = client.get("/api/weather?city=http://evil.com")
        assert response.status_code == 400

    def test_weather_suspect_at_input(self):
        """含 @ 的输入应返回 400"""
        response = client.get("/api/weather?city=test@evil.com")
        assert response.status_code == 400

    def test_weather_suspect_slash_input(self):
        """含 / 的输入应返回 400"""
        response = client.get("/api/weather?city=/etc/passwd")
        assert response.status_code == 400

    def test_weather_nonexistent_city(self):
        """不存在的城市应返回 400"""
        response = client.get("/api/weather?city=非存在城市")
        assert response.status_code == 400

    def test_weather_beijing(self):
        """查询北京天气应返回包含城市名和详情 URL 的 JSON"""
        mock_data = {
            "data": {
                "wendu": "22",
                "shidu": "45%",
                "forecast": [{
                    "type": "晴",
                    "high": "高温 28℃",
                    "low": "低温 16℃",
                    "fx": "北风",
                    "fl": "3级"
                }]
            },
            "cityInfo": {"city": "北京"}
        }
        with patch("weather_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = AsyncMock()
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = client.get("/api/weather?city=北京")
            assert response.status_code == 200
            data = response.json()
            assert "city" in data
            assert "weather" in data
            assert "temp" in data
            assert "detail_url" in data
            assert "101010100" in data["detail_url"]

    def test_weather_tianjin_city_code(self):
        """天津市城市代码必须是 101030100"""
        code = get_city_code("天津市")
        assert code == "101030100"

    def test_weather_tianjin_alias(self):
        """天津别名也必须映射到正确代码"""
        code = get_city_code("天津")
        assert code == "101030100"

    def test_weather_shanghai_city_code(self):
        """上海市城市代码必须是 101020100"""
        code = get_city_code("上海市")
        assert code == "101020100"

    def test_weather_shanghai_alias(self):
        """上海别名也必须映射到正确代码"""
        code = get_city_code("上海")
        assert code == "101020100"

    def test_weather_tianjin_response(self):
        """天津市天气查询应返回正确数据"""
        mock_data = {
            "data": {
                "wendu": "20",
                "shidu": "55%",
                "forecast": [{
                    "type": "多云",
                    "high": "高温 25℃",
                    "low": "低温 15℃",
                    "fx": "东风",
                    "fl": "2级"
                }]
            },
            "cityInfo": {"city": "天津"}
        }
        with patch("weather_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = AsyncMock()
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = client.get("/api/weather?city=天津市")
            assert response.status_code == 200
            data = response.json()
            assert data["city_code"] == "101030100"
            assert "weather" in data
            assert "detail_url" in data
            assert "101030100" in data["detail_url"]

    def test_weather_shanghai_response(self):
        """上海市天气查询应返回正确数据"""
        mock_data = {
            "data": {
                "wendu": "24",
                "shidu": "65%",
                "forecast": [{
                    "type": "阴",
                    "high": "高温 27℃",
                    "low": "低温 20℃",
                    "fx": "东南风",
                    "fl": "3级"
                }]
            },
            "cityInfo": {"city": "上海"}
        }
        with patch("weather_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = AsyncMock()
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = client.get("/api/weather?city=上海市")
            assert response.status_code == 200
            data = response.json()
            assert data["city_code"] == "101020100"
            assert "101020100" in data["detail_url"]


class TestSSRFProtection:
    """SSRF 防护测试"""

    def test_url_in_city_param(self):
        response = client.get("/api/weather?city=http://evil.com")
        assert response.status_code == 400

    def test_https_in_city_param(self):
        response = client.get("/api/weather?city=https://evil.com")
        assert response.status_code == 400

    def test_ftp_in_city_param(self):
        response = client.get("/api/weather?city=ftp://evil.com")
        assert response.status_code == 400

    def test_at_symbol_in_city_param(self):
        response = client.get("/api/weather?city=user@host")
        assert response.status_code == 400

    def test_dot_com_in_city_param(self):
        response = client.get("/api/weather?city=evil.com")
        assert response.status_code == 400

    def test_percent_in_city_param(self):
        response = client.get("/api/weather?city=test%00")
        assert response.status_code == 400

    def test_backslash_in_city_param(self):
        response = client.get("/api/weather?city=test\\evil")
        assert response.status_code == 400

    def test_is_suspect_input_function(self):
        """测试 is_suspect_input 函数"""
        assert is_suspect_input("http://evil.com") is True
        assert is_suspect_input("ftp://evil.com") is True
        assert is_suspect_input("test@host") is True
        assert is_suspect_input("evil.com") is True
        assert is_suspect_input("/etc/passwd") is True
        assert is_suspect_input("北京") is False
        assert is_suspect_input("上海市") is False
        assert is_suspect_input("广州") is False


class TestCityCodes:
    """城市代码映射测试"""

    def test_beijing_code(self):
        assert get_city_code("北京") == "101010100"
        assert get_city_code("北京市") == "101010100"

    def test_shanghai_code(self):
        assert get_city_code("上海") == "101020100"
        assert get_city_code("上海市") == "101020100"

    def test_tianjin_code(self):
        assert get_city_code("天津") == "101030100"
        assert get_city_code("天津市") == "101030100"

    def test_chongqing_code(self):
        assert get_city_code("重庆") == "101040100"
        assert get_city_code("重庆市") == "101040100"

    def test_all_provinces_have_codes(self):
        """所有省级行政区都应该有映射"""
        provinces = [
            "北京", "上海", "天津", "重庆",
            "河北", "山西", "辽宁", "吉林", "黑龙江",
            "江苏", "浙江", "安徽", "福建", "江西", "山东",
            "河南", "湖北", "湖南", "广东", "海南",
            "四川", "贵州", "云南", "陕西", "甘肃", "青海",
            "内蒙古", "广西", "西藏", "宁夏", "新疆",
            "香港", "澳门", "台湾"
        ]
        for province in provinces:
            assert is_valid_city(province), f"缺少省份映射: {province}"

    def test_nonexistent_city(self):
        assert is_valid_city("非存在城市") is False
        assert get_city_code("非存在城市") is None


class TestDetailURL:
    """详情页 URL 测试"""

    def test_detail_url_format(self):
        """详情页 URL 必须指向中国天气网"""
        from weather_service import DETAIL_URL_TEMPLATE
        url = DETAIL_URL_TEMPLATE.format(code="101010100")
        assert url == "http://www.weather.com.cn/weather1d/101010100.shtml"
        assert url.startswith("http://www.weather.com.cn/")

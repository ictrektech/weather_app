# 中国地图天气查询

交互式中国地图天气查询 Web 应用。用户在地图上悬停省份即可查看实时天气，点击可跳转中国天气网详情页。

## 快速开始

### 1. 克隆仓库

```bash
git clone <repo-url> weather_app
cd weather_app
```

### 2. 安装依赖

建议使用虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

cd china_weather_map
pip install -r requirements.txt
```

依赖清单：
- fastapi==0.104.1
- uvicorn==0.24.0
- httpx==0.25.2
- pytest==7.4.3
- pytest-asyncio==0.23.2

### 3. 启动服务

```bash
cd china_weather_map
bash start.sh
```

或手动启动：

```bash
cd china_weather_map
python -m uvicorn app:app --host 0.0.0.0 --port 7878
```

服务将监听 `0.0.0.0:7878`。

### 4. 访问应用

- 首页: http://localhost:7878/
- 健康检查: http://localhost:7878/health
- 天气查询: http://localhost:7878/api/weather?city=北京

## 测试

```bash
cd china_weather_map
pytest test_app.py -v
```

## API 说明

### GET /
返回交互式中国地图前端页面。

### GET /health
健康检查，返回 `{"status": "ok"}`。

### GET /api/weather?city=城市名
查询指定城市天气信息。

**参数**: `city` (必填) - 中文城市名称

**成功响应** (200):
```json
{
  "city": "北京",
  "city_code": "101010100",
  "weather": "晴",
  "temp": "22℃",
  "wind": "北风 3级",
  "humidity": "45%",
  "detail_url": "http://www.weather.com.cn/weather1d/101010100.shtml"
}
```

**错误响应** (400):
```json
{
  "error": "缺少 city 参数"
}
```

## 部署

### 直接部署

```bash
# 1. 克隆并进入项目
git clone <repo-url>
cd weather_app/china_weather_map

# 2. 安装依赖（建议虚拟环境）
pip install -r requirements.txt

# 3. 启动（前台）
python -m uvicorn app:app --host 0.0.0.0 --port 7878
```

### 后台运行

```bash
nohup python -m uvicorn app:app --host 0.0.0.0 --port 7878 > server.log 2>&1 &
```

### Systemd 服务（推荐生产环境）

创建 `/etc/systemd/system/weather-app.service`：

```ini
[Unit]
Description=China Weather Map App
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/weather_app/china_weather_map
ExecStart=/path/to/venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 7878
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并启用：

```bash
sudo systemctl daemon-reload
sudo systemctl start weather-app
sudo systemctl enable weather-app
```

### Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY china_weather_map/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY china_weather_map/ .
EXPOSE 7878
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7878"]
```

构建并运行：

```bash
docker build -t weather-app .
docker run -d -p 7878:7878 --name weather-app weather-app
```

## 安全特性

- **SSRF 防护**: city 参数仅允许白名单内的中文城市名，拒绝 URL、特殊字符等可疑输入
- **XSS 防护**: 前端使用 textContent 展示动态内容，链接 href 仅允许 weather.com.cn 域名

## 已知限制

1. **天气数据源**: 使用中国天气网社区维护的公开接口 (t.weather.itboy.net)，该接口非官方，可能存在不稳定或限流的情况
2. **城市覆盖**: 当前覆盖所有省级行政区及主要城市的省会，部分地级市可能未覆盖
3. **省份级天气**: 地图悬停显示的是省级天气（省会城市天气），如需更精细的市级天气，可在前端扩展
4. **网络依赖**: 天气查询需要服务器能访问 t.weather.itboy.net，如果网络不通则无法获取天气数据
5. **GeoJSON 数据**: 中国地图数据来源于阿里云 DataV，包含南海诸岛

#!/bin/bash
# 中国地图天气查询 - 一键启动脚本
cd "$(dirname "$0")"

# 安装依赖
pip install -r requirements.txt -q || { echo "依赖安装失败，请检查 requirements.txt"; exit 1; }

# 启动服务，绑定 0.0.0.0:7878
exec python -m uvicorn app:app --host 0.0.0.0 --port 7878

# APK Installer - 设备管理系统

基于 **Tactile Utility** 设计系统的高端设备管理应用，提供优雅的 APK 安装体验。

## 功能特性

- 📱 **设备管理** - 支持多设备连接，实时显示设备型号、ABI、连接状态
- 🚀 **一键安装** - 拖拽或选择 APK 文件，自动静默安装到设备
- 📊 **实时进度** - 显示上传进度、传输速率、剩余时间
- ✅ **安装验证** - 自动验证安装结果，确保成功
- ❌ **错误处理** - 友好的错误提示，便于排查问题
- 📜 **历史记录** - 本地保存安装历史，随时查看
- 🐳 **Docker 部署** - 一键部署，开箱即用

## 设计系统

采用 **Tactile Utility** 美学设计：
- 高端编辑感配色（Traffic Light 状态系统）
- Manrope + Inter 字体组合
- 无边框设计，通过背景色差异区分层级
- 毛玻璃效果和渐变设计

## 环境要求

- Docker
- Docker Compose
- Android 设备（开启 ADB 调试）
- 网络互通

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yao1987825/apk-installer-docker.git
cd apk-installer-docker
```

### 2. 配置设备 IP

编辑 `config.env` 文件，修改 `DEVICE_IP` 为你的 Android 设备 IP：

```env
DEVICE_IP=10.10.10.168
```

### 3. 启动服务

```bash
docker-compose up -d --build
```

服务将在 `http://your-server:6767` 启动。

### 4. 使用方法

1. 打开浏览器访问 `http://your-server:6767`
2. 系统自动检测已连接的 Android 设备
3. 点击设备卡片选择目标设备
4. 拖拽或选择 APK 文件开始上传
5. 等待安装完成

## 项目结构

```
apk-installer-docker/
├── app.py              # FastAPI 后端
├── Dockerfile          # Docker 配置
├── docker-compose.yml  # Docker Compose 配置
├── config.env          # 环境配置
└── templates/          # 前端静态文件
    └── index.html      # 主页面
```

## 后端 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 界面 |
| `/devices` | GET | 获取设备列表 |
| `/device/status` | GET | 获取设备状态 |
| `/upload` | POST | 上传 APK 文件 |
| `/upload-with-progress` | POST | 带进度的上传 |
| `/start-install` | POST | 开始安装 |
| `/progress/{install_id}` | GET | 获取安装进度（SSE） |
| `/health` | GET | 健康检查 |

### 设备列表响应示例

```json
{
  "devices": [
    {
      "serial": "10.10.10.168:5555",
      "model": "Pixel 7 Pro",
      "name": "sdk_gphone64",
      "abi": "arm64-v8a",
      "connected": true
    }
  ],
  "count": 1
}
```

### 设备状态响应示例

```json
{
  "device_ip": "10.10.10.168",
  "connected": true,
  "device_abi": "arm64-v8a",
  "device_model": "Pixel 7 Pro",
  "device_name": "sdk_gphone64",
  "service": "apk-installer"
}
```

## 注意事项

1. Android 设备需开启 USB 调试或无线 ADB
2. 设备与服务器需在同一网络
3. 如遇连接问题，检查防火墙设置
4. APK 文件需要正确签名才能安装
5. 首次连接设备需要在手机上确认授权

## 技术栈

- **后端**: FastAPI + Python
- **前端**: 原生 HTML/CSS/JavaScript
- **设计**: Tactile Utility Design System
- **部署**: Docker

## 许可证

MIT License

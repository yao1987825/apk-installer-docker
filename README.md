# APK Installer

通过 Web 界面向 Android 设备远程安装 APK 应用。

## 功能特性

- 📱 Web 界面上传 APK 文件
- 🚀 支持远程安装到 Android 设备
- 📊 实时进度展示（地铁线路图风格）
- 🔄 支持安装进度恢复（页面刷新不丢失）
- ✅ 安装成功自动验证
- ❌ 安装失败友好提示
- 🐳 Docker 部署支持

## 环境要求

- Docker
- Docker Compose
- Android 设备（开启 ADB 调试）

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
2. 确保 Android 设备已连接并开启 ADB 调试
3. 点击上传区域或拖拽 APK 文件
4. 点击"开始安装"按钮
5. 等待安装完成

## 项目结构

```
apk-installer-docker/
├── app.py              # FastAPI 后端
├── Dockerfile          # Docker 配置
├── docker-compose.yml  # Docker Compose 配置
├── config.env          # 环境配置
├── templates/          # 编译后的前端静态文件
└── frontend/          # Vue 前端源码
    ├── src/
    │   └── App.vue    # 前端组件
    └── package.json
```

## 开发

### 前端开发

```bash
cd frontend
npm install
npm run dev     # 开发模式
npm run build   # 构建生产版本
```

### 后端 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 界面 |
| `/upload` | POST | 上传 APK 文件 |
| `/start-install` | POST | 开始安装 |
| `/progress/{install_id}` | GET | 获取安装进度（SSE） |
| `/device/status` | GET | 设备状态 |
| `/health` | GET | 健康检查 |

## 注意事项

1. Android 设备需开启 USB 调试模式
2. 设备与服务器需在同一网络
3. 如遇连接问题，检查防火墙设置
4. APK 文件需要正确签名才能安装

## 许可证

MIT License

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import subprocess
import os
import uuid
import logging
import time
import threading
import re
import hashlib
from logging.handlers import RotatingFileHandler

app = FastAPI(title="APK Installer")

DEVICE_IP = os.environ.get("DEVICE_IP", "10.10.10.168")
UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LOG_FILE = "/data/logs/app.log"
os.makedirs("/data/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

_lock = threading.Lock()
_device_cache = {"connected": False, "device_abi": None, "last_check": 0}
CACHE_TTL = 60
_last_adb_restart = 0

_progress_data = {}


def restart_adb():
    global _last_adb_restart
    current_time = time.time()
    if current_time - _last_adb_restart < 30:
        return False

    try:
        subprocess.run(["adb", "kill-server"], capture_output=True, timeout=5)
        time.sleep(0.5)
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=10)
        _last_adb_restart = current_time
        logger.info("ADB server restarted")
        return True
    except Exception as e:
        logger.error(f"Failed to restart ADB: {e}")
        return False


def reconnect_device():
    try:
        subprocess.run(["adb", "disconnect", DEVICE_IP], capture_output=True, timeout=5)
        result = subprocess.run(
            ["adb", "connect", f"{DEVICE_IP}:5555"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip().lower()
        logger.info(f"Reconnect output: {output}")
        time.sleep(1)
        return "connected" in output or "already connected" in output
    except Exception as e:
        logger.error(f"Failed to reconnect: {e}")
        return False


def ensure_device_connected():
    global _device_cache
    current_time = time.time()

    with _lock:
        if (
            current_time - _device_cache["last_check"] < CACHE_TTL
            and _device_cache["connected"]
        ):
            return _device_cache["connected"], _device_cache["device_abi"]

        try:
            result = subprocess.run(
                ["adb", "-s", f"{DEVICE_IP}:5555", "get-state"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            state = result.stdout.strip().lower()
            logger.info(f"Device state: {state}")

            if "device" in state:
                abi_result = subprocess.run(
                    [
                        "adb",
                        "-s",
                        f"{DEVICE_IP}:5555",
                        "shell",
                        "getprop",
                        "ro.product.cpu.abi",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                abi = abi_result.stdout.strip() if abi_result.returncode == 0 else None

                _device_cache = {
                    "connected": True,
                    "device_abi": abi,
                    "last_check": current_time,
                }
                logger.info(f"Device connected: True, ABI: {abi}")
                return True, abi

            elif not state or state == "" or "no devices" in state:
                logger.warning(
                    f"Device state empty: '{state}', attempting to reconnect..."
                )
                restart_adb()
                reconnect_device()

                result = subprocess.run(
                    ["adb", "-s", f"{DEVICE_IP}:5555", "get-state"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                state = result.stdout.strip().lower()

                if "device" in state:
                    abi_result = subprocess.run(
                        [
                            "adb",
                            "-s",
                            f"{DEVICE_IP}:5555",
                            "shell",
                            "getprop",
                            "ro.product.cpu.abi",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    abi = (
                        abi_result.stdout.strip()
                        if abi_result.returncode == 0
                        else None
                    )

                    _device_cache = {
                        "connected": True,
                        "device_abi": abi,
                        "last_check": current_time,
                    }
                    logger.info(f"Device reconnected after fix: True, ABI: {abi}")
                    return True, abi

            elif "unauthorized" in state or "offline" in state:
                logger.warning(f"Device {state}, attempting to reconnect...")
                restart_adb()
                reconnect_device()

                result = subprocess.run(
                    ["adb", "-s", f"{DEVICE_IP}:5555", "get-state"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                state = result.stdout.strip().lower()

                if "device" in state:
                    abi_result = subprocess.run(
                        [
                            "adb",
                            "-s",
                            f"{DEVICE_IP}:5555",
                            "shell",
                            "getprop",
                            "ro.product.cpu.abi",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    abi = (
                        abi_result.stdout.strip()
                        if abi_result.returncode == 0
                        else None
                    )

                    _device_cache = {
                        "connected": True,
                        "device_abi": abi,
                        "last_check": current_time,
                    }
                    logger.info(f"Device reconnected after fix: True, ABI: {abi}")
                    return True, abi

            _device_cache = {
                "connected": False,
                "device_abi": None,
                "last_check": current_time,
            }
            logger.info(f"Device not connected: {state}")
            return False, None

        except Exception as e:
            logger.error(f"Device check error: {e}")
            _device_cache = {
                "connected": False,
                "device_abi": None,
                "last_check": current_time,
            }
            return False, None


def get_package_name(apk_path):
    try:
        result = subprocess.run(
            ["aapt", "dump", "badging", apk_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.split("\n"):
            if "package: name=" in line:
                match = re.search(r"name='([^']+)'", line)
                if match:
                    return match.group(1)
    except:
        pass
    return None


def run_install(apk_path, install_id):
    install_result = {"success": False, "output": ""}

    def send_progress(message, percentage):
        if percentage == -1:
            _progress_data[install_id] = {
                "message": message,
                "percentage": -1,
                "done": True,
            }
            logger.info(f"Progress: {message} ({percentage}%)")
            return

        current = _progress_data.get(install_id, {}).get("percentage", 0)
        if percentage > current:
            _progress_data[install_id] = {
                "message": message,
                "percentage": percentage,
                "done": False,
            }
            logger.info(f"Progress: {message} ({percentage}%)")

    def install_thread():
        nonlocal install_result
        try:
            process = subprocess.Popen(
                ["adb", "-s", f"{DEVICE_IP}:5555", "install", "-r", apk_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output_lines.append(line)
                    logger.info(f"ADB: {line.strip()}")
                    if "pushing" in line.lower() or "pushed" in line.lower():
                        send_progress("正在传输APK...", 50)
                    elif "installing" in line.lower():
                        send_progress("正在安装APK...", 70)
                    elif "Success" in line:
                        send_progress("正在验证安装...", 85)

                        pkg_name = get_package_name(apk_path)
                        verified = False

                        if pkg_name:
                            for attempt in range(10):
                                time.sleep(3)
                                check = subprocess.run(
                                    [
                                        "adb",
                                        "-s",
                                        f"{DEVICE_IP}:5555",
                                        "shell",
                                        "pm",
                                        "list",
                                        "packages",
                                    ],
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                )
                                if pkg_name in check.stdout:
                                    send_progress(f"验证成功 ({attempt + 1}/10)", 90)
                                    verified = True
                                    break
                                send_progress(f"等待设备响应... ({attempt + 1}/10)", 85)

                        time.sleep(15)
                        send_progress("安装完成", 100)
                        time.sleep(5)
                        install_result["success"] = True
                    elif (
                        "Failed" in line or "Error" in line or "failure" in line.lower()
                    ):
                        send_progress("安装失败", -1)
                        install_result["success"] = False

            stdout, stderr = process.communicate()
            full_output = "".join(output_lines) + stderr

            if not install_result.get("success"):
                if "Success" in full_output:
                    send_progress("安装完成", 100)
                    install_result["success"] = True
                elif "Failed" in full_output or "Error" in full_output:
                    send_progress("安装失败", -1)
                    install_result["success"] = False

            install_result["output"] = full_output

        except Exception as e:
            logger.error(f"Install error: {e}")
            send_progress(f"安装失败: {str(e)}", -1)
            install_result["success"] = False
        finally:
            _progress_data[install_id]["done"] = True
            if os.path.exists(apk_path):
                try:
                    os.remove(apk_path)
                except:
                    pass

    try:
        send_progress("正在连接设备...", 10)

        connected, device_abi = ensure_device_connected()

        if not connected:
            send_progress("设备未连接", -1)
            _progress_data[install_id]["done"] = True
            return {"success": False, "error": "Device not connected"}

        send_progress("正在传输APK...", 30)

        thread = threading.Thread(target=install_thread)
        thread.start()

        stages = [
            (2, "正在传输APK...", 40),
            (4, "正在传输APK...", 50),
            (6, "正在安装APK...", 60),
            (8, "正在安装APK...", 70),
            (10, "正在完成安装...", 80),
        ]

        for wait_secs, msg, min_pct in stages:
            time.sleep(wait_secs)
            if _progress_data[install_id].get("done"):
                break
            current_pct = _progress_data[install_id].get("percentage", 0)
            if current_pct >= 85:
                break
            if current_pct < min_pct and current_pct < 85:
                send_progress(msg, min_pct)

        thread.join(timeout=300)

        if not _progress_data[install_id].get("done"):
            current_pct = _progress_data[install_id].get("percentage", 0)
            if current_pct < 100:
                send_progress("安装完成", 100)
            _progress_data[install_id]["done"] = True

        return {"success": True, "message": "Installation completed"}

    except Exception as e:
        _progress_data[install_id]["done"] = True
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(apk_path):
            try:
                os.remove(apk_path)
            except:
                pass


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("/app/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.mount("/assets", StaticFiles(directory="/app/templates/assets"), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "apk-installer"}


@app.get("/device/status")
async def device_status():
    connected, abi = ensure_device_connected()

    return {
        "device_ip": DEVICE_IP,
        "connected": connected,
        "device_abi": abi,
        "service": "apk-installer",
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only APK files are allowed")

    content = await file.read()
    total_size = len(content)

    file_hash = hashlib.md5(content[: 1024 * 100]).hexdigest()
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")

    for existing_file in os.listdir(UPLOAD_FOLDER):
        if existing_file.endswith(".apk") and existing_file.startswith(file_hash[:8]):
            existing_path = os.path.join(UPLOAD_FOLDER, existing_file)
            logger.info(f"File already exists, using: {existing_path}")
            return {
                "install_id": str(uuid.uuid4()),
                "apk_path": existing_path,
                "filename": file.filename,
                "size": total_size,
                "cached": True,
            }

    install_id = str(uuid.uuid4())
    apk_filename = f"{file_hash[:8]}_{install_id[:8]}_{safe_filename}"
    apk_path = os.path.join(UPLOAD_FOLDER, apk_filename)

    with open(apk_path, "wb") as f:
        f.write(content)

    logger.info(f"File uploaded: {apk_path}, size: {total_size} bytes")

    return {
        "install_id": install_id,
        "apk_path": apk_path,
        "filename": file.filename,
        "size": total_size,
        "cached": False,
    }


@app.post("/upload-with-progress")
async def upload_file_with_progress(file: UploadFile = File(...)):
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only APK files are allowed")

    install_id = str(uuid.uuid4())
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")
    apk_filename = f"{install_id}_{safe_filename}"
    apk_path = os.path.join(UPLOAD_FOLDER, apk_filename)

    total_size = 0
    chunk_size = 64 * 1024

    _progress_data[install_id] = {
        "message": "正在读取文件...",
        "percentage": 0,
        "done": False,
    }

    with open(apk_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            total_size += len(chunk)
            _progress_data[install_id] = {
                "message": f"上传中... {total_size / 1024 / 1024:.1f} MB",
                "percentage": 50,
                "done": False,
            }

    _progress_data[install_id] = {
        "message": "文件上传完成",
        "percentage": 50,
        "done": False,
    }

    logger.info(f"File uploaded: {apk_path}, size: {total_size} bytes")

    return {
        "install_id": install_id,
        "apk_path": apk_path,
        "filename": file.filename,
        "size": total_size,
    }


@app.post("/start-install")
async def start_install(data: dict):
    install_id = data.get("install_id")
    apk_path = data.get("apk_path")

    if not install_id or not apk_path:
        raise HTTPException(status_code=400, detail="Missing install_id or apk_path")

    logger.info(f"Starting install: {install_id}")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_install, apk_path, install_id)

    return result


@app.get("/progress/{install_id}")
async def get_progress(install_id: str):
    async def event_stream():
        while True:
            if install_id in _progress_data:
                data = _progress_data[install_id]
                yield f"data: {data['message']}|{data['percentage']}\n\n"
                if data.get("done"):
                    await asyncio.sleep(10)
                    if install_id in _progress_data:
                        del _progress_data[install_id]
                    break
            else:
                yield f"data: waiting|0\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6767)

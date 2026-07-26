import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.pipeline import StreamSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str, token: str = ""):
    await websocket.accept()
    
    session = StreamSession(device_id)
    
    await websocket.send_json({
        "type": "connected",
        "session_id": session.session_id,
        "device_id": device_id,
        "timestamp": session.created_at.isoformat()
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            msg_type = data.get("type", "")
            msg_data = data.get("data", {})
            
            frame_size = 0
            if msg_type == "frame" and msg_data.get("image"):
                frame_size = len(msg_data["image"])
            elif msg_type == "sensor_data" and msg_data.get("video_frame"):
                frame_size = len(msg_data["video_frame"])
            elif data.get("video_frame"):
                frame_size = len(data["video_frame"])
            
            logger.info(f"[WS] 收到消息 - device_id={device_id}, type={msg_type}, frame_size={frame_size} bytes")
            
            if msg_type == "frame":
                b64 = msg_data.get("image", "")
                logger.info(f"[WS] 开始处理帧 - device_id={device_id}, b64_len={len(b64)}")
                try:
                    result = await session.process_frame(b64)
                    logger.info(f"[WS] process_frame 完成 - device_id={device_id}")
                except Exception as e:
                    import traceback
                    logger.error(f"[WS] process_frame 异常: {e}")
                    logger.error(f"完整堆栈:\n{traceback.format_exc()}")
                    continue
                
                det_count = len(result.get("detections", []))
                logger.info(f"[WS] 返回结果 - device_id={device_id}, fps={result.get('fps')}, detections={det_count}")
                
                try:
                    await websocket.send_json(result)
                    logger.info(f"[WS] send_json 成功")
                except Exception as e:
                    import traceback
                    logger.error(f"[WS] send_json 异常: {e}")
                    logger.error(f"result类型检查: {type(result)}")
                    logger.error(f"完整堆栈:\n{traceback.format_exc()}")
            
            elif msg_type == "sensor_data":
                if msg_data.get("video_frame"):
                    b64 = msg_data["video_frame"]
                    result = await session.process_frame(b64)
                    det_count = len(result.get("detections", []))
                    logger.info(f"[WS] 返回结果 - device_id={device_id}, fps={result.get('fps')}, detections={det_count}")
                    await websocket.send_json(result)
                else:
                    await _process_sensor_only(websocket, session, msg_data)
            
            else:
                base64_image = data.get("video_frame", "")
                if base64_image:
                    result = await session.process_frame(base64_image)
                    det_count = len(result.get("detections", []))
                    logger.info(f"[WS] 返回结果 - device_id={device_id}, fps={result.get('fps')}, detections={det_count}")
                    await websocket.send_json(result)
    
    except WebSocketDisconnect:
        logger.info(f"设备 {device_id} 断开连接")
    except Exception as e:
        import traceback
        logger.error(f"WebSocket处理异常: {e}")
        logger.error(f"完整堆栈:\n{traceback.format_exc()}")


async def _process_sensor_only(websocket: WebSocket, session: StreamSession, msg_data: dict):
    result = {
        "type": "sensor_result",
        "frame_id": session.frame_count,
        "fps": 0,
        "detections": [],
        "blind_road_status": "not_found",
        "warning": {"level": 0, "tts_text": "", "vibration": "none"},
        "route": None,
        "perf": {},
        "timestamp": session.frame_count * 1000
    }
    await websocket.send_json(result)
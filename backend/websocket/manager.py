import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"设备 {device_id} 连接成功")
    
    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"设备 {device_id} 断开连接")
    
    async def send_personal_message(self, message: dict, device_id: str):
        if device_id in self.active_connections:
            try:
                await self.active_connections[device_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(device_id)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for device_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(device_id)
        
        for device_id in disconnected:
            self.disconnect(device_id)


try:
    manager
except NameError:
    manager = ConnectionManager()
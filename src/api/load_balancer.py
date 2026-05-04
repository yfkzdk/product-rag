from typing import List, Dict, Optional
from src.config import get_settings
import random
import logging

logger = logging.getLogger(__name__)


class LoadBalancer:
    """负载均衡器"""

    def __init__(self, servers: Optional[List[str]] = None):
        """初始化"""
        self._servers = servers or []
        self._current_index = 0
        self._weights = {s: 1 for s in self._servers}

    def get_next_server(self) -> Optional[str]:
        """轮询获取下一个服务器"""
        if not self._servers:
            return None

        server = self._servers[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._servers)
        return server

    def get_weighted_server(self) -> Optional[str]:
        """加权轮询获取服务器"""
        if not self._servers:
            return None

        total_weight = sum(self._weights.values())
        rand = random.uniform(0, total_weight)

        cumulative = 0
        for server, weight in self._weights.items():
            cumulative += weight
            if rand <= cumulative:
                return server

        return self._servers[0]

    def add_server(self, server: str, weight: int = 1):
        """添加服务器"""
        if server not in self._servers:
            self._servers.append(server)
            self._weights[server] = weight

    def remove_server(self, server: str):
        """移除服务器"""
        if server in self._servers:
            self._servers.remove(server)
            del self._weights[server]
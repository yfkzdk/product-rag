"""
自动扩缩容

基于负载的自动扩缩容
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class AutoScaler:
    """自动扩缩容器"""

    def __init__(self, min_instances: int = 1, max_instances: int = 10):
        """
        初始化自动扩缩容器

        Args:
            min_instances: 最小实例数
            max_instances: 最大实例数
        """
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.current_instances = min_instances
        self.scaling_rules = {
            "scale_up_threshold": 0.8,  # CPU使用率阈值
            "scale_down_threshold": 0.3,
            "cooldown_period": 300  # 冷却期（秒）
        }
        self.last_scale_time = 0
        logger.info(f"Auto scaler initialized: min={min_instances}, max={max_instances}")

    def evaluate_scaling(self, metrics: Dict) -> str:
        """
        评估是否需要扩缩容

        Args:
            metrics: 性能指标

        Returns:
            扩缩容决策
        """
        import time

        current_time = time.time()

        # 检查冷却期
        if current_time - self.last_scale_time < self.scaling_rules["cooldown_period"]:
            logger.debug("In cooldown period, skipping scaling")
            return "none"

        cpu_usage = metrics.get("cpu_usage", 0.0)
        memory_usage = metrics.get("memory_usage", 0.0)
        request_rate = metrics.get("request_rate", 0.0)

        # 扩容条件
        if cpu_usage > self.scaling_rules["scale_up_threshold"]:
            if self.current_instances < self.max_instances:
                self.current_instances += 1
                self.last_scale_time = current_time
                logger.info(f"Scaling up: {self.current_instances - 1} -> {self.current_instances}")
                return "scale_up"

        # 缩容条件
        if cpu_usage < self.scaling_rules["scale_down_threshold"]:
            if self.current_instances > self.min_instances:
                self.current_instances -= 1
                self.last_scale_time = current_time
                logger.info(f"Scaling down: {self.current_instances + 1} -> {self.current_instances}")
                return "scale_down"

        return "none"

    def get_current_instances(self) -> int:
        """
        获取当前实例数

        Returns:
            实例数
        """
        return self.current_instances

    def set_instances(self, count: int) -> None:
        """
        手动设置实例数

        Args:
            count: 实例数
        """
        if self.min_instances <= count <= self.max_instances:
            self.current_instances = count
            logger.info(f"Instances set to: {count}")
        else:
            logger.warning(f"Invalid instance count: {count}")

    def get_scaling_metrics(self) -> Dict:
        """
        获取扩缩容指标

        Returns:
            指标数据
        """
        return {
            "current_instances": self.current_instances,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "scaling_rules": self.scaling_rules
        }


# 全局实例
auto_scaler = AutoScaler()

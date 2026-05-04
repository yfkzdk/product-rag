"""
告警系统

基于指标的自动告警
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class AlertingSystem:
    """告警系统"""

    def __init__(self):
        """初始化告警系统"""
        self.alert_rules = {
            "P0": {
                "faithfulness_threshold": 0.6,
                "latency_threshold": 1.0,
                "actions": ["暂停服务", "通知管理员"]
            },
            "P1": {
                "faithfulness_threshold": 0.7,
                "latency_threshold": 0.8,
                "actions": ["调整参数", "增加缓存"]
            },
            "P2": {
                "faithfulness_threshold": 0.8,
                "latency_threshold": 0.5,
                "actions": ["记录日志", "监控趋势"]
            }
        }
        logger.info("Alerting system initialized")

    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """
        检查告警

        Args:
            metrics: 指标数据

        Returns:
            告警列表
        """
        alerts = []

        # 检查忠实度
        faithfulness = metrics.get("faithfulness", 1.0)
        for level, config in self.alert_rules.items():
            if faithfulness < config["faithfulness_threshold"]:
                alerts.append({
                    "level": level,
                    "type": "faithfulness_low",
                    "value": faithfulness,
                    "threshold": config["faithfulness_threshold"],
                    "actions": config["actions"]
                })
                break

        # 检查延迟
        latency = metrics.get("latency", 0.0)
        for level, config in self.alert_rules.items():
            if latency > config["latency_threshold"]:
                alerts.append({
                    "level": level,
                    "type": "latency_high",
                    "value": latency,
                    "threshold": config["latency_threshold"],
                    "actions": config["actions"]
                })
                break

        logger.info(f"Checked alerts: {len(alerts)} alerts")
        return alerts

    def send_alert(self, alert: Dict) -> None:
        """
        发送告警

        Args:
            alert: 告警信息
        """
        logger.warning(f"ALERT [{alert['level']}]: {alert['type']} = {alert['value']} (threshold={alert['threshold']})")
        logger.info(f"Actions: {alert['actions']}")


# 全局实例
alerting_system = AlertingSystem()
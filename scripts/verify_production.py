"""
生产部署验证

验证生产环境部署就绪状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.health_check import HealthChecker
from src.api.load_balancer import LoadBalancer
from src.api.auto_scaler import AutoScaler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_production_readiness():
    """验证生产就绪状态"""
    logger.info("=" * 60)
    logger.info("Production Deployment Verification")
    logger.info("=" * 60)

    checks = []

    # 1. 健康检查
    logger.info("\n1. Health Check")
    checker = HealthChecker()
    checker.register_check("database", checker.check_database)
    checker.register_check("cache", checker.check_cache)
    checker.register_check("vector_store", checker.check_vector_store)

    health = checker.run_all_checks()
    checks.append(("Health Check", health["overall_status"] == "healthy"))
    logger.info(f"   Status: {health['overall_status']}")

    # 2. 负载均衡
    logger.info("\n2. Load Balancer")
    lb = LoadBalancer(["server1:8000", "server2:8000"])
    server = lb.get_next_server()
    checks.append(("Load Balancer", server is not None))
    logger.info(f"   Server: {server}")

    # 3. 自动扩缩容
    logger.info("\n3. Auto Scaler")
    scaler = AutoScaler(min_instances=2, max_instances=10)
    metrics = scaler.get_scaling_metrics()
    checks.append(("Auto Scaler", metrics["current_instances"] >= metrics["min_instances"]))
    logger.info(f"   Instances: {metrics['current_instances']}")

    # 4. Docker配置
    logger.info("\n4. Docker Configuration")
    dockerfile_exists = os.path.exists("docker/Dockerfile")
    checks.append(("Docker Config", dockerfile_exists))
    logger.info(f"   Dockerfile: {'Found' if dockerfile_exists else 'Missing'}")

    # 5. CI/CD配置
    logger.info("\n5. CI/CD Pipeline")
    cicd_exists = os.path.exists(".github/workflows/deploy.yml")
    checks.append(("CI/CD Pipeline", cicd_exists))
    logger.info(f"   Pipeline: {'Configured' if cicd_exists else 'Missing'}")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("Production Readiness Summary")
    logger.info("=" * 60)

    all_passed = all(check[1] for check in checks)

    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {name}")

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 Production Deployment Ready")
    else:
        logger.info("⚠️ Production Deployment Not Ready")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = verify_production_readiness()
    sys.exit(0 if success else 1)
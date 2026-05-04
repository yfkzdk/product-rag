"""
Month 6 单元测试

测试缓存优化、索引优化、负载均衡、健康检查、自动扩缩容
"""
import pytest


# ===== 缓存优化测试 =====

def test_advanced_cache_init():
    """测试高级缓存初始化"""
    from src.cache.advanced_cache import AdvancedCache

    cache = AdvancedCache()
    assert cache is not None


def test_advanced_cache_set_get():
    """测试缓存设置和获取"""
    from src.cache.advanced_cache import AdvancedCache

    cache = AdvancedCache()

    # 设置缓存
    cache.set("key1", "value1")

    # 获取缓存
    value = cache.get("key1")
    assert value == "value1"


def test_advanced_cache_stats():
    """测试缓存统计"""
    from src.cache.advanced_cache import AdvancedCache

    cache = AdvancedCache()

    # 设置和获取
    cache.set("key1", "value1")
    cache.get("key1")
    cache.get("key2")  # miss

    stats = cache.get_stats()
    assert stats["hit_count"] == 1
    assert stats["miss_count"] == 1


# ===== 索引优化测试 =====

def test_index_optimizer_init():
    """测试索引优化器初始化"""
    from src.storage.index_optimizer import IndexOptimizer

    optimizer = IndexOptimizer()
    assert optimizer is not None


def test_index_optimizer_analyze():
    """测试查询模式分析"""
    from src.storage.index_optimizer import IndexOptimizer

    optimizer = IndexOptimizer()

    queries = ["PROD-001功率", "故障E001", "PROD-001 PROD-002兼容"]
    patterns = optimizer.analyze_query_patterns(queries)

    assert patterns["product_queries"] == 2
    assert patterns["fault_queries"] == 1


def test_index_optimizer_recommend():
    """测试索引推荐"""
    from src.storage.index_optimizer import IndexOptimizer

    optimizer = IndexOptimizer()

    patterns = {"product_queries": 15, "fault_queries": 5, "compatibility_queries": 3}
    recommendations = optimizer.recommend_indexes(patterns)

    assert len(recommendations) > 0


# ===== 负载均衡测试 =====

def test_load_balancer_init():
    """测试负载均衡器初始化"""
    from src.api.load_balancer import LoadBalancer

    lb = LoadBalancer(["server1", "server2"])
    assert lb is not None


def test_load_balancer_round_robin():
    """测试轮询负载均衡"""
    from src.api.load_balancer import LoadBalancer

    lb = LoadBalancer(["server1", "server2"])

    server1 = lb.get_next_server()
    server2 = lb.get_next_server()
    server3 = lb.get_next_server()

    assert server1 == "server1"
    assert server2 == "server2"
    assert server3 == "server1"


# ===== 健康检查测试 =====

def test_health_checker_init():
    """测试健康检查器初始化"""
    from src.api.health_check import HealthChecker

    checker = HealthChecker()
    assert checker is not None


def test_health_checker_run():
    """测试健康检查运行"""
    from src.api.health_check import HealthChecker

    checker = HealthChecker()
    checker.register_check("test", lambda: True)

    result = checker.run_check("test")
    assert result["status"] == "healthy"


def test_health_checker_all():
    """测试所有健康检查"""
    from src.api.health_check import HealthChecker

    checker = HealthChecker()
    checker.register_check("test1", lambda: True)
    checker.register_check("test2", lambda: False)

    results = checker.run_all_checks()
    assert results["overall_status"] == "unhealthy"


# ===== 自动扩缩容测试 =====

def test_auto_scaler_init():
    """测试自动扩缩容器初始化"""
    from src.api.auto_scaler import AutoScaler

    scaler = AutoScaler()
    assert scaler is not None


def test_auto_scaler_evaluate():
    """测试扩缩容评估"""
    from src.api.auto_scaler import AutoScaler

    scaler = AutoScaler(min_instances=1, max_instances=5)
    # 设置冷却期为0以允许连续扩缩容
    scaler.scaling_rules["cooldown_period"] = 0

    # 高负载
    decision = scaler.evaluate_scaling({"cpu_usage": 0.9})
    assert decision == "scale_up"

    # 低负载
    decision = scaler.evaluate_scaling({"cpu_usage": 0.2})
    assert decision == "scale_down"


def test_auto_scaler_instances():
    """测试实例数管理"""
    from src.api.auto_scaler import AutoScaler

    scaler = AutoScaler(min_instances=1, max_instances=5)

    scaler.set_instances(3)
    assert scaler.get_current_instances() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
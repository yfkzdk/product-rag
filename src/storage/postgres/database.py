from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Declarative base has no connection side effects
Base = declarative_base()

_engine = None
_SessionLocal = None
_seeded = False


def _init_engine():
    """延迟初始化数据库引擎"""
    global _engine, _SessionLocal, _seeded
    if _engine is None:
        settings = get_settings()
        if settings.DEMO_MODE:
            import os
            db_path = os.path.abspath(settings.DEMO_DB_PATH)
            _engine = create_engine(
                f"sqlite:///{db_path}",
                echo=settings.DEBUG,
                connect_args={"check_same_thread": False},
                json_serializer=lambda obj: __import__("json").dumps(obj, ensure_ascii=False),
            )
            # 确保 SQLite 使用 UTF-8
            @__import__("sqlalchemy").event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                dbapi_connection.execute("PRAGMA encoding = 'UTF-8'")
                dbapi_connection.execute("PRAGMA journal_mode = WAL")
        else:
            _engine = create_engine(
                settings.POSTGRES_URL,
                pool_size=settings.POSTGRES_POOL_SIZE,
                echo=settings.DEBUG
            )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

        if settings.DEMO_MODE and not _seeded:
            _seed_demo_data()
            _seeded = True


def _seed_demo_data():
    """向SQLite注入示例数据（如已存在则跳过）"""
    from src.storage.postgres.models import Product, Fault, CompatibilityMatrix, Severity
    from src.storage.postgres.models import Base as ModelsBase
    ModelsBase.metadata.create_all(_engine)

    session = _SessionLocal()
    try:
        # 检查是否已有数据
        existing = session.query(Product).count()
        if existing > 0:
            logger.info(f"Demo data already seeded ({existing} products), skipping")
            session.close()
            return

        # Products
        products = [
            Product(product_code="PROD-001", name="智能温控器 X1", category="温控设备",
                    description="高精度智能温控器，支持PID调节和远程监控",
                    specifications={"power": "220V/50Hz", "temp_range": "-20°C~80°C", "accuracy": "±0.5°C", "weight": "0.8kg", "protection": "IP65"}),
            Product(product_code="PROD-002", name="工业电源模块 P200", category="电源模块",
                    description="200W工业级AC-DC电源模块，宽电压输入",
                    specifications={"input": "85-264VAC", "output": "24VDC/8.3A", "efficiency": "92%", "weight": "1.2kg", "mtbf": "500000h"}),
            Product(product_code="PROD-003", name="多协议网关 GW-01", category="通信设备",
                    description="支持Modbus/Profibus/EtherNet/IP的多协议工业网关",
                    specifications={"protocols": "Modbus RTU/TCP, Profibus DP, EtherNet/IP", "ports": "2xRJ45, 1xRS485", "power": "12VDC/0.5A"}),
            Product(product_code="PROD-004", name="伺服驱动器 SD-200", category="驱动设备",
                    description="200W数字伺服驱动器，支持位置/速度/转矩控制",
                    specifications={"power": "200W", "voltage": "220VAC", "current": "1.5A", "encoder": "2500ppr"}),
            Product(product_code="PROD-005", name="压力变送器 PT-100", category="传感器",
                    description="高精度压力变送器，4-20mA输出",
                    specifications={"range": "0-100MPa", "output": "4-20mA", "accuracy": "0.1%FS", "temp_range": "-40°C~85°C"}),
        ]
        session.add_all(products)
        session.flush()

        # Faults — product_id maps to the flushed product IDs
        faults = [
            Fault(fault_code="E001", symptom="设备无法启动", description="上电后指示灯不亮，设备无响应",
                  root_cause="电源模块损坏或输入电压异常", severity=Severity.CRITICAL,
                  solution="1. 检查输入电源是否正常（220V±10%）\n2. 检查保险丝是否熔断\n3. 更换电源模块", product_id=products[0].id),
            Fault(fault_code="E002", symptom="温度读数偏差过大", description="显示温度与实际温度偏差超过5°C",
                  root_cause="传感器老化或接线松动", severity=Severity.HIGH,
                  solution="1. 检查传感器接线是否牢固\n2. 执行温度校准程序\n3. 若偏差持续，更换传感器", product_id=products[0].id),
            Fault(fault_code="E003", symptom="输出电压不稳定", description="输出24V电压波动超过±5%",
                  root_cause="滤波电容老化或负载功率超限", severity=Severity.HIGH,
                  solution="1. 检查负载功率是否超过额定值\n2. 测量输出端纹波\n3. 更换滤波电容或整个模块", product_id=products[1].id),
            Fault(fault_code="E004", symptom="通信中断", description="网关与上位机通信频繁断开",
                  root_cause="网络配置错误或电磁干扰", severity=Severity.MEDIUM,
                  solution="1. 检查IP地址和子网掩码配置\n2. 更换屏蔽网线\n3. 检查现场是否有强电磁干扰源", product_id=products[2].id),
            Fault(fault_code="E005", symptom="驱动器过载报警", description="伺服驱动器频繁报OL（过载）故障",
                  root_cause="机械负载过大或加速度设置过高", severity=Severity.HIGH,
                  solution="1. 检查机械传动部分是否有卡滞\n2. 降低加速度参数\n3. 确认电机功率是否匹配负载", product_id=products[3].id),
            Fault(fault_code="E006", symptom="压力信号为零", description="变送器输出恒为4mA（零点）",
                  root_cause="传感器膜片损坏或引压管堵塞", severity=Severity.MEDIUM,
                  solution="1. 检查引压管是否堵塞\n2. 确认工艺阀门是否打开\n3. 更换传感器膜片", product_id=products[4].id),
        ]
        session.add_all(faults)
        session.flush()

        # Compatibility — uses product IDs from flushed objects
        compat = [
            CompatibilityMatrix(product_a_id=products[0].id, product_b_id=products[1].id, compatibility_type="compatible",
                                confidence=0.95, notes="温控器X1可通过电源模块P200供电，已验证"),
            CompatibilityMatrix(product_a_id=products[0].id, product_b_id=products[2].id, compatibility_type="compatible",
                                confidence=0.90, notes="温控器X1支持通过网关GW-01上云"),
            CompatibilityMatrix(product_a_id=products[1].id, product_b_id=products[3].id, compatibility_type="partial",
                                confidence=0.70, notes="电源模块P200可驱动SD-200但功率接近上限，建议预留20%余量"),
            CompatibilityMatrix(product_a_id=products[2].id, product_b_id=products[4].id, compatibility_type="incompatible",
                                confidence=0.95, notes="网关GW-01不支持模拟量输入，无法直接连接PT-100"),
            CompatibilityMatrix(product_a_id=products[0].id, product_b_id=products[4].id, compatibility_type="compatible",
                                confidence=0.85, notes="温控器X1可使用PT-100作为外部温度输入"),
        ]
        session.add_all(compat)

        session.commit()
        logger.info(f"Demo data seeded: {len(products)} products, {len(faults)} faults, {len(compat)} compatibility entries")
    except Exception as e:
        session.rollback()
        logger.warning(f"Demo data seed failed (non-fatal): {e}")
    finally:
        session.close()


def get_engine():
    """获取数据库引擎（延迟初始化）"""
    _init_engine()
    return _engine


def get_session_local():
    """获取会话工厂（延迟初始化）"""
    _init_engine()
    return _SessionLocal


def get_db():
    """获取数据库会话"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
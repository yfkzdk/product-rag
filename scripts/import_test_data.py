"""
测试数据导入脚本

导入产品和故障到数据库和向量库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.storage.postgres.database import get_session_local
from src.storage.postgres.models import Product, Fault, CompatibilityMatrix, ManualChunk, Severity
from src.storage.milvus.client import get_milvus_client
from src.embeddings.bge_embedder import get_encoder
from src.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Realistic product data
PRODUCTS = [
    {
        "product_code": "CTL-001",
        "name": "智能控制器X1",
        "category": "控制器",
        "description": "高性能工业智能控制器，支持多协议通信",
        "specifications": {
            "power": "220V AC",
            "weight": "1.2kg",
            "dimensions": "200×100×50mm",
            "working_temp": "-10°C ~ 60°C",
            "protection_level": "IP65",
            "communication": ["Modbus RTU", "CAN", "Ethernet"]
        }
    },
    {
        "product_code": "CTL-002",
        "name": "PLC控制器A3",
        "category": "控制器",
        "description": "可编程逻辑控制器，适用于自动化生产线",
        "specifications": {
            "power": "24V DC",
            "weight": "0.8kg",
            "dimensions": "150×80×40mm",
            "io_channels": 16,
            "communication": ["RS485", "Profibus"]
        }
    },
    {
        "product_code": "SEN-001",
        "name": "温度传感器T200",
        "category": "传感器",
        "description": "高精度工业温度传感器",
        "specifications": {
            "range": "-20°C ~ 200°C",
            "accuracy": "±0.5°C",
            "response_time": "100ms",
            "output_signal": "4-20mA",
            "protection_level": "IP67"
        }
    },
    {
        "product_code": "SEN-002",
        "name": "压力传感器P100",
        "category": "传感器",
        "description": "工业压力传感器，适用于液压系统",
        "specifications": {
            "range": "0 ~ 10MPa",
            "accuracy": "±0.25%",
            "output_signal": "0-10V",
            "connection": "M12"
        }
    },
    {
        "product_code": "ACT-001",
        "name": "电动执行器E50",
        "category": "执行器",
        "description": "高性能电动执行器，支持远程控制",
        "specifications": {
            "torque": "500Nm",
            "speed": "10rpm",
            "voltage": "380V AC",
            "control_mode": "模拟量/数字量"
        }
    },
    {
        "product_code": "MOD-001",
        "name": "通信模块C4",
        "category": "模块",
        "description": "多协议通信转换模块",
        "specifications": {
            "protocols": ["Modbus RTU", "Modbus TCP", "CANopen"],
            "power_consumption": "5W",
            "channels": 4
        }
    },
    {
        "product_code": "MOD-002",
        "name": "电源模块PS24",
        "category": "模块",
        "description": "工业级24V电源模块",
        "specifications": {
            "output_voltage": "24V DC",
            "output_current": "10A",
            "input_voltage": "220V AC",
            "efficiency": "95%"
        }
    },
]

FAULTS = [
    {
        "fault_code": "E001",
        "description": "设备无法启动，电源指示灯不亮",
        "severity": Severity.CRITICAL,
        "solution": "1. 检查电源连接是否正常\n2. 检查保险丝是否熔断\n3. 如保险丝完好，更换电源模块",
        "product_id": 1  # CTL-001
    },
    {
        "fault_code": "E002",
        "description": "通信中断，Modbus连接超时",
        "severity": Severity.HIGH,
        "solution": "1. 检查通信线路连接\n2. 确认通信参数配置正确\n3. 重启通信模块",
        "product_id": 1  # CTL-001
    },
    {
        "fault_code": "E003",
        "description": "温度显示异常，读数偏差超过±5°C",
        "severity": Severity.MEDIUM,
        "solution": "1. 检查传感器安装位置\n2. 校准传感器参数\n3. 如校准无效，更换传感器",
        "product_id": 3  # SEN-001
    },
    {
        "fault_code": "E004",
        "description": "执行器响应迟缓，动作延迟超过2秒",
        "severity": Severity.MEDIUM,
        "solution": "1. 检查执行器供电电压\n2. 清洁执行器机械部件\n3. 调整控制参数",
        "product_id": 5  # ACT-001
    },
    {
        "fault_code": "E005",
        "description": "电源模块输出电压不稳定，波动超过±2V",
        "severity": Severity.HIGH,
        "solution": "1. 检查输入电源质量\n2. 检查负载是否超出额定范围\n3. 更换电源模块",
        "product_id": 7  # MOD-002
    },
]

COMPATIBILITIES = [
    {"product_a_id": 1, "product_b_id": 6, "compatibility_type": "compatible", "confidence": 0.95, "notes": "CTL-001与MOD-001完全兼容"},
    {"product_a_id": 1, "product_b_id": 7, "compatibility_type": "compatible", "confidence": 0.98, "notes": "CTL-001推荐使用MOD-002供电"},
    {"product_a_id": 3, "product_b_id": 1, "compatibility_type": "compatible", "confidence": 0.90, "notes": "SEN-001可直接连接CTL-001"},
    {"product_a_id": 4, "product_b_id": 1, "compatibility_type": "compatible", "confidence": 0.85, "notes": "SEN-002需通过MOD-001转换后连接"},
    {"product_a_id": 2, "product_b_id": 6, "compatibility_type": "upgrade", "confidence": 0.80, "notes": "CTL-002可升级为CTL-001"},
]

CHUNKS = [
    {"product_id": 1, "chunk_type": "spec", "section_title": "产品概述", "content": "智能控制器X1是一款高性能工业控制器，支持Modbus RTU、CAN和Ethernet三种通信协议。额定电压220V AC，工作温度范围-10°C至60°C，防护等级IP65，适合恶劣工业环境使用。"},
    {"product_id": 1, "chunk_type": "spec", "section_title": "技术参数", "content": "CTL-001技术参数：输入电压220V AC（100-240V宽范围），额定功率500W，重量1.2kg，外形尺寸200×100×50mm。支持16路数字量输入、8路模拟量输入（4-20mA/0-10V），8路数字量输出。"},
    {"product_id": 1, "chunk_type": "troubleshoot", "section_title": "故障排查-无法启动", "content": "CTL-001无法启动排查步骤：1. 检查电源线连接是否牢固；2. 确认输入电压在100-240V范围内；3. 检查保险丝（规格5A/250V）；4. 观察电源指示灯状态；5. 如以上均正常，联系技术支持。"},
    {"product_id": 3, "chunk_type": "spec", "section_title": "温度传感器T200规格", "content": "温度传感器T200：测量范围-20°C至200°C，精度±0.5°C，响应时间100ms，输出信号4-20mA，防护等级IP67。安装方式：M12螺纹安装。"},
    {"product_id": 3, "chunk_type": "troubleshoot", "section_title": "温度异常排查", "content": "温度传感器T200显示异常排查：1. 检查传感器安装位置是否正确；2. 校准零点和量程；3. 检查信号线连接；4. 如读数持续偏差>±5°C，更换传感器。"},
]


def import_data():
    """导入所有数据"""
    logger.info("=== 开始导入数据 ===")

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # 1. 导入产品
        logger.info("导入产品...")
        for product_data in PRODUCTS:
            existing = db.query(Product).filter(
                Product.product_code == product_data["product_code"]
            ).first()
            if not existing:
                product = Product(**product_data)
                db.add(product)
        db.commit()

        # 2. 导入故障（需要先获取产品ID）
        logger.info("导入故障...")
        products = db.query(Product).all()
        product_map = {p.product_code: p.id for p in products}

        for fault_data in FAULTS:
            # Resolve product_id from product_code
            existing = db.query(Fault).filter(
                Fault.fault_code == fault_data["fault_code"]
            ).first()
            if not existing:
                fault = Fault(
                    fault_code=fault_data["fault_code"],
                    description=fault_data["description"],
                    severity=fault_data["severity"],
                    solution=fault_data["solution"],
                    product_id=fault_data["product_id"]
                )
                db.add(fault)
        db.commit()

        # 3. 导入兼容性
        logger.info("导入兼容性数据...")
        for compat_data in COMPATIBILITIES:
            compat = CompatibilityMatrix(**compat_data)
            db.add(compat)
        db.commit()

        # 4. 导入手册分块
        logger.info("导入手册分块...")
        for chunk_data in CHUNKS:
            chunk = ManualChunk(**chunk_data)
            db.add(chunk)
        db.commit()

        # 5. 向量化分块并导入Milvus
        logger.info("向量化并导入Milvus...")
        chunks = db.query(ManualChunk).all()

        if chunks:
            try:
                encoder = get_encoder()
                milvus = get_milvus_client()

                texts = [c.content for c in chunks]
                vectors = encoder.encode(texts)

                metadata = []
                for c in chunks:
                    metadata.append({
                        "product_id": c.product_id,
                        "chunk_id": c.id,
                        "chunk_type": c.chunk_type,
                        "content": c.content[:200]  # Milvus field size limit
                    })

                milvus.insert_vectors(vectors, metadata)
                logger.info(f"已向量化并导入 {len(chunks)} 个分块到Milvus")
            except Exception as e:
                logger.warning(f"Milvus导入失败（可稍后手动导入）: {e}")

        # 统计
        product_count = db.query(Product).count()
        fault_count = db.query(Fault).count()
        compat_count = db.query(CompatibilityMatrix).count()
        chunk_count = db.query(ManualChunk).count()

        logger.info("=== 数据导入完成 ===")
        logger.info(f"产品: {product_count}个")
        logger.info(f"故障: {fault_count}个")
        logger.info(f"兼容性: {compat_count}条")
        logger.info(f"手册分块: {chunk_count}个")

    except Exception as e:
        logger.error(f"数据导入失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_data()
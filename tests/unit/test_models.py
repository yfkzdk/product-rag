import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.postgres.models import Base, Product, Fault
from src.exceptions import ValidationError


@pytest.fixture(scope="function")
def db_session():
    """数据库会话fixture"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def sample_product():
    """示例产品数据"""
    return {
        "product_code": "PROD-001",
        "name": "智能控制器",
        "category": "控制器",
        "specifications": {
            "power": "220V",
            "weight": "1.2kg"
        }
    }


@pytest.fixture
def sample_fault():
    """示例故障数据"""
    return {
        "fault_code": "E001",
        "symptom": "温度异常",
        "root_cause": "传感器故障",
        "solution": "更换传感器",
        "severity": "HIGH"
    }


# ===== 产品测试 =====

def test_create_product(db_session, sample_product):
    """测试创建产品"""
    product = Product(**sample_product)
    db_session.add(product)
    db_session.commit()

    assert product.id is not None
    assert product.product_code == "PROD-001"
    assert product.name == "智能控制器"


def test_product_specifications(db_session, sample_product):
    """测试产品规格JSONB"""
    product = Product(**sample_product)
    db_session.add(product)
    db_session.commit()

    assert product.specifications["power"] == "220V"
    assert product.specifications["weight"] == "1.2kg"


def test_product_unique_code(db_session, sample_product):
    """测试产品型号唯一性"""
    product1 = Product(**sample_product)
    db_session.add(product1)
    db_session.commit()

    # 尝试创建相同型号的产品
    product2 = Product(**sample_product)
    db_session.add(product2)

    with pytest.raises(Exception):  # SQLite会抛出IntegrityError
        db_session.commit()


def test_product_parent_relationship(db_session, sample_product):
    """测试产品父子关系"""
    parent = Product(**sample_product)
    db_session.add(parent)
    db_session.commit()

    child = Product(
        product_code="PROD-002",
        name="子产品",
        parent_product_id=parent.id
    )
    db_session.add(child)
    db_session.commit()

    assert child.parent_product_id == parent.id
    assert parent.children[0].product_code == "PROD-002"


# ===== 故障测试 =====

def test_create_fault(db_session, sample_fault, sample_product):
    """测试创建故障"""
    # 先创建产品
    product = Product(**sample_product)
    db_session.add(product)
    db_session.commit()

    # 创建故障
    fault = Fault(**sample_fault, product_id=product.id)
    db_session.add(fault)
    db_session.commit()

    assert fault.id is not None
    assert fault.fault_code == "E001"
    assert fault.product_id == product.id


def test_fault_product_relationship(db_session, sample_fault, sample_product):
    """测试故障产品关系"""
    product = Product(**sample_product)
    db_session.add(product)
    db_session.commit()

    fault = Fault(**sample_fault, product_id=product.id)
    db_session.add(fault)
    db_session.commit()

    assert fault.product.product_code == "PROD-001"
    assert product.faults[0].fault_code == "E001"


def test_fault_parent_relationship(db_session, sample_fault, sample_product):
    """测试故障父子关系"""
    product = Product(**sample_product)
    db_session.add(product)
    db_session.commit()

    parent_fault = Fault(**sample_fault, product_id=product.id)
    db_session.add(parent_fault)
    db_session.commit()

    child_fault = Fault(
        fault_code="E002",
        symptom="子故障",
        parent_fault_id=parent_fault.id,
        product_id=product.id
    )
    db_session.add(child_fault)
    db_session.commit()

    assert child_fault.parent_fault_id == parent_fault.id
    assert parent_fault.children[0].fault_code == "E002"


# ===== 异常测试 =====

def test_validation_error():
    """测试校验异常"""
    error = ValidationError("缺少产品型号", "product_code")

    assert error.code == "VALIDATION_ERROR"
    assert error.message == "缺少产品型号"
    assert error.details["field"] == "product_code"
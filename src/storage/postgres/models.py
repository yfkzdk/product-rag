from sqlalchemy import Column, Integer, String, Text, Float, JSON, Enum, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class Severity(enum.Enum):
    """故障严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Product(Base):
    """产品表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    specifications = Column(JSON, default=dict)
    parent_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    faults = relationship("Fault", back_populates="product")
    manual_chunks = relationship("ManualChunk", back_populates="product")
    parent = relationship("Product", back_populates="children", remote_side=[id])
    children = relationship("Product", back_populates="parent")

    def __repr__(self):
        return f"<Product(id={self.id}, code={self.product_code}, name={self.name})>"


class Fault(Base):
    """故障表"""
    __tablename__ = "faults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fault_code = Column(String(50), nullable=False, index=True)
    symptom = Column(Text)
    description = Column(Text)
    root_cause = Column(Text)
    severity = Column(Enum(Severity), default=Severity.MEDIUM)
    solution = Column(Text)
    product_id = Column(Integer, ForeignKey("products.id"))
    parent_fault_id = Column(Integer, ForeignKey("faults.id"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    product = relationship("Product", back_populates="faults")
    parent_fault = relationship("Fault", back_populates="children", remote_side=[id])
    children = relationship("Fault", back_populates="parent_fault")

    def __repr__(self):
        return f"<Fault(id={self.id}, code={self.fault_code})>"


class CompatibilityMatrix(Base):
    """兼容性矩阵"""
    __tablename__ = "compatibility_matrix"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_a_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_b_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    compatibility_type = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<CompatibilityMatrix(id={self.id}, type={self.compatibility_type})>"


class ManualChunk(Base):
    """手册分块表"""
    __tablename__ = "manual_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    chunk_type = Column(String(50), nullable=False)
    section_title = Column(String(200))
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    product = relationship("Product", back_populates="manual_chunks")

    def __repr__(self):
        return f"<ManualChunk(id={self.id}, type={self.chunk_type}, product_id={self.product_id})>"
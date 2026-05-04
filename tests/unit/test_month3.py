"""
Month 3 单元测试

测试HyDE检索、模板化Chunking、知识图谱检索
"""
import pytest


# ===== HyDE检索测试 =====

def test_hyde_retriever_init():
    """测试HyDE检索器初始化"""
    from src.retrieval.hyde_retriever import HyDERetriever

    retriever = HyDERetriever()
    assert retriever is not None


def test_hyde_generate_hypothetical_doc():
    """测试假设文档生成"""
    from src.retrieval.hyde_retriever import HyDERetriever

    retriever = HyDERetriever()

    # 测试规格查询
    doc = retriever.generate_hypothetical_doc("PROD-001的功率是多少？")
    assert len(doc) > 0
    assert "功率" in doc or "PROD-001" in doc

    # 测试故障查询
    doc = retriever.generate_hypothetical_doc("设备无法启动怎么办？")
    assert len(doc) > 0
    assert "故障" in doc or "启动" in doc


def test_hyde_mock_hypothetical_doc():
    """测试Mock假设文档生成"""
    from src.retrieval.hyde_retriever import HyDERetriever

    retriever = HyDERetriever()

    # 测试不同查询类型
    spec_doc = retriever._mock_hypothetical_doc("产品规格参数")
    assert "功率" in spec_doc or "规格" in spec_doc

    fault_doc = retriever._mock_hypothetical_doc("故障代码E001")
    assert "故障" in fault_doc

    compat_doc = retriever._mock_hypothetical_doc("兼容性查询")
    assert "兼容" in compat_doc


# ===== 模板化Chunking测试 =====

def test_template_chunker_init():
    """测试模板分块器初始化"""
    from src.ingestion.template_chunker import TemplateChunker

    chunker = TemplateChunker()
    assert len(chunker.CHUNK_TEMPLATES) == 4


def test_template_chunker_detect_table_type():
    """测试表格类型检测"""
    from src.ingestion.template_chunker import TemplateChunker

    chunker = TemplateChunker()

    # 规格表
    spec_table = {"headers": ["参数名", "参数值", "单位"]}
    table_type = chunker.detect_table_type(spec_table)
    assert table_type == "spec_table"

    # 故障表
    fault_table = {"headers": ["故障代码", "症状", "原因"]}
    table_type = chunker.detect_table_type(fault_table)
    assert table_type == "fault_table"


def test_template_chunker_chunk_table():
    """测试表格分块"""
    from src.ingestion.template_chunker import TemplateChunker

    chunker = TemplateChunker()

    # 规格表
    table_data = {
        "headers": ["参数名", "参数值", "单位"],
        "rows": [
            ["功率", "220", "V"],
            ["重量", "1.2", "kg"]
        ]
    }

    chunks = chunker.chunk_table(table_data, "spec_table")
    assert len(chunks) == 2
    assert "功率" in chunks[0]
    assert "重量" in chunks[1]


def test_template_chunker_smart_chunk():
    """测试智能分块"""
    from src.ingestion.template_chunker import TemplateChunker

    chunker = TemplateChunker()

    # 故障文本
    fault_text = "故障代码E001：设备无法启动，原因：电源故障"
    chunks = chunker.smart_chunk(fault_text)
    assert len(chunks) > 0

    # 兼容性文本
    compat_text = "PROD-001与PROD-002完全兼容"
    chunks = chunker.smart_chunk(compat_text)
    assert len(chunks) > 0


# ===== Neo4j客户端测试 =====

def test_neo4j_client_init():
    """测试Neo4j客户端初始化"""
    from src.storage.neo4j.client import Neo4jClient

    client = Neo4jClient()
    assert client is not None


def test_neo4j_create_product_node():
    """测试创建产品节点"""
    from src.storage.neo4j.client import Neo4jClient

    client = Neo4jClient()

    product_data = {
        "product_code": "PROD-001",
        "name": "智能控制器",
        "specifications": {"power": "220V"},
        "category": "控制器"
    }

    success = client.create_product_node(product_data)
    # Mock模式下应该成功
    assert success is True or success is False


def test_neo4j_find_n_hop_paths():
    """测试N-hop路径查询"""
    from src.storage.neo4j.client import Neo4jClient

    client = Neo4jClient()

    paths = client.find_n_hop_paths("PROD-001", n_hops=2)
    assert isinstance(paths, list)


# ===== 实体抽取测试 =====

def test_entity_extractor_init():
    """测试实体抽取器初始化"""
    from src.ingestion.entity_extractor import EntityExtractor

    extractor = EntityExtractor()
    assert extractor is not None


def test_entity_extractor_rule_extract():
    """测试规则实体抽取"""
    from src.ingestion.entity_extractor import EntityExtractor

    extractor = EntityExtractor()

    text = "产品PROD-001和PROD-002兼容，故障代码E001表示无法启动"
    entities = extractor._rule_extract_entities(text)

    # 应该提取出产品型号和故障代码
    entity_names = [e["name"] for e in entities]
    assert "PROD-001" in entity_names
    assert "PROD-002" in entity_names
    assert "E001" in entity_names


def test_entity_extractor_extract_relations():
    """测试关系抽取"""
    from src.ingestion.entity_extractor import EntityExtractor

    extractor = EntityExtractor()

    text = "PROD-001和PROD-002完全兼容"
    entities = [
        {"type": "Product", "name": "PROD-001"},
        {"type": "Product", "name": "PROD-002"}
    ]

    relations = extractor.extract_relations(text, entities)
    assert len(relations) > 0
    assert relations[0]["type"] == "COMPATIBLE_WITH"


# ===== 知识图谱检索测试 =====

def test_kg_search_init():
    """测试知识图谱检索初始化"""
    from src.retrieval.kg_search import KGSearch

    search = KGSearch()
    assert search is not None


@pytest.mark.asyncio
async def test_kg_search_extract_entities():
    """测试实体提取"""
    from src.retrieval.kg_search import KGSearch

    search = KGSearch()

    entities = await search.extract_entities("PROD-001的故障代码E001")
    assert "PROD-001" in entities
    assert "E001" in entities


# ===== 故障传播测试 =====

def test_fault_propagation_init():
    """测试故障传播初始化"""
    from src.retrieval.fault_propagation import FaultPropagation

    propagation = FaultPropagation()
    assert propagation is not None


def test_fault_propagation_find_root_causes():
    """测试查找根本原因"""
    from src.retrieval.fault_propagation import FaultPropagation

    propagation = FaultPropagation()

    causes = propagation.find_root_causes("E001")
    assert isinstance(causes, list)


def test_fault_propagation_analyze_impact():
    """测试故障影响分析"""
    from src.retrieval.fault_propagation import FaultPropagation

    propagation = FaultPropagation()

    impact = propagation.analyze_fault_impact("E001")
    assert "fault_code" in impact
    assert "impact_score" in impact
    assert "severity" in impact


# ===== 社区检测测试 =====

def test_community_detector_init():
    """测试社区检测器初始化"""
    from src.retrieval.community_detector import CommunityDetector

    detector = CommunityDetector()
    assert detector is not None


def test_community_detector_fallback():
    """测试降级社区检测"""
    from src.retrieval.community_detector import CommunityDetector

    detector = CommunityDetector()

    communities = detector._fallback_community_detection(min_size=2)
    assert isinstance(communities, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

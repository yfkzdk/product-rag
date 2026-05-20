from typing import List, Dict, Optional
from src.config import get_settings
import re
import logging

logger = logging.getLogger(__name__)

# Demo-mode mock KG data: product relationships, fault→solution chains, compatibility
_DEMO_KG = {
    "products": {
        "PROD-001": {
            "name": "PROD-001", "category": "工业控制器",
            "related": ["PROD-002", "PROD-003"],
            "faults": ["E001", "E002", "E003"],
            "compatible": ["PROD-002"],
        },
        "PROD-002": {
            "name": "PROD-002", "category": "电源模块",
            "related": ["PROD-001", "PROD-003"],
            "faults": ["E004"],
            "compatible": ["PROD-001", "PROD-003"],
        },
        "PROD-003": {
            "name": "PROD-003", "category": "通信网关",
            "related": ["PROD-001", "PROD-002"],
            "faults": ["E005", "E006"],
            "compatible": ["PROD-002"],
        },
    },
    "faults": {
        "E001": {
            "code": "E001", "desc": "设备无法启动，电源指示灯不亮",
            "solutions": [
                {"desc": "测量输入电压应为220V±10%，检查保险丝F1/F2是否导通", "confidence": 0.92},
                {"desc": "若保险丝正常，更换电源模块P200", "confidence": 0.85},
            ]
        },
        "E002": {
            "code": "E002", "desc": "温度读数偏差超过±5°C，传感器信号异常",
            "solutions": [
                {"desc": "拆下传感器接线，用酒精清洗端子后重新紧固（扭矩0.5N·m）", "confidence": 0.90},
                {"desc": "进入菜单执行自动校准程序", "confidence": 0.78},
            ]
        },
        "E003": {
            "code": "E003", "desc": "输出电压不稳定，波动超过±5%额定值",
            "solutions": [
                {"desc": "断开负载测量空载输出电压，逐步增加负载至额定值观察变化", "confidence": 0.88},
                {"desc": "更换输出滤波电容C5/C6（规格：1000μF/50V）", "confidence": 0.82},
            ]
        },
        "E004": {
            "code": "E004", "desc": "电源模块过温保护触发，散热风扇不转",
            "solutions": [
                {"desc": "检查散热风扇供电及转速反馈信号线", "confidence": 0.91},
                {"desc": "清理散热片积尘，确保通风道畅通", "confidence": 0.80},
            ]
        },
        "E005": {
            "code": "E005", "desc": "通信超时，网关无响应，数据上传中断",
            "solutions": [
                {"desc": "ping测试确认网络通断，检查网关IP/掩码/网关配置", "confidence": 0.93},
                {"desc": "更换STP屏蔽网线并确保单端接地，消除电磁干扰", "confidence": 0.79},
            ]
        },
        "E006": {
            "code": "E006", "desc": "通信数据校验失败率超过阈值，误码率高",
            "solutions": [
                {"desc": "检查RS485终端电阻设置是否正确（120Ω）", "confidence": 0.87},
                {"desc": "降低通信波特率至9600bps测试稳定性", "confidence": 0.76},
            ]
        },
    },
}


class KGRetriever:
    """知识图谱检索器 — 嵌入语义搜索 + 关系遍历"""

    def __init__(self):
        pass

    def retrieve(self, query: str, product_name: Optional[str] = None, top_k: Optional[int] = None) -> List[Dict]:
        """知识图谱检索：嵌入匹配实体 → 关系遍历"""
        settings = get_settings()
        effective_top_k = top_k or settings.RETRIEVAL_TOP_K

        # Demo模式：使用内置mock数据提供结构化KG结果
        if settings.DEMO_MODE or not settings.NEO4J_URI:
            return self._demo_retrieve(query, effective_top_k)

        from src.storage.neo4j.client import get_kg_client
        from src.embeddings.bge_embedder import get_encoder

        kg = get_kg_client()
        if not kg.is_available:
            return self._demo_retrieve(query, effective_top_k)

        try:
            encoder = get_encoder()
            query_embedding = encoder.encode_single(query)
            results = []

            # 1. 语义搜索产品
            products = kg.search_products_by_embedding(query_embedding, limit=3)
            for p in products:
                p_name = p.get("name", "")
                results.append({
                    "content": f"产品: {p_name} | 类别: {p.get('category', '')}",
                    "source": "knowledge_graph",
                    "retrieval_type": "semantic_product",
                    "score": p.get("_similarity", 0.0),
                })

            # 2. 语义搜索故障 → 遍历解决方案
            faults = kg.search_faults_by_embedding(query_embedding, limit=5)
            for f in faults:
                fault_code = f.get("fault_code", "")
                fault_desc = f.get("description", "")
                solutions = kg.get_solutions_for_fault(fault_code)
                for sol in solutions:
                    results.append({
                        "content": f"故障[{fault_code}]: {fault_desc} → 方案: {sol.get('description', '')}",
                        "source": "knowledge_graph",
                        "retrieval_type": "fault_solution",
                        "score": sol.get("confidence", f.get("_similarity", 0.0)),
                        "fault_code": fault_code,
                    })

            # 3. 兼容性关系
            for p in products[:2]:
                p_name = p.get("name", "")
                compat = kg.get_product_compatibility(p_name)
                for c in compat:
                    results.append({
                        "content": f"{p_name} ↔ {c.get('product', '')} | 兼容性: {c.get('confidence', 0.0)}",
                        "source": "knowledge_graph",
                        "retrieval_type": "compatibility",
                        "score": c.get("confidence", 0.5),
                    })

            # 4. N-hop 路径探索
            if products:
                p_code = products[0].get("product_code", "")
                if p_code:
                    paths = kg.find_n_hop_paths(p_code, n_hops=2, limit=5)
                    for path in paths:
                        results.append({
                            "content": f"N-hop路径: {path.get('start', '')} → ... → {path.get('target', '')} ({path.get('hops', 0)}跳)",
                            "source": "knowledge_graph",
                            "retrieval_type": "n_hop_path",
                            "score": 0.6,
                        })

            logger.info(f"KG retrieval: {len(results)} results (embedding-based)")
            return results[:effective_top_k]

        except Exception as e:
            logger.error(f"KG retrieval failed: {e}")
            return self._demo_retrieve(query, effective_top_k)

    def _demo_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """Demo模式KG检索：从内置mock数据提供结构化关系结果"""
        results = []

        # 提取产品代码和故障代码
        p_match = re.search(r'[A-Z]{2,5}-\d{3,5}', query.upper())
        f_match = re.search(r'E\d{3,5}', query.upper())

        matched_products = []
        if p_match:
            code = p_match.group(0)
            if code in _DEMO_KG["products"]:
                matched_products.append(code)
        # 关键词回退匹配
        query_lower = query.lower()
        for code, info in _DEMO_KG["products"].items():
            if code not in matched_products:
                if any(kw in query_lower for kw in [code.lower(), info["category"].lower()]):
                    matched_products.append(code)

        if not matched_products:
            matched_products = ["PROD-001"]  # 默认产品

        # 1. 产品关系
        for code in matched_products[:2]:
            info = _DEMO_KG["products"][code]
            for related in info["related"]:
                rel_info = _DEMO_KG["products"].get(related, {})
                results.append({
                    "content": f"相关产品: {code}({info['category']}) ↔ {related}({rel_info.get('category', '')})",
                    "source": "knowledge_graph",
                    "retrieval_type": "related_products",
                    "score": 0.85,
                })

        # 2. 故障 → 解决方案
        fault_codes_to_search = []
        if f_match:
            fault_codes_to_search.append(f_match.group(0))
        else:
            for code in matched_products:
                fault_codes_to_search.extend(_DEMO_KG["products"][code]["faults"])

        for fc in fault_codes_to_search[:4]:
            fault = _DEMO_KG["faults"].get(fc)
            if fault:
                for sol in fault["solutions"]:
                    results.append({
                        "content": f"故障[{fc}]: {fault['desc']} → 方案: {sol['desc']}",
                        "source": "knowledge_graph",
                        "retrieval_type": "fault_solution",
                        "score": sol["confidence"],
                        "fault_code": fc,
                    })

        # 3. 兼容性
        for code in matched_products[:2]:
            info = _DEMO_KG["products"][code]
            for comp in info["compatible"]:
                results.append({
                    "content": f"兼容: {code} ↔ {comp} | 接口兼容，可互换使用",
                    "source": "knowledge_graph",
                    "retrieval_type": "compatibility",
                    "score": 0.80,
                })

        logger.info(f"KG demo retrieval: {len(results)} results from mock data")
        return results[:top_k]


_kg_retriever: Optional[KGRetriever] = None


def get_kg_retriever() -> KGRetriever:
    global _kg_retriever
    if _kg_retriever is None:
        _kg_retriever = KGRetriever()
    return _kg_retriever

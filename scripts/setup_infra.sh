#!/usr/bin/env bash
# ============================================================
# RAG 基础设施一键启动脚本
# ============================================================
# 用法:
#   bash scripts/setup_infra.sh          # 启动所有服务
#   bash scripts/setup_infra.sh down     # 停止所有服务
#   bash scripts/setup_infra.sh clean    # 停止并清除数据
#   bash scripts/setup_infra.sh status   # 查看服务状态
# ============================================================
set -e

COMPOSE_FILE="docker-compose.yml"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[ERROR] Docker not found. Please install Docker Desktop: https://www.docker.com/products/docker-desktop/${NC}"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}[ERROR] docker compose not available. Please update Docker to latest version.${NC}"
        exit 1
    fi
}

wait_for_healthy() {
    local service=$1
    local max_wait=${2:-60}
    local elapsed=0
    echo -ne "${YELLOW}Waiting for $service to be healthy...${NC} "
    while [ $elapsed -lt $max_wait ]; do
        status=$(docker compose ps -a --format json 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line)
    if d.get('Service') == '$service':
        print(d.get('Health', ''))
        break
" 2>/dev/null || echo "")
        if [ "$status" = "healthy" ]; then
            echo -e "${GREEN}OK${NC}"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo -e "${RED} TIMEOUT${NC}"
    return 1
}

case "${1:-up}" in
    down)
        check_docker
        echo -e "${YELLOW}Stopping all services...${NC}"
        docker compose down
        echo -e "${GREEN}All services stopped.${NC}"
        ;;
    clean)
        check_docker
        echo -e "${RED}Stopping and removing all data...${NC}"
        docker compose down -v
        echo -e "${GREEN}All services stopped and data removed.${NC}"
        ;;
    status)
        check_docker
        docker compose ps
        ;;
    up|*)
        check_docker
        echo -e "${GREEN}Starting RAG infrastructure...${NC}"
        echo ""
        docker compose up -d
        echo ""

        # Wait for services
        wait_for_healthy "postgres" 30
        wait_for_healthy "redis" 15
        wait_for_healthy "milvus" 60
        wait_for_healthy "neo4j" 45
        echo ""

        echo -e "${GREEN}============================================================${NC}"
        echo -e "${GREEN}  Infrastructure Ready!${NC}"
        echo -e "${GREEN}============================================================${NC}"
        echo ""
        echo -e "  PostgreSQL:  ${GREEN}postgresql://product_kg:product_kg@localhost:5432/product_kg${NC}"
        echo -e "  Milvus:      ${GREEN}http://localhost:19530${NC}  (monitor: http://localhost:9091)"
        echo -e "  Neo4j:       ${GREEN}bolt://localhost:7687${NC}  (browser: http://localhost:7474)"
        echo -e "  Redis:       ${GREEN}redis://localhost:6379${NC}"
        echo ""
        echo -e "  Neo4j credentials: neo4j / product_kg_password"
        echo ""
        echo -e "  Start RAG server: ${YELLOW}cd O:/AII/RAG && .venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000${NC}"
        echo ""
        ;;
esac

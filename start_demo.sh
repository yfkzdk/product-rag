#!/bin/bash
cd "O:/AII/RAG"
echo "=== RAG Demo Mode Startup ==="
echo "Starting FastAPI server on port 8000..."
"O:/AII/.venv/Scripts/python.exe" -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

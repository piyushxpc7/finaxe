.PHONY: help costs test cache budget

help:
	@echo "Available commands:"
	@echo "  make costs        - Show LLM cost analytics"
	@echo "  make test         - Run integration tests"
	@echo "  make cache        - Test Redis caching layer"
	@echo "  make budget       - Test context budget management"

costs:
	@echo "=== LLM Cost Analytics ==="
	@curl -s http://localhost:8000/admin/costs | python3 -m json.tool || echo "Server not running. Start with: uvicorn app.main:app --reload"

test:
	pytest app/tests/ -v

cache:
	@echo "=== Testing Redis Cache Layer ==="
	python scripts/test_cache.py

budget:
	@echo "=== Testing Context Budget Management ==="
	python scripts/test_budget.py

.PHONY: test run clean

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

# Launch Streamlit Dashboard
run:
	streamlit run web/app_v3.py

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache

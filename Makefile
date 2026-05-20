.PHONY: install test lint run-api run-dashboard

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/

lint:
	black .
	flake8 .

run-api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	streamlit run dashboard/app.py

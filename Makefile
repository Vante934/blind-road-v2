.PHONY: install run dev docker-build docker-run clean

install:
	pip install -r requirements.txt

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker-compose build

docker-run:
	docker-compose up

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
IMAGE=fraud-detection-api
TAG?=v0.0.1

run:
	PORT=$${PORT:-9000} /usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port $$PORT
.PHONY: run

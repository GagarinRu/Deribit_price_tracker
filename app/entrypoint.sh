#!/usr/bin/env bash
exec uvicorn src.main:app --reload --host $UVICORN_HOST --port $UVICORN_PORT

#!/bin/bash

echo "Starting Statified Backend..."
cd server
uv run uvicorn app:app --reload &

echo "Starting Statified Frontend..."
cd ../client
npm run dev

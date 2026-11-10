# Starts the FastAPI backend. Run this from the backend folder with: .\run.ps1
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

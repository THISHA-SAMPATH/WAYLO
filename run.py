"""
One-command launcher: python run.py
Starts the unified WAYLO web application and FastAPI backend on one port (http://localhost:8000).
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  WAYLO — Physical AI Shared-Autonomy Wheelchair Copilot")
    print("  Unified Web App and API Server: http://localhost:8000")
    print("  Interactive OpenAPI Docs     : http://localhost:8000/docs")
    print("=" * 70)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

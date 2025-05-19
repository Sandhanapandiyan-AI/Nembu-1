from pathlib import Path
import sys
import uvicorn

# Add the parent directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

if __name__ == "__main__":
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir / "app")]
    )

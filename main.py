"""
Main entry point for the Digital Courtroom application
"""

import uvicorn
from src.api.main import app


def main():
    """启动FastAPI服务器"""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下启用热重载
        log_level="info",
    )


if __name__ == "__main__":
    main()

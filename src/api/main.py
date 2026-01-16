"""
FastAPI Main Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routes import sessions, websocket


# 创建FastAPI应用
app = FastAPI(
    title="数字法庭API",
    description="基于LangGraph的法庭辩论模拟系统API",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加路由
app.include_router(sessions.router)
app.include_router(websocket.router)

# 静态文件服务 - 用于演示页面
examples_path = Path(__file__).parent.parent.parent / "examples"
if examples_path.exists():
    # 使用html=True参数，这样访问/examples/时会自动返回index.html
    app.mount("/examples", StaticFiles(directory=examples_path, html=True), name="examples")
else:
    print(f"警告: examples目录不存在于 {examples_path}")


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "数字法庭API",
        "demo": "/examples/index.html",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

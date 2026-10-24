"""
FastAPI Application Entrypoint
Configures middleware, exception handlers, and mounts domain routers with versioned routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.exceptions import (
    F1SimulatorError,
    f1_simulator_exception_handler,
    global_exception_handler,
)
from .api.routes import (
    system_router,
    circuits_router,
    drivers_router,
    simulation_router,
    optimization_router,
    telemetry_router,
)


def create_app() -> FastAPI:
    """Application factory for the F1 Monte Carlo Strategy Simulator API."""
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        description=(
            "High-performance vectorized Monte Carlo simulation and MCTS strategy optimizer "
            "for Formula 1 Grand Prix racing."
        ),
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom exception handlers
    app.add_exception_handler(F1SimulatorError, f1_simulator_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # 1. Mount root routes (100% backward compatible with existing frontend / tests)
    app.include_router(system_router)
    app.include_router(circuits_router)
    app.include_router(drivers_router)
    app.include_router(simulation_router)
    app.include_router(optimization_router)
    app.include_router(telemetry_router)

    # 2. Mount versioned API routes (/api/v1/...) for forward scalability
    app.include_router(system_router, prefix=settings.API_V1_PREFIX)
    app.include_router(circuits_router, prefix=settings.API_V1_PREFIX)
    app.include_router(drivers_router, prefix=settings.API_V1_PREFIX)
    app.include_router(simulation_router, prefix=settings.API_V1_PREFIX)
    app.include_router(optimization_router, prefix=settings.API_V1_PREFIX)
    app.include_router(telemetry_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

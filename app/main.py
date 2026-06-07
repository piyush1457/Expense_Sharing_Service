from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, engine
from app.exceptions import AppException
from app.routers import users, groups, expenses, balances, settlements

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense Sharing Service",
    description="Production-quality Backend API for Decentro Interview",
    version="1.0.0"
)

# Register routers
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(balances.router)
app.include_router(settlements.router)

@app.get("/", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "expense-sharing-service"}

# --- EXCEPTION HANDLERS ---
# Handled exceptions in this file:
# 1. AppException (Custom application-level domain errors)
# 2. RequestValidationError (Pydantic validation errors)
# 3. StarletteHTTPException (FastAPI/Starlette default HTTP exceptions)
# 4. Exception (General generic python exception fallback)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles domain-specific AppExceptions from services."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "detail": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic request body validation errors."""
    error_details = []
    for err in exc.errors():
        location = " -> ".join(str(loc) for loc in err.get("loc", []))
        message = err.get("msg", "Validation failed")
        error_details.append(f"Field '{location}': {message}")
        
    detail_str = "; ".join(error_details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation Error",
            "detail": detail_str
        }
    )

@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats default HTTP exceptions (like 404 URL Not Found, 405 Method Not Allowed)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": "HTTP Exception",
            "detail": exc.detail
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled server exceptions (500)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal Server Error",
            "detail": str(exc)
        }
    )

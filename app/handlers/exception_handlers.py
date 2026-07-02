import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import StoreNotFoundError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(StoreNotFoundError)
    async def store_not_found_handler(
        request: Request,
        exc: StoreNotFoundError,
    ):
        logger.warning(
            "Store %s not found.",
            exc.store_id,
        )

        return JSONResponse(
            status_code=404,
            content={
                "detail": f"Store {exc.store_id} not found."
            },
        )
    
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled exception while processing request."
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error."
            },
        )
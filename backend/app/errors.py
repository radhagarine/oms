"""Domain exceptions raised by services and translated to HTTP responses by the API layer."""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class BusinessValidationError(AppError):
    status_code = 422


class InsufficientInventoryError(ConflictError):
    pass


class InvalidStatusTransitionError(ConflictError):
    pass

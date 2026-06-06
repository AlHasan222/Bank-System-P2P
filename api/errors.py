"""API error handling."""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from typing import Any, Dict, Optional


class APIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_response(self):
        response = {
            'success': False,
            'error': self.message
        }
        if self.details:
            response['details'] = self.details
        return jsonify(response), self.status_code


class ValidationError(APIError):
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, 400, details)


class NotFoundError(APIError):
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, 404, details)


class ConflictError(APIError):
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, 409, details)


class InternalError(APIError):
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, 500, details)


def handle_api_error(error: APIError):
    return error.to_response()


def handle_generic_error(error: Exception):
    if isinstance(error, HTTPException):
        return jsonify({
            'success': False,
            'error': error.name,
            'details': error.description
        }), error.code
    
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'details': str(error)
    }), 500
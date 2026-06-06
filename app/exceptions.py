class AppException(Exception):
    """
    Custom exception class for application-level errors.
    Enables services to raise business logic/validation errors that are
    automatically formatted into the requested standard JSON error response.
    """
    def __init__(self, status_code: int, message: str, detail: str):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)

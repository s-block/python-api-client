class CantSaveException(Exception):
    pass


class ResourceSetException(Exception):
    pass


class ApiException(Exception):
    pass


class AuthFailureException(ApiException):
    pass


class UnauthorizedException(ApiException):
    pass


class ForbiddenException(ApiException):
    pass


class NotFoundException(ApiException):
    pass


class MethodNotAllowed(ApiException):
    pass


RESPONSE_ERROR_EXCEPTIONS = {
    'Resource not found.': NotFoundException,
    'Authentication failed.': AuthFailureException,
    401: UnauthorizedException,
    403: ForbiddenException,
    404: NotFoundException,
    501: MethodNotAllowed,
}


def get_exception_class(status_code, error):
    try:
        ExceptionClass = RESPONSE_ERROR_EXCEPTIONS[status_code]
    except KeyError:
        try:
            ExceptionClass = RESPONSE_ERROR_EXCEPTIONS[error]
        except KeyError:
            ExceptionClass = ApiException

    return ExceptionClass

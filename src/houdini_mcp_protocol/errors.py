from enum import StrEnum


class ErrorCode(StrEnum):
    UNKNOWN_COMMAND = 'unknown command'
    BAD_ARGUMENTS = 'bad arguments'
    CONNECTION_ERROR = 'connection error'
    INVALID_REQUEST = 'invalid request'
    TIMEOUT_ERROR = 'request timed out'
    COMMAND_ERROR = 'command failed'

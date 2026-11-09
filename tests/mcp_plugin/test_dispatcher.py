from houdini_mcp_plugin import dispatcher
from houdini_mcp_protocol import ErrorCode, ResponseStatus


def test_dispatch_success() -> None:
    @dispatcher.register_command('test.success')
    def handler() -> dict[str, bool]:
        return {'ok': True}

    response = dispatcher.dispatch('test.success', {})

    assert response.status is ResponseStatus.SUCCESS
    assert response.data == {'ok': True}


def test_unknown_command() -> None:
    response = dispatcher.dispatch('test.missing', {})

    assert response.status is ResponseStatus.ERROR
    assert response.error is not None
    assert response.error['code'] == ErrorCode.UNKNOWN_COMMAND


def test_bad_arguments() -> None:
    @dispatcher.register_command('test.arguments')
    def handler(value: int) -> int:
        return value

    response = dispatcher.dispatch('test.arguments', {})

    assert response.status is ResponseStatus.ERROR
    assert response.error is not None
    assert response.error['code'] == ErrorCode.BAD_ARGUMENTS


def test_handler_exception() -> None:
    @dispatcher.register_command('test.failure')
    def handler() -> None:
        raise RuntimeError('boom')

    response = dispatcher.dispatch('test.failure', {})

    assert response.status is ResponseStatus.ERROR
    assert response.error is not None
    assert response.error['code'] == ErrorCode.COMMAND_ERROR
    assert 'boom' in response.error['message']

from houdini_mcp_protocol import Response, ResponseStatus


def test_response_success() -> None:
    response = Response.from_payload(
        {'status': 'success', 'data': {'ok': True}, 'request_id': 'abc'}
    )

    assert response.status is ResponseStatus.SUCCESS
    assert response.data == {'ok': True}
    assert response.error is None
    assert response.request_id == 'abc'


def test_response_error() -> None:
    response = Response.from_payload(
        {
            'status': 'error',
            'error': {'code': 'command failed', 'message': 'node not found'},
        }
    )

    assert response.status is ResponseStatus.ERROR
    assert response.data is None
    assert response.error == {'code': 'command failed', 'message': 'node not found'}

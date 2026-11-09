from houdini_mcp_protocol import Request, Response, ResponseStatus


def test_request_round_trip() -> None:
    request = Request(command='scene.get_scene_info', params={'node': '/obj/geo1'})

    payload = request.to_payload()

    assert payload == {
        'command': 'scene.get_scene_info',
        'params': {'node': '/obj/geo1'},
        'request_id': request.request_id,
    }
    assert Request.from_payload(payload) == request


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

from fastapi.testclient import TestClient
from studio.application import create_app

def test_internal_exception_does_not_expose_details():
    app = create_app()
    @app.get('/test-error')
    def error():
        raise RuntimeError('private-test-marker')
    response = TestClient(app, raise_server_exceptions=False).get('/test-error')
    assert response.status_code == 500
    assert 'private-test-marker' not in response.text

def test_navigation_and_login_copy():
    page = TestClient(create_app()).get('/').text
    assert 'href="#learning-profile"' in page and 'href="#publisher"' in page
    assert '보안 해시' in page
    assert '암호는 서버로 전송하거나 저장하지 않습니다' not in page

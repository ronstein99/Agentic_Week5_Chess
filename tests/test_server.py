"""The HTTP server: static files, game state and actions over a real local socket."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from server import make_server


@pytest.fixture
def base_url():
    server = make_server(port=0)  # Any free port.
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def get(url):
    with urllib.request.urlopen(url) as response:
        return response.status, response.headers, response.read()


def post(url, body):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.mark.parametrize("path,content_type", [("/", "text/html"),
                                               ("/app.js", "text/javascript"),
                                               ("/style.css", "text/css")])
def test_serves_static_files(base_url, path, content_type):
    status, headers, body = get(base_url + path)
    assert status == 200 and body
    assert headers["Content-Type"].startswith(content_type)
    assert headers["Cache-Control"] == "no-store"


def test_unknown_paths_are_not_found(base_url):
    with pytest.raises(urllib.error.HTTPError) as error:
        get(base_url + "/missing")
    assert error.value.code == 404
    assert post(base_url + "/api/other", {"action": "new"}) == (404, {"error": "Not found"})


def test_state_starts_with_a_new_game(base_url):
    status, _, body = get(base_url + "/api/state")
    state = json.loads(body)
    assert status == 200
    assert state["turn"] == "w" and state["moves"] == [] and state["opponent"] == "human"


def test_actions_change_the_shared_game(base_url):
    action = base_url + "/api/action"
    status, state = post(action, {"action": "move", "source": "e2", "target": "e4"})
    assert status == 200 and state["moves"] == ["e2-e4"] and state["turn"] == "b"
    _, _, body = get(base_url + "/api/state")
    assert json.loads(body)["moves"] == ["e2-e4"]
    status, state = post(action, {"action": "undo"})
    assert status == 200 and state["moves"] == []


@pytest.mark.parametrize("body,error", [
    ({"action": "move", "source": "e2", "target": "e5"}, None),
    ({"action": "fly"}, "Unknown action"),
    ([1, 2], "Expected an action object"),
    (b"not json", None),
])
def test_bad_actions_are_rejected(base_url, body, error):
    status, result = post(base_url + "/api/action", body)
    assert status == 400 and result["error"]
    if error:
        assert result["error"] == error


def test_empty_request_is_rejected(base_url):
    request = urllib.request.Request(base_url + "/api/action", data=b"", method="POST")
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request)
    assert error.value.code == 400
    assert json.loads(error.value.read()) == {"error": "Invalid request size"}

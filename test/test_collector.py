import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from path_coverage.collector import serve
from path_coverage.post import deliver

REPORT = {"sites": {"src/kata.py:3:11": [{"truthy": 1, "falsy": 1}]}}
SRC = str(Path(__file__).parent.parent / "src")


def _serving(directory):
    """A listening socket, its port, a stop event, and a thread serving it
    into directory."""
    server = socket.create_server(("127.0.0.1", 0))
    stop = threading.Event()
    thread = threading.Thread(target=serve, args=(server, directory, stop))
    thread.start()
    return server, server.getsockname()[1], stop, thread


def _stopped(server, stop, thread):
    """Stops serving, and closes server once serve has returned."""
    stop.set()
    thread.join(5)
    server.close()


def _exchange(port, request):
    """Sends request on a connection of its own, closes its writing side,
    and returns the whole reply."""
    with socket.create_connection(("127.0.0.1", port)) as client:
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        chunks = []
        while chunk := client.recv(4096):
            chunks.append(chunk)
    return b"".join(chunks).decode()


def test_6c2b8e01(tmp_path):
    """Example: two reports POSTed one after the other
    The collector saves each as a file of its own, numbered in the order
    they arrive, ready to be merged once every run is done."""
    server, port, stop, thread = _serving(tmp_path)
    assert deliver(json.dumps(REPORT), f"http://127.0.0.1:{port}/runs") == 200
    assert deliver(json.dumps({"sites": {}}), f"http://127.0.0.1:{port}/runs") == 200
    _stopped(server, stop, thread)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["run-0001.json", "run-0002.json"]
    assert json.loads((tmp_path / "run-0001.json").read_text()) == REPORT


def test_6c2b8e02(tmp_path):
    """Example: a collector saving into a dir that does not exist
    A report it cannot save is not acknowledged: the reply is 500.
    A 200 means the report is already saved."""
    server, port, stop, thread = _serving(tmp_path / "missing")
    assert deliver(json.dumps(REPORT), f"http://127.0.0.1:{port}/") == 500
    _stopped(server, stop, thread)


def test_6c2b8e03(tmp_path):
    """Example: a POST with Content-Length 120 whose sender stops after
    10 bytes, as when it dies mid-send
    The body is not a whole report, so nothing is saved.
    The reply is 400."""
    server, port, stop, thread = _serving(tmp_path)
    reply = _exchange(port, b'POST /runs HTTP/1.1\r\nContent-Length: 120\r\n\r\n{"sites":{')
    _stopped(server, stop, thread)
    assert reply == "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"
    assert list(tmp_path.iterdir()) == []


def test_6c2b8e04(tmp_path):
    """Example: GET /alive, GET /ready, then a POST, and GET /ready to a
    collector whose dir is missing
    /alive is answered 200 while the collector runs.
    /ready is answered 200 when its dir is writable, 503 when not.
    Neither saves anything or uses up a run number."""
    server, port, stop, thread = _serving(tmp_path)
    alive = _exchange(port, b"GET /alive HTTP/1.1\r\n\r\n")
    ready = _exchange(port, b"GET /ready HTTP/1.1\r\n\r\n")
    deliver(json.dumps(REPORT), f"http://127.0.0.1:{port}/")
    _stopped(server, stop, thread)
    ok = "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
    assert [alive, ready] == [ok, ok]
    assert [p.name for p in tmp_path.iterdir()] == ["run-0001.json"]
    server, port, stop, thread = _serving(tmp_path / "missing")
    unready = _exchange(port, b"GET /ready HTTP/1.1\r\n\r\n")
    _stopped(server, stop, thread)
    assert unready == "HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n"


def test_6c2b8e08(tmp_path):
    """Example: a connection closed without a request, as a TCP liveness
    check makes, then a POST
    The empty connection is closed unanswered and saves nothing, so the
    POST's report is still run 1."""
    server, port, stop, thread = _serving(tmp_path)
    assert _exchange(port, b"") == ""
    assert deliver(json.dumps(REPORT), f"http://127.0.0.1:{port}/runs") == 200
    _stopped(server, stop, thread)
    assert [p.name for p in tmp_path.iterdir()] == ["run-0001.json"]


def test_6c2b8e05():
    """Example: a collector that is not running
    deliver passes over it in silence, returning None, so the run's own
    output and exit status stay as they are."""
    probe = socket.create_server(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    assert deliver(json.dumps(REPORT), f"http://127.0.0.1:{port}/") is None


def test_6c2b8e06(tmp_path):
    """Example: python -m path_coverage.collector PORT DIR, sent half a
    report, then TERM, then the rest
    It creates DIR, finishes the report in hand, saves it, answers 200,
    and exits 0, printing nothing."""
    probe = socket.create_server(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    runs = tmp_path / "runs"
    process = subprocess.Popen(
        [sys.executable, "-m", "path_coverage.collector", str(port), str(runs)],
        env={**os.environ, "PYTHONPATH": SRC},
        stderr=subprocess.PIPE,
    )
    while True:
        try:
            assert _exchange(port, b"GET /ready HTTP/1.1\r\n\r\n").startswith("HTTP/1.1 200")
            break
        except OSError:
            time.sleep(0.1)
    body = json.dumps(REPORT).encode()
    half = len(body) // 2
    with socket.create_connection(("127.0.0.1", port)) as client:
        client.sendall(b"POST / HTTP/1.1\r\nContent-Length: %d\r\n\r\n" % len(body) + body[:half])
        time.sleep(0.2)
        process.send_signal(signal.SIGTERM)
        time.sleep(0.2)
        client.sendall(body[half:])
        client.shutdown(socket.SHUT_WR)
        reply = client.recv(4096).decode()
    _, stderr = process.communicate(timeout=5)
    assert reply == "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
    assert json.loads((runs / "run-0001.json").read_text()) == REPORT
    assert [process.returncode, stderr] == [0, b""]


def test_6c2b8e07():
    """Example: python -m path_coverage.collector -h
    It prints its usage, with an example, and exits 0."""
    done = subprocess.run(
        [sys.executable, "-m", "path_coverage.collector", "-h"],
        env={**os.environ, "PYTHONPATH": SRC},
        capture_output=True,
        text=True,
        check=False,
    )
    assert [done.returncode, done.stderr] == [0, ""]
    assert "Usage: path_coverage_collector PORT DIR" in done.stdout
    assert "path_coverage_collector 4570 " in done.stdout

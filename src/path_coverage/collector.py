"""Receives the JSON reports the post reporter sends, so the runs that sent
them, eg failing docker build steps, can be merged and rendered once they
are all done. Run as path_coverage_collector PORT DIR."""

import os
import signal
import socket
import sys
import threading
from pathlib import Path

HELP = """\
Usage: path_coverage_collector PORT DIR

Listens on PORT and saves each JSON report the post reporter
sends as DIR/run-0001.json, DIR/run-0002.json, and so on,
creating DIR if need be. A 200 means the report is saved.

GET /alive answers 200 while it runs.
GET /ready answers 200 when DIR is writable, 503 when not.

Runs until sent TERM. It then stops accepting connections,
finishes the report in hand, and exits 0.

Options:
  -h    Show this help

Example:
  path_coverage_collector 4570 /tmp/paths/runs
"""

# How often, in seconds, serve looks up from accepting to see if it is to
# stop.
POLL = 0.2

# The check each GET path makes of the collector's dir: /alive passes
# whenever the collector answers; /ready only when dir is a writable
# directory, so a report sent now could be saved.
PROBES = {
    "/alive": lambda directory: True,
    "/ready": lambda directory: directory.is_dir() and os.access(directory, os.W_OK),
}


def serve(server, directory, stop):
    """Answers every request on server, a listening socket, until stop (a
    threading.Event) is set, then returns, any request in hand finished
    first. Each report is saved in directory as run-0001.json,
    run-0002.json, and so on, in the order they arrive. A connection
    sending no request, eg a check that the collector is up, is skipped."""
    directory = Path(directory)
    server.settimeout(POLL)
    n = 0
    while not stop.is_set():
        try:
            client, _ = server.accept()
        except TimeoutError:
            continue
        client.settimeout(5)
        with client:
            if _receive(client, directory, f"run-{n + 1:04d}.json"):
                n += 1


def _receive(client, directory, name):
    """Answers the one HTTP request on client, and returns whether a report
    was saved in directory as name. A client that closes without sending a
    request is closed unanswered."""
    reader = client.makefile("rb")
    headers = []
    while (line := reader.readline()) not in (b"", b"\r\n"):
        headers.append(line.decode("latin-1"))
    if not headers:
        return False
    method, _, rest = headers[0].partition(" ")
    probe = PROBES.get(rest.split(" ")[0]) if method == "GET" else None
    if probe:
        _reply(client, "200 OK" if probe(directory) else "503 Service Unavailable")
        return False
    return _answer(client, reader, headers, directory / name)


def _answer(client, reader, headers, path):
    """Reads the body of a request with headers and saves it at path. The
    200 is sent only once it is saved, so a 200 always means the report is
    on disk. A body shorter than its Content-Length, eg from a sender that
    died mid-send, is answered 400 and not saved. A save that fails is
    answered 500. Returns whether it was saved."""
    length = sum(
        int(value) for name, _, value in (h.partition(":") for h in headers[1:])
        if name.strip().lower() == "content-length"
    )
    body = reader.read(length)
    if len(body) < length:
        _reply(client, "400 Bad Request")
        return False
    try:
        _save(path, body)
    except OSError:
        _reply(client, "500 Internal Server Error")
        return False
    _reply(client, "200 OK")
    return True


def _save(path, body):
    """Saves body at path whole or not at all: it is written to path.tmp
    and renamed, so a collector stopped mid-write leaves no partial report
    under a run's name."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(body)
    os.replace(temporary, path)


def _reply(client, status):
    """Writes an HTTP response of status, with no body, to client."""
    client.sendall(f"HTTP/1.1 {status}\r\nContent-Length: 0\r\n\r\n".encode())


def main(argv):
    """The path_coverage_collector command: serves on PORT into DIR until
    sent TERM, then exits 0; -h prints its help."""
    if argv[:1] == ["-h"]:
        print(HELP, end="")
        return 0
    port, directory = argv
    Path(directory).mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    with socket.create_server(("0.0.0.0", int(port))) as server:
        serve(server, directory, stop)
    return 0


def command():
    """The installed path_coverage_collector script's entry point."""
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    command()

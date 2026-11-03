"""The post reporter: sends the JSON report to a collector, for runs whose
own files are thrown away, eg a failing docker build step."""

import http.client
from urllib.parse import urlsplit


def deliver(body, url):
    """POSTs body, the JSON report's text, to url, never through a proxy,
    which could not reach a collector local to the run, and returns the
    reply's status, eg 200 once the collector has saved it. A collector
    that cannot be reached, or does not answer within a second, is passed
    over in silence, returning None: the run's own output and exit status
    must stay as they are."""
    parts = urlsplit(url)
    try:
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=1)
        try:
            connection.request(
                "POST", parts.path or "/", body.encode(), {"Content-Type": "application/json"}
            )
            return connection.getresponse().status
        finally:
            connection.close()
    except (OSError, http.client.HTTPException):
        return None

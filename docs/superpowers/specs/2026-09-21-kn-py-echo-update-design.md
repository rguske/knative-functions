# kn-py-echo: Dependency Update + Podman/Containerfile Build Path

## Context

`kn-py-echo` is a Knative/CloudEvents echo function written in Flask. It is
currently built exclusively via Cloud Native Buildpacks (`pack build`), and
its `requirements.txt` is stale: it pins `Flask==2.3.2` and
`cloudevents==1.2.0`, formatted as a manually-maintained dependency tree
(indented lines showing which package pulled in which transitive dependency).

Goals:
1. Bring dependencies up to date.
2. Add a `Containerfile`-based build path usable with Podman, as an
   alternative to Buildpacks (both remain supported).

## Decisions

- **Dependency pinning strategy:** Pin only top-level direct dependencies
  (`Flask`, `cloudevents`). Transitive dependencies are resolved by pip at
  install/build time rather than manually pinned and tracked.
- **Web server:** Keep Flask's built-in dev server (`flask run`), matching
  today's `Procfile`. No gunicorn/production WSGI server is introduced. This
  keeps the Buildpacks and Containerfile paths behaviorally identical and
  avoids adding a new dependency.
- **Python version:** Target Python 3.12 for the `Containerfile` base image.
- **Containerfile naming:** A single `Containerfile` (Podman-native name).
  No duplicate `Dockerfile` is added; `docker build -f Containerfile .` works
  if ever needed since the syntax is standard OCI build syntax.

## Changes

### 1. `requirements.txt`

Replace the manually-pinned dependency tree with a flat, top-level-only list:

```
Flask==3.1.3
cloudevents==2.2.0
```

### 2. `handler.py` — breaking API change in `cloudevents` 2.x

Verified against the actual `cloudevents==2.2.0` package contents: the
top-level `cloudevents.http` module (used today as
`from cloudevents.http import from_http`) has been removed entirely in 2.x.
The event's attributes are also no longer conveniently reachable via the
private `event._attributes` field in the way the old code relied on.

New usage (v2 "core" API):

```python
from cloudevents.core.bindings.http import from_http_event, HTTPMessage

event = from_http_event(HTTPMessage(dict(request.headers), request.get_data()))
attributes = dict(event.get_attributes())  # public accessor, was event._attributes
data = event.get_data()                    # was event.data
```

Behavioral notes:
- The new SDK validates `time` as a timezone-aware `datetime` object (not a
  plain string). `json.dumps(...)` must be called with `default=str` so
  serialization doesn't break; the logged output format is otherwise
  unchanged.
- Success/error response behavior (`204` on success, `400` + JSON body with
  `status`/`error` keys on failure) is preserved exactly.

### 3. New file: `Containerfile`

- Base image: `python:3.12-slim`
- Copies `requirements.txt`, runs `pip install --no-cache-dir -r requirements.txt`
- Copies `handler.py`
- Creates and switches to a non-root user (parity with Buildpacks-produced
  images, which also run as non-root)
- `ENV PORT=8080`, `EXPOSE 8080`
- `CMD` runs the same command as the existing `Procfile`:
  `flask run --host=0.0.0.0 --port=$PORT` (with `FLASK_APP=handler.py`)

### 4. `README.md`

- Add a new subsection documenting the Podman build/run flow, placed
  alongside (not replacing) the existing "Build with `pack`" step:
  ```bash
  podman build -t <registry>/kn-py-echo:1.3 -f Containerfile .
  podman run -e PORT=8080 -it --rm -p 8080:8080 <registry>/kn-py-echo:1.3
  ```
- Existing Buildpacks instructions remain unchanged in substance; both build
  paths are documented as valid options.

### Out of scope / unchanged

- `function.yaml` — no changes needed.
- `Procfile` — unchanged; still used by the Buildpacks path.
- `test/testevent.json`, `test/event.json` — unchanged, used to verify both
  build paths produce identical runtime behavior.

## Verification Plan

1. `podman build -t kn-py-echo:test -f Containerfile .` succeeds.
2. `podman run -e PORT=8080 -it --rm -p 8080:8080 kn-py-echo:test`, then in a
   second terminal: `curl -i -d@test/testevent.json localhost:8080` returns
   `HTTP/1.0 204 NO CONTENT`, and the container logs show the decoded
   CloudEvent JSON (same shape as documented in the README today).
3. Confirm `pack build -B gcr.io/buildpacks/builder:v1 <image>` still
   succeeds with the updated `requirements.txt`/`handler.py` (Buildpacks path
   unaffected in principle, but validated since `handler.py` changed).

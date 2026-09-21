# kn-py-echo Dependency Update + Podman Build Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `kn-py-echo`'s dependencies to current stable releases (migrating `handler.py` off the removed `cloudevents.http` API), and add a `Containerfile` build path usable with Podman alongside the existing Buildpacks path.

**Architecture:** No architectural change — this is a dependency bump plus one new build artifact. `handler.py` moves from the removed `cloudevents.http` module to the current `cloudevents.core.bindings.http` module while preserving identical request/response behavior. `requirements.txt` switches from a hand-maintained dependency tree to a flat, top-level-only pin list. A new `Containerfile` provides a Podman/Docker-buildable equivalent to the existing `pack build` (Buildpacks) flow, running the same Flask dev server command as today's `Procfile`.

**Tech Stack:** Python 3.12, Flask 3.1.3, cloudevents 2.2.0, Podman (or Docker), Cloud Native Buildpacks (`pack` CLI, unchanged).

## Global Constraints

- `requirements.txt` pins only direct/top-level dependencies (`Flask`, `cloudevents`); transitive deps are resolved by pip, not manually pinned.
- No new runtime dependency is introduced (no gunicorn) — both build paths run Flask's dev server via `flask run`.
- Containerfile base image: `python:3.12-slim`.
- New build artifact is named `Containerfile` (not `Dockerfile`); no duplicate file is created.
- `function.yaml` and `Procfile` are unchanged.
- Directory: `serverless/knative/knative-functions/kn-py-echo/` (all file paths below are relative to this directory unless stated otherwise).

---

### Task 1: Update `requirements.txt` and migrate `handler.py` to `cloudevents` 2.x API

**Files:**
- Modify: `kn-py-echo/requirements.txt`
- Modify: `kn-py-echo/handler.py`

**Interfaces:**
- Produces: `handler.py`'s Flask app object `app` (module-level), route `POST /` returning `(dict, 204)` on success or `(flask.Response, 400)` on failure — consumed by Task 2 (Containerfile `CMD`) and Task 3 (manual curl verification). No other task depends on internal function names.

- [ ] **Step 1: Replace `requirements.txt` contents**

Replace the entire file with:

```
Flask==3.1.3
cloudevents==2.2.0
```

- [ ] **Step 2: Rewrite `handler.py` to use the current `cloudevents` API**

Replace the entire file with:

```python
from flask import Flask, request, jsonify
from cloudevents.core.bindings.http import from_http_event, HTTPMessage
import logging, json

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

app = Flask(__name__)
@app.route('/', methods=['POST'])
def echo():
    try:
        event = from_http_event(HTTPMessage(dict(request.headers), request.get_data()))

        data = event.get_data()
        # hack to handle non JSON payload, e.g. xml
        if not isinstance(data,dict):
            data = str(data)

        e = {
            "attributes": dict(event.get_attributes()),
            "data": data
        }
        app.logger.info(f'"***cloud event*** {json.dumps(e, default=str)}')
        return {}, 204
    except Exception as e:
        sc = 400
        msg = f'could not decode cloud event: {e}'
        app.logger.error(msg)
        message = {
            'status': sc,
            'error': msg,
        }
        resp = jsonify(message)
        resp.status_code = sc
        return resp

# hint: run with FLASK_ENV=development FLASK_APP=handler.py flask run
if __name__ == "__main__":
    app.run()
```

Notes on the diff from the old version:
- Import changed from `from cloudevents.http import from_http` (module removed in `cloudevents` 2.x) to `from cloudevents.core.bindings.http import from_http_event, HTTPMessage`.
- `from_http(request.headers, request.get_data(), None)` → `from_http_event(HTTPMessage(dict(request.headers), request.get_data()))`.
- `event._attributes` (private field) → `dict(event.get_attributes())` (public accessor; wrapped in `dict()` since it returns a read-only `Mapping`).
- `event.data` → `event.get_data()`.
- `json.dumps(e)` → `json.dumps(e, default=str)` — required because the new SDK stores `time` as a real `datetime` object (not a string), which isn't JSON-serializable by default.

- [ ] **Step 3: Verify locally with a virtualenv**

```bash
cd kn-py-echo
python3 -m venv .venv-check && source .venv-check/bin/activate
pip install --no-cache-dir -r requirements.txt
FLASK_APP=handler.py FLASK_ENV=development flask run --port=8080 &
sleep 2
curl -i -d@test/testevent.json localhost:8080
```

Expected: `HTTP/1.0 204 NO CONTENT`. Then stop the server and clean up:

```bash
kill %1
deactivate
rm -rf .venv-check
```

- [ ] **Step 4: Commit**

```bash
cd kn-py-echo
git add requirements.txt handler.py
git commit -m "chore(kn-py-echo): update Flask/cloudevents deps, migrate handler.py to cloudevents 2.x API"
```

---

### Task 2: Add `Containerfile` for Podman/Docker builds

**Files:**
- Create: `kn-py-echo/Containerfile`

**Interfaces:**
- Consumes: `kn-py-echo/requirements.txt` and `kn-py-echo/handler.py` from Task 1 (must exist and be install/runnable as-is).
- Produces: a container image whose entrypoint serves `POST /` on `$PORT` (default `8080`) — consumed by Task 3's manual verification.

- [ ] **Step 1: Create `Containerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV FLASK_APP=handler.py
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=${PORT}"]
```

- [ ] **Step 2: Build the image with Podman**

```bash
cd kn-py-echo
podman build -t kn-py-echo:test -f Containerfile .
```

Expected: build completes with `COMMIT kn-py-echo:test` (or equivalent success output), no errors.

- [ ] **Step 3: Run and verify with curl**

```bash
podman run -e PORT=8080 -d --rm -p 8080:8080 --name kn-py-echo-test kn-py-echo:test
sleep 2
curl -i -d@test/testevent.json localhost:8080
podman logs kn-py-echo-test
podman stop kn-py-echo-test
```

Expected: `curl` prints `HTTP/1.0 204 NO CONTENT`; `podman logs` shows a line containing `"***cloud event***` with the decoded attributes/data JSON.

- [ ] **Step 4: Commit**

```bash
cd kn-py-echo
git add Containerfile
git commit -m "feat(kn-py-echo): add Containerfile for Podman/Docker builds"
```

---

### Task 3: Document the Podman build path in `README.md`

**Files:**
- Modify: `kn-py-echo/README.md`

**Interfaces:**
- Consumes: `kn-py-echo/Containerfile` from Task 2 (referenced by path/name in the new doc section).

- [ ] **Step 1: Add a "Build with Podman" subsection**

In `README.md`, immediately after the existing `## Step 1 - Build with \`pack\`` section (and its closing code block for `pack build ...`), insert a new subsection:

```markdown
## Step 1 (alternative) - Build with Podman

Instead of Buildpacks, you can build the container image directly from the
included `Containerfile` using [Podman](https://podman.io) (or Docker):

\`\`\`bash
IMAGE=<registry>/kn-py-echo:1.3
podman build -t ${IMAGE} -f Containerfile .
\`\`\`

Run it the same way as the Buildpacks-built image (see Step 2 below):

\`\`\`bash
podman run -e PORT=8080 -it --rm -p 8080:8080 ${IMAGE}
\`\`\`
```

(Use literal triple-backtick fences in the actual file, not escaped — the escaping above is only to nest this code block inside the plan document.)

- [ ] **Step 2: Update the example image tag**

In the existing `pack build` and `docker push`/`docker run` examples further down the README, bump the example tag from `1.2` to `1.3` to match the new subsection, for consistency (cosmetic only — functionally the tag is a placeholder either way).

- [ ] **Step 3: Verify rendering**

Open `README.md` in a Markdown preview (or `cat` it) and confirm the new subsection reads correctly and code fences are balanced (no stray/unmatched \`\`\`).

- [ ] **Step 4: Commit**

```bash
cd kn-py-echo
git add README.md
git commit -m "docs(kn-py-echo): document Podman/Containerfile build path"
```

---

## Self-Review Notes

- **Spec coverage:** requirements.txt update (Task 1), handler.py cloudevents 2.x migration (Task 1), Containerfile (Task 2), README documentation (Task 3), verification via podman build/run/curl (Task 2 Step 3), Buildpacks path left untouched (no task modifies `function.yaml`/`Procfile`) — all spec items covered.
- **Placeholder scan:** none found; all steps contain literal file contents and exact commands.
- **Type/name consistency:** `handler.py`'s Flask route and `app` object are referenced consistently across Task 1 (definition), Task 2 (Containerfile `CMD` invoking `flask run` against `FLASK_APP=handler.py`), and Task 3 (docs). `PORT` env var name is consistent across `Procfile` (unchanged), `Containerfile`, and README examples.

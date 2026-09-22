# kn-py-echo

Example Python function with `Flask` REST API running in Knative to echo
[CloudEvents](https://github.com/cloudevents/sdk-python).

## Step 1 - Build with `Buildpacks`

[Buildpacks](https://buildpacks.io) are used to create the container image.

```shell
IMAGE=<docker-username>/<repo>/kn-py-echo:1.3
pack build -B gcr.io/buildpacks/builder:v1 ${IMAGE}
```

## Step 1 (alternative) - Build with Podman

Instead of Buildpacks, you can build the container image directly from the
included `Containerfile` using [Podman](https://podman.io):

```shell
IMAGE=<registry>/<repo>/kn-py-echo:1.3
podman build -t ${IMAGE} -f Containerfile .
```

## Step 1 (alternative) - Build a multi-arch image with Podman

If the image needs to run on nodes with different CPU architectures (e.g.
`amd64` and `arm64` in the same cluster), build a multi-arch manifest list
instead of a single-platform image. On macOS, `podman machine` ships with
the QEMU emulation needed to build for architectures other than the host's,
so this works out of the box — no extra setup required.

```shell
IMAGE=<registry>/<repo>/kn-py-echo:1.3
podman manifest create ${IMAGE}
podman build --platform=linux/amd64,linux/arm64 --manifest ${IMAGE} -f Containerfile .
```

Push the whole manifest list (both architectures) to the registry:

```shell
podman manifest push --all ${IMAGE} docker://${IMAGE}
```

Verify the pushed manifest references both architectures:

```shell
podman manifest inspect ${IMAGE}
```

## Step 2 - Test

Verify the container image works by executing it locally.

```bash
podman run -e PORT=8080 -it --rm -p 8080:8080 ${IMAGE}
```

You should see output similar to the following:

```shell
 * Serving Flask app 'handler.py'
 * Debug mode: off
2026-09-21 08:49:50,112 INFO werkzeug MainThread : WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://10.88.0.68:8080
2026-09-21 08:49:50,112 INFO werkzeug MainThread : Press CTRL+C to quit
 ```

In a separate terminal window, use the `testevent.json` file to validate the function is working.

```shell
curl -i -d@test/testevent.json localhost:8080
```

You should see output similar to this below.

```json
2026-09-21 08:50:33,781 INFO handler Thread-1 (process_request_thread) : ***cloud event*** {
  "context_attributes": {
    "id": "08179137-b8e0-4973-b05f-8f212bf5003b",
    "source": "https://10.0.0.1:443/sdk",
    "specversion": "1.0",
    "type": "com.vmware.vsphere.VmPoweredOffEvent.v0",
    "time": "2020-02-11 21:29:54.905253+00:00",
    "datacontenttype": "application/json"
  },
  "extensions": {
    "eventclass": "event"
  },
  "data": {
    "Key": 9902,
    "ChainId": 9895,
    "CreatedTime": "2020-02-11T21:28:23.677595Z",
    "UserName": "VSPHERE.LOCAL\\Administrator",
    "Datacenter": {"Name": "testDC", "Datacenter": {"Type": "Datacenter", "Value": "datacenter-2"}},
    "ComputeResource": {"Name": "cls", "ComputeResource": {"Type": "ClusterComputeResource", "Value": "domain-c7"}},
    "Host": {"Name": "10.185.22.74", "Host": {"Type": "HostSystem", "Value": "host-21"}},
    "Vm": {"Name": "test-01", "Vm": {"Type": "VirtualMachine", "Value": "vm-56"}},
    "Ds": null,
    "Net": null,
    "Dvs": null,
    "FullFormattedMessage": "test-01 on  10.0.0.1 in testDC is powered off",
    "ChangeTag": "",
    "Template": false
  }
}
2026-09-21 08:50:33,783 INFO werkzeug Thread-1 (process_request_thread) : 192.168.127.1 - - [21/Sep/2026 08:50:33] "POST / HTTP/1.1" 200 -
```

The response body mirrors this same structure, split into `context_attributes`
(the [CloudEvents spec](https://github.com/cloudevents/spec) core fields),
`extensions` (any additional CloudEvent extension attributes, e.g. Knative's
`kind`/`name`/`namespace`), and `data` (the event payload). The `extensions`
and `data` keys are omitted entirely when not present on the incoming event,
instead of rendering a misleading `null`.

## Step 3 - Deploy

> **Note:** The following steps assume a working Knative environment using the
`default` Rabbit `broker`. The Knative `service` and `trigger` will be installed in the
`vmware-functions` Kubernetes namespace, assuming that the `broker` is also available there.

Push your container image to an accessible registry such as Docker once you're done developing and testing your function logic.

```shell
docker push <docker-username>/<repo>/kn-py-echo:1.3
```

> If you built a multi-arch manifest list instead (Step 1 alternative
> above), push it with `podman manifest push --all` as shown there, rather
> than a plain `docker push` / `podman push`.

Edit the `function.yaml` file with the name of the container image from Step 1 if you made any changes. If not, the default VMware container image will suffice. By default, the function deployment will filter on the `VmPoweredOffEvent` vCenter Server Event. If you wish to change this, update the `subject` field within `function.yaml` to the desired event type.

Deploy the function to the VMware Event Broker Appliance (VEBA).

```shell
kubectl -n vmware-functions apply -f function.yaml
```

For testing purposes, the `function.yaml` contains the following annotations, which will ensure the Knative Service Pod will always run **exactly** one instance for debugging purposes. Functions deployed through through the VMware Event Broker Appliance UI defaults to scale to 0, which means the pods will only run when it is triggered by an vCenter Event.

```yaml
annotations:
  autoscaling.knative.dev/maxScale: "1"
  autoscaling.knative.dev/minScale: "1"
```

## Step 4 - Undeploy

```console
# undeploy function
kubectl -n vmware-functions delete -f function.yaml
```
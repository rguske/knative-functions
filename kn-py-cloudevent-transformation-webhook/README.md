# kn-py-cloudevent-transformation-function

⚠️ WIP

Example Knative Python function for receiving a custom json event (payload) which will be transformed into a CloudEvent.

# How the function works

The function starts a HTTP server, transforms an incoming json payload to a [CloudEvent](https://cloudevents.io/) and sends it to the configured `K_SINK` (injected via a Knative [`SinkBinding`](https://knative.dev/docs/eventing/custom-event-source/sinkbinding/)).

The webhook endpoint in the function, i.e. the HTTP `POST` target, by default is `/webhook` (configurable.)

See the [deployment](#step-3---deploy) section for configuration options and details.

The event transformation is done as follows:

| CloudEvent Field | Event Field | Comment                                                                                                                 | Example                                |
|------------------|--------------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| `ID`             | tbd                | An `ID` specified in UUIDv4 format                                                                                   | `0866ff41-0d90-4003-a0a6-06b4c0d16cfa` |
| `Source`         | tbd                | The source is fixed in this version.                                   | `/kn-py-cloudevent-transformation-function`                |
| `Type`           | `type`             | Event `type` field is lower-cased and injected into a fixed CloudEvent `Type` format (`my.very.own.cloudevent."f"{payload['action']}.v0`) | `my.very.own.cloudevent.created.v0`   |
| `Time`           | `time`         | Systemtime                                                                                   | `2023-09-11T13:26:37.469567Z`                 |
| `Data`           | tbd                | JSON-encoded data event                                                                                          |                                        |

A full example of a structured CloudEvent (JSON):

```json
{
	"action": "created",
	"example": {
	  "attendee": {
		"feelings": "EXCITED"
	  }
	},
	"actuator": {
	  "event": {
		"organization": "Container Days 2023"
	  }
	},
	"next": {
		"up": "Coffee Break - W00t"
	},
	"command_id": "0866ff41-0d90-4003-a0a6-06b4c0d16cfa"
}
```

# Step 1 - Build

[Buildpacks](https://buildpacks.io) are used to create the container image.

Create the container image locally to test your function logic. Change the IMAGE name accordingly, example below for Docker.

```console
export IMAGE=<docker username>/kn-py-cloudevent-transformation-function:1.0
pack build -B gcr.io/buildpacks/builder:v1 ${IMAGE}
```

# Step 2 - Test

Verify the container image works by executing it locally.

Change into the `test` directory

```console
cd test
```

Start the container image by running the following command:

```shell
docker run -e PORT=8080 --env-file docker-test-env-variable -it --rm -p 8080:8080 ${IMAGE}
```

You should see output similar to the following:

```shell
 * Serving Flask app 'handler.py'
 * Debug mode: off
2023-07-24 11:02:33,324 INFO werkzeug MainThread : WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://172.17.0.3:8080
2023-07-24 11:02:33,324 INFO werkzeug MainThread : Press CTRL+C to quit
```

```
docker ps -a

CONTAINER ID   IMAGE                                                                        COMMAND                  CREATED          STATUS                   PORTS                                                NAMES
eca1a2f27ef0   rguske/kn-py-cloudevent-transformation-function:1.0   "/cnb/process/web"       10 seconds ago   Up 9 seconds             0.0.0.0:8080->8080/tcp                               lucid_boyd
```

# Step 2 - Test

In a separate terminal window, go to the test directory and use the `test-payload.json`` file to validate the function is working.

Send the json payload to the webhook endpoint. The following json blob will be used as a simulated test-event:

`cat test-payload.json`

```json
{
	"action": "created",
	"example": {
	  "attendee": {
		"feelings": "EXCITED"
	  }
	},
	"actuator": {
	  "event": {
		"organization": "Container Days 2023"
	  }
	},
	"next": {
		"up": "Coffee Break - W00t"
	},

	"command_id": "0866ff41-0d90-4003-a0a6-06b4c0d16cfa"
  }
```

Send the json payload to the `/webhook` endpoint:

```shell
curl -s -d@test-payload.json http://127.0.0.1:8080/webhook -H 'Content-Type: application/json'
```

You should see an output like:

```shell
{'specversion': '1.0', 'type': 'my.very.own.cloudevent.created.v0', 'datacontenttype': 'application/json', 'source': '/kn-py-cloudevent-transformation-function', 'id': '0866ff41-0d90-4003-a0a6-06b4c0d16cfa', 'time': '2023-09-11T11:02:39.283277Z', 'data': ......}}
2023-09-11 11:02:39,290 INFO werkzeug Thread-1 (process_request_thread) : 172.17.0.1 - - [24/Jul/2023 11:02:39] "POST /webhook HTTP/1.1" 500 -
```

The `http` 500 error is expected since the transformed json blob couldn't be send to a `K_SINK`. Important in this local test, is the transformed event.

# Step 3 - Deploy

⚠️ The following steps assume a working Knative environment using the `rabbitmq-broker` or the [MTChannelBasedBroker](https://knative.dev/docs/eventing/brokers/broker-types/channel-based-broker/). The Knative `service` and `sinkbinding` will be installed in
 the `vmware-functions` Kubernetes namespace, assuming that the `broker` is also
 available there.

## Deploy the Function

Create the `SinkBinding` which will automatically inject the Knative `broker` into the function.

```bash
kubectl create -f sinkbinding.yaml -n vmware-functions
```

Deploy the function to Knative:

```bash
kubectl create -f function.yaml -n vmware-functions
```

For testing purposes, the [Knative manifest](function.yaml) contains the
following annotations, which will ensure the Knative Service Pod will always run
**exactly** one instance for debugging purposes.

```yaml
annotations:
  autoscaling.knative.dev/maxScale: "1"
  autoscaling.knative.dev/minScale: "1"
```

# Step 4 - Undeploy

```bash
# undeploy function
kubectl delete -f function.yaml -n vmware-functions

# undeploy sinkbinding
kubectl delete -f sinkbinding.yaml -n vmware-functions

# delete secret
kubectl delete secret webhook-auth -n vmware-functions
```

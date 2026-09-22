from flask import Flask, request, Response
from cloudevents.core.bindings.http import from_http_event, HTTPMessage
import logging, json

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

app = Flask(__name__)

# CloudEvents spec v1.0 core context attributes. Anything else present on an
# event's attribute set is a CloudEvent *extension* attribute (e.g. Knative's
# "kind"/"name"/"namespace"/"network"/"storageclass" on apiserversource
# events).
CORE_ATTR_KEYS = {
    "specversion", "type", "source", "subject", "id", "time",
    "datacontenttype", "dataschema",
}


def split_attributes(attributes):
    """Split a CloudEvent's attribute dict into (context_attributes, extensions)."""
    context_attributes = {}
    extensions = {}
    for key, value in attributes.items():
        if key in CORE_ATTR_KEYS:
            context_attributes[key] = value
        else:
            extensions[key] = value
    return context_attributes, extensions


@app.route('/', methods=['POST'])
def echo():
    try:
        event = from_http_event(HTTPMessage(dict(request.headers), request.get_data()))

        data = event.get_data()
        # Preserve values that are already JSON-native (including None/null,
        # e.g. events with no data body) as-is. Only stringify anything else
        # (e.g. raw XML bytes) so it doesn't break json.dumps below.
        if data is not None and not isinstance(data, (dict, list, str, int, float, bool)):
            data = str(data)

        context_attributes, extensions = split_attributes(dict(event.get_attributes()))

        e = {"context_attributes": context_attributes}
        if extensions:
            e["extensions"] = extensions
        # Omit the "data" key entirely when there is no payload (e.g. Knative
        # apiserversource delete events carry no VM spec body), instead of
        # emitting a misleading "data": null.
        if data is not None:
            e["data"] = data
        payload = json.dumps(e, indent=2, default=str)
        app.logger.info(f'***cloud event*** {payload}')
        return Response(payload, status=200, mimetype='application/json')
    except Exception as e:
        sc = 400
        msg = f'could not decode cloud event: {e}'
        app.logger.error(msg)
        message = {
            'status': sc,
            'error': msg,
        }
        resp = Response(json.dumps(message, indent=2), status=sc, mimetype='application/json')
        return resp

# hint: run with FLASK_ENV=development FLASK_APP=handler.py flask run
if __name__ == "__main__":
    app.run()

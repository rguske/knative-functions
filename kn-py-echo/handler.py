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

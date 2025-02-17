import json,os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import logging,json

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Receive the JSON payload
    payload = request.json

    try:
        current_time = datetime.utcnow().isoformat() + "Z"
        # Perform field mapping for CloudEvent.io compliance
        cloud_event = {
            "specversion": "1.0",
            "type": "my.very.own.cloudevent."f"{payload['action']}.v0",
            "datacontenttype": "application/json",
            "source": "/kn-py-cloudevent-transformation-function",
            "id": payload["command_id"],
            "time": current_time,
            "data": {
                "action": payload["action"],
                "example": {
                    "attendee": {
                        "feelings": payload["example"]["attendee"]["feelings"]
                    }
                },
                "actuator": {
                    "event": {
                        "organization": payload["actuator"]["event"]["organization"]
                    }
                },
                "next": {
                    "up": payload["next"]["up"]
                },
                "command_id": payload["command_id"]
            }
        }

        # Convert the CloudEvent payload to JSON with ordered keys
        json_output = json.dumps(cloud_event, indent=2, sort_keys=False)

        # Send the CloudEvent payload to the target Sink/Broker
        target = os.getenv("K_SINK")
        if not target:
            return jsonify({"error": "K_SINK environment variable not set"}), 500

        headers = {"Content-Type": "application/cloudevents+json"}

        print(cloud_event)  # Print to stdout
        response = requests.post(target, json=cloud_event, headers=headers)

        if response.status_code >= 200 and response.status_code <= 299:
            return jsonify({"message": "CloudEvent payload sent to SinkBinding"}), 200
        else:
            return jsonify({"error": "Failed to send CloudEvent payload to SinkBinding"}), 500

    except KeyError as e:
        error_message = f"Missing required field: {str(e)}"
        return jsonify({"error": error_message}), 400

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    app.run()

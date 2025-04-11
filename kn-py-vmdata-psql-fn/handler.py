from flask import Flask, request, jsonify
from cloudevents.http import from_http
import time
import psycopg2
import os

app = Flask(__name__)

# Track seen CloudEvent IDs
seen_ids = set()

# Load and validate required environment variables
REQUIRED_ENV_VARS = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT', 5432))  # Ensure this is an integer
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@app.route("/", methods=["GET", "POST"])
# def root():
#     if request.method == "GET":
#         return "OK", 200  # for readiness/liveness probes
#     elif request.method == "POST":
#         return jsonify({"message": "POST received at root"}), 200  # optional
# def health():
#     return "OK", 200
def receive_event():
    print("📥 Received POST request")
    print("Headers:", dict(request.headers))
    print("Content-Type:", request.content_type)

    # Pull values from CloudEvent headers
    headers = request.headers

    event_id = headers.get("Ce-Id")
    print("CloudEvent ID:", event_id)

    # Skip duplicate events
    if event_id in seen_ids:
        print("🟡 Duplicate event detected, skipping:", event_id)
        return jsonify({"status": "skipped", "reason": "duplicate event"}), 200

    # Mark as seen
    seen_ids.add(event_id)

    # ⏱️ Start timing here
    start_time = time.time()

    transformed_data = {
        "type": headers.get("Ce-Type"),
        "id": headers.get("Ce-Id"),
        "kind": headers.get("Ce-Kind"),
        "name": headers.get("Ce-Name"),
        "namespace": headers.get("Ce-Namespace"),
        "time": headers.get("Ce-Time"),
        "cpucores": int(headers.get("Ce-Cpucores", 0)),
        "cpusockets": int(headers.get("Ce-Cpusockets", 0)),
        "memory": headers.get("Ce-Memory"),
        "storageclass": headers.get("Ce-Storageclass"),
        "network": headers.get("Ce-Network")
    }

    print("Transformed data:", transformed_data)

    # DB insert logic here (same as before)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO virtual_machines (type, id, kind, name, namespace, time, cpucores, cpusockets, memory, storageclass, network)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            transformed_data["type"],
            transformed_data["id"],
            transformed_data["kind"],
            transformed_data["name"],
            transformed_data["namespace"],
            transformed_data["time"],
            transformed_data["cpucores"],
            transformed_data["cpusockets"],
            transformed_data["memory"],
            transformed_data["storageclass"],
            transformed_data["network"]
        ))
        conn.commit()
        cur.close()
        conn.close()

        # ⏱️ Stop timing here
        duration = time.time() - start_time
        print(f"✅ Event {event_id} processed in {duration:.2f} seconds")

        return jsonify({"status": "✅ success"}), 200
    except Exception as e:
        print("🔥 Database insert failed:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

import os
from flask import Flask, request, jsonify
from cloudevents.http import from_http
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Load and validate required environment variables
REQUIRED_ENV_VARS = ['SMTP_SERVER', 'SMTP_PORT', 'EMAIL_SENDER', 'EMAIL_PASSWORD', 'RECIPIENT_EMAIL']
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))  # Ensure this is an integer
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')


def send_email(subject, body, recipient):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print(f"Connecting to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(2)  # Enable detailed SMTP logs
        server.starttls()
        print("Attempting to login...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        print("Login successful!")
        server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        server.quit()
        print("Email sent successfully")
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False


@app.route("/", methods=["POST"])
def handle_cloudevent():
    try:
        event = from_http(request.headers, request.get_data())

        subject = f"CloudEvent Received: {event.get('type', 'Unknown Type')}"
        body = f"""CloudEvent Details:

Type: {event.get('type', 'N/A')}
Source: {event.get('source', 'N/A')}
ID: {event.get('id', 'N/A')}
Name: {event.get('name', 'N/A')}
Namespace: {event.get('namespace', 'N/A')}
Kind: {event.get('kind', 'N/A')}
CPU-Cores: {event.get('cpu-cores', 'N/A')}
CPU-Sockets: {event.get('cpu-sockets', 'N/A')}
CPU-Threads: {event.get('cpu-threads', 'N/A')}
Memory: {event.get('memory', 'N/A')}
StorageClass: {event.get('storageclass', 'N/A')}
Network: {event.get('network', 'N/A')}
"""

        print(f"Sending email to {RECIPIENT_EMAIL} with subject '{subject}'")
        success = send_email(subject, body, RECIPIENT_EMAIL)

        if success:
            return jsonify({"message": "Email sent successfully"}), 200
        else:
            return jsonify({"message": "Failed to send email"}), 500
    except Exception as e:
        print(f"Error processing CloudEvent: {e}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

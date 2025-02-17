# kn-py-email-fn

⚠️ WIP

Knative email function which sends a CloudEvent to an email recipient.

## Testing

export IMAGE="quay.io/rguske/kn-py-email-fn:1.0"

podman run -e PORT=8080 -it --rm -p 8080:8080 --env EMAIL_SECRET="$(cat email_secret.json)" ${IMAGE}

curl -i -d@test/testevent.json localhost:8080

## Deployment

```code
kubectl create secret generic email-secret \
  --from-literal=smtp_server="" \
  --from-literal=smtp_port="" \
  --from-literal=email_sender="" \
  --from-literal=email_password="" \
  --from-literal=recipient_email=""
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-service
spec:
  template:
    spec:
      containers:
      - name: email-container
        image: your-email-handler-image:latest
        env:
        - name: SMTP_SERVER
          valueFrom:
            secretKeyRef:
              name: email-config
              key: smtp_server
        - name: SMTP_PORT
          valueFrom:
            secretKeyRef:
              name: email-config
              key: smtp_port
        - name: EMAIL_SENDER
          valueFrom:
            secretKeyRef:
              name: email-config
              key: email_sender
        - name: EMAIL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: email-config
              key: email_password
        - name: RECIPIENT_EMAIL
          valueFrom:
            secretKeyRef:
              name: email-config
              key: recipient_email
```

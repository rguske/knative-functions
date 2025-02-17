
$headers = @{
    "Content-Type" = "application/json";
    "ce-specversion" = "1.0";
    "ce-id" = "2da43885-5e52-4c7f-80f8-7ccd337bab3f";
    "ce-source" = "https://198.48.0.1:443";
    "ce-type" = "dev.knative.apiserver.resource.update";
    "ce-time" = "2023-09-07T14:48:09.308148663Z";
}

$body = Get-Content -Raw -Path "./test-payload.json"

Write-Host "Testing Function ..."
Invoke-WebRequest -Uri http://localhost:8080 -Method POST -Headers $headers -Body $body

Write-host "See docker container console for output"
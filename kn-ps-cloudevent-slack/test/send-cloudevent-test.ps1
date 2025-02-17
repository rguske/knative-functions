
$headers = @{
    "Content-Type" = "application/json";
    "ce-specversion" = "1.0";
    "ce-id" = "d70079f9-fddd-4b7f-aa76-1193f28b0611";
    "ce-source" = "/kn-py-cloudevent-transformation-function";
    "ce-type" = "my.very.own.cloudevent.created.v0";
    "ce-time" = "2022-09-11T11:42:42Z";
}

$body = Get-Content -Raw -Path "./test-payload.json"

Write-Host "Testing Function ..."
Invoke-WebRequest -Uri http://localhost:8080 -Method POST -Headers $headers -Body $body

Write-host "See docker container console for output"
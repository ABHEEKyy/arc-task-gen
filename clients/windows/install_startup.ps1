$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$python = (Get-Command py.exe).Source
$taskName = "Jarvis Ambient Voice Assistant"
$script = Join-Path $PSScriptRoot "alexa_backend.py"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "-3 `"$script`"" `
    -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts the local J.A.R.V.I.S. ambient voice listener at sign-in." `
    -Force | Out-Null

Write-Host "Installed '$taskName'. It will start automatically at your next sign-in."
Write-Host "To start it now, run: Start-ScheduledTask -TaskName '$taskName'"
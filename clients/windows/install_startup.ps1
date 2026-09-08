$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$python = (Get-Command pyw.exe -ErrorAction SilentlyContinue)
if (-not $python) {
    $python = (Get-Command py.exe).Source
} else {
    $python = $python.Source
}

$taskName = "Jarvis Ambient Voice Assistant"
$script = Join-Path $PSScriptRoot "jarvis_daemon.py"

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Runs lightweight Jarvis wake daemon in background. Pops up CMD terminal when JARVIS is called." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Jarvis Background Daemon installed & started! It will pop up the CMD terminal window automatically when you say 'JARVIS'."
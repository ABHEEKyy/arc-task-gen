Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
$shortcutPath = Join-Path $startupFolder "Run_Jarvis.lnk"
$batPath = "c:\Users\abhee\arc-task-gen\clients\windows\Run_Jarvis.bat"
$repoPath = "c:\Users\abhee\arc-task-gen"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $repoPath
$shortcut.Save()

Write-Host "Success: Run_Jarvis.bat will now automatically open on laptop startup!"

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
$shortcutPath = Join-Path $startupFolder "Run_Jarvis.lnk"
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$batPath = Join-Path $repoPath "Run_Jarvis.bat"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $repoPath
$shortcut.Save()

Write-Host "Success: Run_Jarvis.bat added to Windows Startup folder ($shortcutPath)!"


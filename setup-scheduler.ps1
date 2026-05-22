# Registers the Cairn scheduler as a Windows Task Scheduler task.
# Runs every 15 minutes. No UI; failures logged to stdout (visible in Task Scheduler history).
# Renamed 2026-05-22 from "life-os-bridge scheduler" to "cairn scheduler".
#
# Usage (PowerShell, elevated):
#   powershell -ExecutionPolicy Bypass -File setup-scheduler.ps1
#
# Remove with:
#   Unregister-ScheduledTask -TaskName "cairn scheduler" -Confirm:$false
#   (For the legacy task: Unregister-ScheduledTask -TaskName "life-os-bridge scheduler" -Confirm:$false)

$TaskName = "cairn scheduler"
$WorkDir = $PSScriptRoot
$PythonExe = (Get-Command pythonw).Source

if (-not $PythonExe) {
    Write-Error "pythonw not found on PATH"
    exit 1
}

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-m src.scheduler" `
    -WorkingDirectory $WorkDir

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Fires ntfy prompts for weight, validated scales, and activity nudges. Gated by quiet hours, busy-blocks.yaml, and Google Calendar."

$ErrorActionPreference = "Stop"
Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "Next run: $(Get-Date -Format 'HH:mm')"
Write-Host "View in Task Scheduler: taskschd.msc"

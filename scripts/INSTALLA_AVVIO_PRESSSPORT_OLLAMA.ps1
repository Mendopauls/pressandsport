# Press & Sport local worker: install per-user startup task, no admin rights.
param([string]$Python="python",[string]$Model="llama3.2")
$ErrorActionPreference="Stop"
$base=Join-Path $env:LOCALAPPDATA "PressSportOllama"
New-Item -ItemType Directory -Force -Path $base | Out-Null
$worker=Join-Path $PSScriptRoot "presssport_ollama_worker.py"
if(!(Test-Path $worker)){throw "File worker assente: $worker"}
$launcher=Join-Path $base "start-worker.cmd"
$command='@echo off'+[Environment]::NewLine+'cd /d "'+$PSScriptRoot+'"'+[Environment]::NewLine+'"'+$Python+'" "'+$worker+'" --root "'+$base+'" --model "'+$Model+'" >> "'+(Join-Path $base "worker.log")+'" 2>&1'
Set-Content -Path $launcher -Value $command -Encoding ascii
$action=New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "'+$launcher+'"')
$trigger=New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "PressSport-Ollama-Worker" -Action $action -Trigger $trigger -Settings $settings -Description "Press & Sport - ripresa automatica bozze Ollama" -Force | Out-Null
Write-Host "Task installato: PressSport-Ollama-Worker"
Write-Host "Cartella dati: $base"
Write-Host "Avvio manuale: Start-ScheduledTask -TaskName PressSport-Ollama-Worker"

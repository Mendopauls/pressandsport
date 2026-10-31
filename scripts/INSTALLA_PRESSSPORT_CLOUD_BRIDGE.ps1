# Press & Sport — separate cloud bridge autostart (per-user task).
param([string]$Model="qwen2.5:3b")
$ErrorActionPreference="Stop"
$dir=Join-Path $env:USERPROFILE "PressSportCloudV2\scripts"
$worker=Join-Path $dir "presssport_cloud_ollama_bridge.py"
if(!(Test-Path $worker)){throw "Bridge non trovato: $worker"}
$secret=[Environment]::GetEnvironmentVariable("PRESSSPORT_WORKER_SECRET","User")
if([string]::IsNullOrWhiteSpace($secret) -or $secret.Length -lt 32){throw "Credenziale Windows mancante o non valida"}
$python=(Get-Command python -ErrorAction Stop).Source
$root=Join-Path $env:LOCALAPPDATA "PressSportOllama"
New-Item -ItemType Directory -Force -Path $root | Out-Null
$launcher=Join-Path $root "start-cloud-bridge.cmd"
$lines=@(
'@echo off',
'setlocal',
'cd /d "'+$dir+'"',
'for /f "usebackq tokens=*" %%s in (`powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable(''PRESSSPORT_WORKER_SECRET'',''User'')"`) do set "PRESSSPORT_WORKER_SECRET=%%s"',
'"'+$python+'" "'+$worker+'" --model "'+$Model+'" >> "'+(Join-Path $root "cloud-bridge.log")+'" 2>&1'
)
# Do not persist the secret in this .cmd file.
[System.IO.File]::WriteAllLines($launcher,$lines,[System.Text.Encoding]::ASCII)
$action=New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c ""'+$launcher+'""') -WorkingDirectory $dir
$trigger=New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings=New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "PressSport-Ollama-Cloud-Bridge" -Action $action -Trigger $trigger -Settings $settings -Description "Press & Sport: recupero lavori cloud e bozze Ollama; nessuna pubblicazione" -Force | Out-Null
Write-Host "PASS: task PressSport-Ollama-Cloud-Bridge installato"
Write-Host "Avvia con Start-ScheduledTask -TaskName PressSport-Ollama-Cloud-Bridge"

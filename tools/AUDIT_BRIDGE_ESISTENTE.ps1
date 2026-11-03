# Press & Sport Cloud V2 - audit NON distruttivo del bridge Ollama.
# Uso: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\AUDIT_BRIDGE_ESISTENTE.ps1
# Nessun riavvio, installazione, trasmissione o pubblicazione. Non legge contenuto script / segreti / log.
$ErrorActionPreference = 'Continue'
$results = [ordered]@{
  audit = 'PressSport_Ollama_Existing_Bridge'
  audited_at = (Get-Date).ToString('o')
  host = $env:COMPUTERNAME
  checked_paths = @()
  python_scripts = @()
  scheduled_tasks = @()
  processes = @()
  logs = @()
}
$roots = @(
  (Join-Path $env:USERPROFILE 'PressSportCloudV2\scripts'),
  'C:\Users\savio\PressSportCloudV2\scripts',
  (Join-Path $env:LOCALAPPDATA 'PressSportOllama')
) | Select-Object -Unique
foreach ($root in $roots) {
  $found = Test-Path -LiteralPath $root -PathType Container
  $results.checked_paths += [ordered]@{ path = $root; exists = [bool]$found }
  if (-not $found) { continue }
  if ($root -like '*PressSportCloudV2*') {
    Get-ChildItem -LiteralPath $root -File -Filter '*ollama*bridge*.py' -ErrorAction SilentlyContinue |
      ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash
        $results.python_scripts += [ordered]@{
          path = $_.FullName
          name = $_.Name
          bytes = $_.Length
          modified_at = $_.LastWriteTime.ToString('o')
          sha256 = $hash
        }
      }
  } else {
    Get-ChildItem -LiteralPath $root -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Extension -in '.log','.json','.txt' } |
      Select-Object -First 30 | ForEach-Object {
        $results.logs += [ordered]@{ name=$_.Name; bytes=$_.Length; modified_at=$_.LastWriteTime.ToString('o') }
      }
  }
}
# Solo nomi, stati e orari: non esportare argomenti di task che possono contenere segreti.
Get-ScheduledTask -ErrorAction SilentlyContinue |
  Where-Object { $_.TaskName -match 'PressSport|Ollama' } |
  ForEach-Object {
    $task = $_
    $info = $null
    try { $info = $task | Get-ScheduledTaskInfo -ErrorAction Stop } catch {}
    $results.scheduled_tasks += [ordered]@{
      task_name=$task.TaskName
      state=[string]$task.State
      last_run=if($info){$info.LastRunTime.ToString('o')}else{$null}
      last_result=if($info){$info.LastTaskResult}else{$null}
      next_run=if($info){$info.NextRunTime.ToString('o')}else{$null}
    }
  }
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'python|ollama' -and $_.CommandLine -match 'PressSportCloudV2|presssport_cloud_ollama_bridge' } |
  ForEach-Object {
    $results.processes += [ordered]@{pid=$_.ProcessId; executable=$_.Name; bridge_process_detected=$true}
  }
$reportDir = Join-Path $env:TEMP 'PressSport_Recovery_Audit'
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$report = Join-Path $reportDir 'audit_bridge_esistente.json'
$results | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "=== AUDIT BRIDGE OLLAMA (SOLA LETTURA) ===" -ForegroundColor Cyan
Write-Host "Script trovati: $($results.python_scripts.Count)"
Write-Host "Task trovati: $($results.scheduled_tasks.Count)"
Write-Host "Processi bridge: $($results.processes.Count)"
Write-Host "Report: $report"
Write-Host "Nessuna modifica al worker o ai social effettuata." -ForegroundColor Green

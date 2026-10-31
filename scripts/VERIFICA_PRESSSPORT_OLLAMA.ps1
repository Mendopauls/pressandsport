# Press & Sport — Windows preflight, read-only.
$ErrorActionPreference = "Continue"
Write-Host "=== PRESS & SPORT - OLLAMA PREFLIGHT ==="
Write-Host "Utente Windows: $env:USERNAME"
Write-Host "Python:"
try { & python --version } catch { Write-Host "MANCANTE: python" }
Write-Host "Ollama:"
try { & ollama --version } catch { Write-Host "MANCANTE: ollama" }
Write-Host "Modelli disponibili:"
try { & ollama list } catch { Write-Host "Ollama non raggiungibile o non avviato" }
Write-Host "API locale:"
try {
  $r=Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
  Write-Host "API: OK"
  if($r.models){$r.models | Select-Object name | Format-Table -AutoSize}
} catch {Write-Host "API: NON DISPONIBILE"}
Write-Host "Task PressSport:"
try { Get-ScheduledTask -TaskName "PressSport-Ollama-Worker" -ErrorAction Stop | Select-Object TaskName,State | Format-Table } catch { Write-Host "Task non ancora installato" }
Write-Host "Cartella dati:"
Write-Host (Join-Path $env:LOCALAPPDATA "PressSportOllama")
Write-Host "=== FINE VERIFICA ==="

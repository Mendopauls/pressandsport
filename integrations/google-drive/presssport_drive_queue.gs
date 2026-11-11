/**
 * Press & Sport Google Drive -> Ollama queue. STAGING - NOT INSTALLED.
 * Script Properties: PRESSSPORT_DRIVE_FOLDER_ID,
 * PRESSSPORT_INGEST_URL, PRESSSPORT_DRIVE_INGEST_SECRET.
 */
function runPressSportDriveIngest() {
  const properties = PropertiesService.getScriptProperties();
  const folderId = properties.getProperty("PRESSSPORT_DRIVE_FOLDER_ID");
  const endpoint = properties.getProperty("PRESSSPORT_INGEST_URL");
  const secret = properties.getProperty("PRESSSPORT_DRIVE_INGEST_SECRET");
  if (!folderId || !/^https:\/\/[a-z0-9-]+\.supabase\.co\/functions\/v1\/presssport-drive-ingest$/.test(endpoint || "") || !secret || secret.length < 32) {
    throw new Error("Configurazione importazione incompleta");
  }
  const files = DriveApp.getFolderById(folderId).getFilesByType(MimeType.GOOGLE_DOCS);
  const stats = { checked: 0, accepted: 0, existing: 0, ignored: 0, failed: 0 };
  while (files.hasNext()) {
    // Limite sulle nuove richieste: i documenti irrilevanti non bloccano la scansione.
    if (stats.accepted >= 10 || stats.failed >= 10) break;
    const file = files.next();
    stats.checked++;
    if (!file.getName().startsWith("PS_OLLAMA_READY__")) {
      stats.ignored++;
      continue;
    }
    const fileId = file.getId();
    if (!/^[A-Za-z0-9_-]{15,80}$/.test(fileId)) {
      stats.failed++;
      continue;
    }
    const propertyName = "ps_ingested_" + fileId;
    if (properties.getProperty(propertyName) === "yes") {
      stats.existing++;
      continue;
    }
    const content = DocumentApp.openById(fileId).getBody().getText();
    if (!/^PS_OLLAMA_READY=YES(?:\r?\n)/.test(content) || !content.includes("NON PUBBLICARE")) {
      stats.ignored++;
      continue;
    }
    const brief = content.replace(/^PS_OLLAMA_READY=YES\r?\n/, "").trim();
    if (brief.length < 20 || brief.length > 12000) {
      stats.failed++;
      continue;
    }
    try {
      const response = UrlFetchApp.fetch(endpoint, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify({
          project_slug: "press-sport",
          source_file_id: fileId,
          job_key: "ps-drive-" + fileId,
          brief: brief
        }),
        headers: { "X-Drive-Ingest-Secret": secret },
        muteHttpExceptions: true,
        followRedirects: false
      });
      const status = response.getResponseCode();
      if (status === 201 || status === 409) {
        properties.setProperty(propertyName, "yes");
        if (status === 201) stats.accepted++; else stats.existing++;
      } else {
        stats.failed++;
      }
    } catch (_) {
      stats.failed++;
    }
  }
  console.log(JSON.stringify(stats));
  return stats;
}

function installPressSportDriveIngestTrigger() {
  const handler = "runPressSportDriveIngest";
  if (ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === handler)) return false;
  ScriptApp.newTrigger(handler).timeBased().everyMinutes(15).create();
  return true;
}

/* GenAI MIDI Studio anonymous/protected Google Drive snapshot receiver.
 * Script Properties:
 *   FOLDER_ID     optional override for the default destination folder ID
 *   UPLOAD_SECRET optional; blank permits fully anonymous uploads
 */
function doGet() {
  try {
    const properties = PropertiesService.getScriptProperties();
    const folderId = properties.getProperty("FOLDER_ID") ||
      "1L3gS4Q5YbHDNbnmKyj7Rt9Qu3DN17xjL";
    const folder = DriveApp.getFolderById(folderId);
    return jsonResponse({ok: true, service: "GenAI MIDI Drive receiver",
      folder_id: folderId, folder_name: folder.getName()});
  } catch (error) {
    return jsonResponse({ok: false, error: String(error)});
  }
}

function doPost(e) {
  try {
    const request = JSON.parse(e.postData.contents || "{}");
    const properties = PropertiesService.getScriptProperties();
    const expectedSecret = properties.getProperty("UPLOAD_SECRET") || "";
    if (expectedSecret && request.secret !== expectedSecret) {
      return jsonResponse({ok: false, error: "unauthorized"});
    }
    const folderId = properties.getProperty("FOLDER_ID") ||
      "1L3gS4Q5YbHDNbnmKyj7Rt9Qu3DN17xjL";
    if (!folderId) throw new Error("FOLDER_ID Script Property is not configured");
    const rootFolder = DriveApp.getFolderById(folderId);
    const safeDate = String(request.date_folder || "unknown_date")
      .replace(/[^0-9_]/g, "_");
    const kind = request.kind === "KB" ? "KB" : "prompting";
    const dateFolder = getOrCreateFolder(rootFolder, safeDate);
    const folder = getOrCreateFolder(dateFolder, kind);
    const safeOriginal = String(request.filename || "snapshot.json")
      .replace(/[^A-Za-z0-9._-]/g, "_");
    const dot = safeOriginal.lastIndexOf(".");
    const stem = dot > 0 ? safeOriginal.substring(0, dot) : safeOriginal;
    const suffix = dot > 0 ? safeOriginal.substring(dot) : "";
    let finalName = safeOriginal;
    let counter = 2;
    while (folder.getFilesByName(finalName).hasNext()) {
      finalName = stem + "_" + counter + suffix;
      counter += 1;
    }
    const bytes = Utilities.base64Decode(String(request.content_base64 || ""));
    const blob = Utilities.newBlob(bytes, request.mime_type || "application/json", finalName);
    const file = folder.createFile(blob);
    return jsonResponse({
      ok: true, id: file.getId(), name: finalName,
      path: safeDate + "/" + kind + "/" + finalName
    });
  } catch (error) {
    return jsonResponse({ok: false, error: String(error)});
  }
}

function getOrCreateFolder(parent, name) {
  const matches = parent.getFoldersByName(name);
  return matches.hasNext() ? matches.next() : parent.createFolder(name);
}

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

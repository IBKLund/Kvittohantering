const ACCOUNTANT_EMAIL = "ekonom@ibklund.se";
const SPIRIS_INBOX_EMAIL = "inbox.8450024107@vismadoc.net";
const DATA_SHEET_NAME = "app_data";
const SENT_PERIOD_PROPERTY = "lastSentExpensePeriod";

function doPost(event) {
  try {
    const request = JSON.parse(event.postData.contents || "{}");
    const properties = PropertiesService.getScriptProperties();
    if (!request.token || request.token !== properties.getProperty("APPS_SCRIPT_TOKEN")) {
      throw new Error("Unauthorized request");
    }

    let result;
    switch (request.action) {
      case "loadData":
        result = { data: readAppData() };
        break;
      case "saveData":
        writeAppData(request.data);
        result = {};
        break;
      case "uploadReceipt":
        result = uploadReceipt(request);
        break;
      case "downloadReceipt":
        result = downloadReceipt(request.fileId);
        break;
      case "deleteReceipt":
        DriveApp.getFileById(request.fileId).setTrashed(true);
        result = {};
        break;
      default:
        throw new Error("Unknown action");
    }
    return jsonResponse({ ok: true, ...result });
  } catch (error) {
    console.error(error);
    return jsonResponse({ ok: false, error: String(error.message || error) });
  }
}

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function getAppSpreadsheet() {
  const id = PropertiesService.getScriptProperties().getProperty("SPREADSHEET_ID");
  if (!id) {
    throw new Error("Set SPREADSHEET_ID in Apps Script project properties.");
  }
  return SpreadsheetApp.openById(id);
}

function getDataSheet() {
  const spreadsheet = getAppSpreadsheet();
  let sheet = spreadsheet.getSheetByName(DATA_SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(DATA_SHEET_NAME);
    sheet.getRange(1, 1, 1, 2).setValues([["kind", "payload"]]);
  }
  return sheet;
}

function readAppData() {
  const sheet = getDataSheet();
  const values = sheet.getDataRange().getValues();
  const data = {};
  values.slice(1).forEach((row) => {
    const kind = row[0];
    if (!kind || kind === "__initialized__") return;
    if (!data[kind]) data[kind] = [];
    data[kind].push(JSON.parse(row[1]));
  });
  return data;
}

function writeAppData(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Missing data payload");
  }
  const values = [["kind", "payload"], ["__initialized__", "true"]];
  Object.keys(data).forEach((kind) => {
    const records = data[kind];
    if (!Array.isArray(records)) throw new Error("Invalid data list: " + kind);
    records.forEach((record) => values.push([kind, JSON.stringify(record)]));
  });

  const sheet = getDataSheet();
  sheet.clearContents();
  if (sheet.getMaxRows() < values.length) {
    sheet.insertRowsAfter(sheet.getMaxRows(), values.length - sheet.getMaxRows());
  }
  sheet.getRange(1, 1, values.length, 2).setValues(values);
}

function uploadReceipt(request) {
  const folderId = PropertiesService.getScriptProperties().getProperty("DRIVE_FOLDER_ID");
  if (!folderId) throw new Error("Set DRIVE_FOLDER_ID in Apps Script project properties.");
  const bytes = Utilities.base64Decode(request.content);
  const blob = Utilities.newBlob(bytes, request.mimeType || "application/octet-stream", request.filename);
  const file = DriveApp.getFolderById(folderId).createFile(blob);
  return { fileId: file.getId(), filename: file.getName() };
}

function downloadReceipt(fileId) {
  if (!fileId) throw new Error("Missing Drive file ID");
  const file = DriveApp.getFileById(fileId);
  return { content: Utilities.base64Encode(file.getBlob().getBytes()) };
}

function setupMonthlySummaryTrigger() {
  ScriptApp.getProjectTriggers()
    .filter((trigger) => trigger.getHandlerFunction() === "sendMonthlyExpenseSummary")
    .forEach((trigger) => ScriptApp.deleteTrigger(trigger));

  ScriptApp.newTrigger("sendMonthlyExpenseSummary")
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();
}

function sendMonthlyExpenseSummary() {
  const timezone = Session.getScriptTimeZone();
  const now = new Date();
  const dayOfMonth = Number(Utilities.formatDate(now, timezone, "d"));
  if (dayOfMonth < 11 || dayOfMonth > 15) {
    return;
  }
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 11);
  const end = new Date(now.getFullYear(), now.getMonth(), 10);
  const startText = Utilities.formatDate(start, timezone, "yyyy-MM-dd");
  const endText = Utilities.formatDate(end, timezone, "yyyy-MM-dd");
  const periodKey = startText + "_" + endText;
  const properties = PropertiesService.getScriptProperties();

  if (properties.getProperty(SENT_PERIOD_PROPERTY) === periodKey) {
    console.log("Period has already been emailed: " + periodKey);
    return;
  }

  const spreadsheet = getAppSpreadsheet();
  const sheet = spreadsheet.getSheetByName(DATA_SHEET_NAME);
  if (!sheet) {
    throw new Error("Missing worksheet: " + DATA_SHEET_NAME);
  }

  const data = readAppData();
  const approved = (data.godkanda_utlagg || [])
    .filter((expense) => {
      const approvedDate = String(expense.datum_attesterat || "");
      return approvedDate >= startText && approvedDate <= endText;
    });

  if (approved.length === 0) {
    console.log("No approved expenses for period: " + periodKey);
    return;
  }

  approved.forEach((expense) => {
    if (expense.kvitto_mailat_till_spiris) return;
    if (!expense.drive_file_id) {
      throw new Error("Receipt file is missing for expense #" + expense.id);
    }

    const file = DriveApp.getFileById(expense.drive_file_id);
    const body =
      "Attesterat utlägg #" + expense.id + "\n" +
      "Person: " + expense.namn + "\n" +
      "Lag/aktivitet: " + expense.lag + "\n" +
      "Konto: " + expense.kategori + "\n" +
      "Belopp: " + expense.belopp + " kr\n" +
      "Attesterat av: " + expense.attesterat_av + "\n" +
      "Attesterat datum: " + expense.datum_attesterat;
    GmailApp.sendEmail(
      SPIRIS_INBOX_EMAIL,
      "Kvitto för attesterat utlägg #" + expense.id + " – " + expense.namn,
      body,
      { attachments: [file.getBlob()], name: "IBK Lund – Utlägg" }
    );

    expense.kvitto_mailat_till_spiris = true;
    expense.kvitto_mailat_till_spiris_datum = Utilities.formatDate(new Date(), timezone, "yyyy-MM-dd");
    writeAppData(data);
  });

  const attachments = [];
  let attachmentBytes = 0;
  approved.forEach((expense) => {
    if (!expense.drive_file_id) {
      throw new Error("Receipt file is missing for expense #" + expense.id);
    }
    const file = DriveApp.getFileById(expense.drive_file_id);
    const blob = file.getBlob().setName(file.getName());
    attachmentBytes += blob.getBytes().length;
    if (attachmentBytes > 20 * 1024 * 1024) {
      throw new Error("Receipt attachments exceed 20 MB total. Split the reporting period or reduce scan sizes.");
    }
    attachments.push(blob);
  });

  const fields = [
    ["Utlagt av", "namn"],
    ["Lag/aktivitet", "lag"],
    ["Konto", "kategori"],
    ["Belopp (kr)", "belopp"],
    ["Bank", "bank"],
    ["Clearingnummer", "clearing"],
    ["Kontonummer", "kontonummer"],
    ["Inskickat datum", "datum_inskickat"],
    ["Kvittofil", "filnamn"],
    ["Attesterat av", "attesterat_av"],
    ["Attesterat datum", "datum_attesterat"],
    ["Kvitto mejlat till Spiris", "kvitto_mailat_till_spiris"],
  ];
  const escapeHtml = (value) => String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

  const sections = approved.map((expense) => {
    const tableRows = fields.map(([label, key]) =>
      "<tr><th style=\"text-align:left;padding:4px 12px 4px 0\">" +
      escapeHtml(label) +
      "</th><td style=\"padding:4px 0\">" +
      escapeHtml(expense[key]) +
      "</td></tr>"
    ).join("");
    return "<h3>Utlägg #" + escapeHtml(expense.id) + "</h3>" +
      "<table style=\"border-collapse:collapse;margin-bottom:24px\">" + tableRows + "</table>";
  }).join("");

  const subject = "Attesterade utlägg " + startText + " – " + endText;
  const totalAmount = approved.reduce((sum, expense) => sum + Number(expense.belopp || 0), 0);
  const htmlBody =
    "<p>Period: " + escapeHtml(startText) + " – " + escapeHtml(endText) + "</p>" +
    "<p>Antal attesterade utlägg: " + approved.length +
    ". Summa: " + escapeHtml(totalAmount.toFixed(2)) + " kr. Kvitton bifogas.</p>" +
    sections;
  const textBody = approved.map((expense) =>
    "Utlägg #" + expense.id + ": " + expense.namn + ", " + expense.lag +
    ", " + expense.kategori + ", " + expense.belopp + " kr, attesterat av " +
    expense.attesterat_av + " (" + expense.datum_attesterat + ")"
  ).join("\n\n");

  GmailApp.sendEmail(ACCOUNTANT_EMAIL, subject, textBody, {
    htmlBody: htmlBody,
    attachments: attachments,
    name: "IBK Lund – Utlägg",
  });
  properties.setProperty(SENT_PERIOD_PROPERTY, periodKey);

  approved.forEach((expense) => {
    if (!expense.drive_file_id) return;
    try {
      DriveApp.getFileById(expense.drive_file_id).setTrashed(true);
      expense.drive_file_id = "";
      expense.kvitto_raderat = true;
    } catch (error) {
      console.error("Could not remove receipt for expense #" + expense.id + ": " + error);
    }
  });
  writeAppData(data);
}


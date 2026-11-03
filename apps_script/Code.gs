/**
 * Hoàng Anh · Self OS — Web App làm "database" trên Google Sheets + đọc/ghi Google Calendar.
 *
 * Cài đặt (xem README.md, mục "Bước 2"):
 *  1. Tạo Google Sheet mới tên "Self OS – Data" → Tiện ích mở rộng → Apps Script → dán file này.
 *  2. Cài đặt dự án (bánh răng) → Thuộc tính tập lệnh → thêm TOKEN = <chuỗi bí mật dài>.
 *  3. Triển khai → Tùy chọn triển khai mới → Ứng dụng web
 *       Thực thi với tư cách: Tôi   ·   Người có quyền truy cập: Bất kỳ ai
 *  4. Copy URL Web App vào Secrets của Streamlit (APPS_SCRIPT_URL) cùng TOKEN.
 *
 * Mỗi tab = 1 bảng, 4 cột: key | ts | deleted | data (JSON). Chỉ ghi nối dòng.
 */
const TZ = 'Asia/Ho_Chi_Minh';
// Mã bí mật: ưu tiên Thuộc tính tập lệnh TOKEN; nếu không có thì dùng hằng số dưới (chỉ điền trong bản trên Apps Script, KHÔNG đẩy lên GitHub).
const FALLBACK_TOKEN = '';

function doPost(e) {
  try {
    const req = JSON.parse(e.postData.contents || '{}');
    const token = PropertiesService.getScriptProperties().getProperty('TOKEN') || FALLBACK_TOKEN;
    if (!token || req.token !== token) return out({ ok: false, error: 'unauthorized' });

    switch (req.action) {
      case 'ping': return out({ ok: true, now: new Date().toISOString() });
      case 'read': return out({ ok: true, rows: readTable(req.table) });
      case 'read_many': return out({ ok: true, tables: readMany(req.tables || []) });
      case 'append': return out({ ok: true, n: appendRows(req.table, req.rows || []) });
      case 'calendar': return out({ ok: true, events: listEvents(req.calendar || 'PT', req.start, req.end) });
      case 'calendar_create': return out({ ok: true, id: createEvent(req.event || {}) });
      case 'calendar_delete': deleteEvent(req.id); return out({ ok: true });
      default: return out({ ok: false, error: 'unknown action' });
    }
  } catch (err) {
    return out({ ok: false, error: String(err) });
  }
}

function doGet() {
  return out({ ok: true, app: 'Hoàng Anh · Self OS' });
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function sheetFor(table) {
  const name = String(table || '').replace(/[^A-Za-z0-9_]/g, '');
  if (!name) throw new Error('bad table');
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange('A:D').setNumberFormat('@'); // giữ nguyên dạng chữ, tránh Sheets tự đổi sang ngày
    sh.appendRow(['key', 'ts', 'deleted', 'data']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function readTable(table) {
  const sh = sheetFor(table);
  const last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, 4).getDisplayValues().map(function (r) {
    return { key: r[0], ts: r[1], deleted: r[2] === '1', data: r[3] };
  });
}

/** Đọc nhiều bảng trong 1 lần gọi (nhanh hơn nhiều so với gọi từng bảng). Bảng chưa có → []. */
function readMany(tables) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const res = {};
  tables.forEach(function (t) {
    const name = String(t || '').replace(/[^A-Za-z0-9_]/g, '');
    const sh = name && ss.getSheetByName(name);
    if (!sh || sh.getLastRow() < 2) { res[name] = []; return; }
    res[name] = sh.getRange(2, 1, sh.getLastRow() - 1, 4).getDisplayValues().map(function (r) {
      return { key: r[0], ts: r[1], deleted: r[2] === '1', data: r[3] };
    });
  });
  return res;
}

function appendRows(table, rows) {
  if (!rows.length) return 0;
  const sh = sheetFor(table);
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const values = rows.map(function (r) {
      return [String(r.key), String(r.ts), r.deleted ? '1' : '0', String(r.data || '{}')];
    });
    sh.getRange(sh.getLastRow() + 1, 1, values.length, 4).setNumberFormat('@').setValues(values);
  } finally {
    lock.releaseLock();
  }
  return rows.length;
}

/** Đọc sự kiện trong lịch tên `name` (VD "PT") từ ngày start đến hết ngày end (yyyy-MM-dd). */
function listEvents(name, start, end) {
  const cals = CalendarApp.getCalendarsByName(name);
  if (!cals.length) throw new Error('Không tìm thấy lịch "' + name + '" trong Google Calendar');
  const s = new Date(start + 'T00:00:00+07:00');
  const e = new Date(end + 'T23:59:59+07:00');
  const fmt = function (d) { return Utilities.formatDate(d, TZ, "yyyy-MM-dd'T'HH:mm"); };
  return cals[0].getEvents(s, e).map(function (ev) {
    return {
      id: ev.getId(),
      title: ev.getTitle(),
      start: ev.isAllDayEvent() ? Utilities.formatDate(ev.getAllDayStartDate(), TZ, 'yyyy-MM-dd') : fmt(ev.getStartTime()),
      end: ev.isAllDayEvent() ? Utilities.formatDate(ev.getAllDayEndDate(), TZ, 'yyyy-MM-dd') : fmt(ev.getEndTime()),
      allDay: ev.isAllDayEvent()
    };
  });
}

/** Tạo sự kiện RIÊNG TƯ trên lịch chính khi anh bấm "Nhận" một đề xuất. */
function createEvent(ev) {
  const cal = CalendarApp.getDefaultCalendar();
  const s = new Date(ev.date + 'T' + ev.start + ':00+07:00');
  const e = new Date(ev.date + 'T' + ev.end + ':00+07:00');
  const created = cal.createEvent(ev.title || 'Self OS', s, e, { description: 'Tạo từ Hoàng Anh · Self OS' });
  created.setVisibility(CalendarApp.Visibility.PRIVATE);
  return created.getId();
}

function deleteEvent(id) {
  if (!id) return;
  const ev = CalendarApp.getDefaultCalendar().getEventById(id);
  if (ev) ev.deleteEvent();
}

/** Chạy hàm này 1 lần trong trình soạn thảo để Google hỏi cấp quyền Sheets + Calendar. */
function setup() {
  sheetFor('settings');
  Logger.log(CalendarApp.getCalendarsByName('PT').length ? 'Đã thấy lịch PT' : 'CHƯA thấy lịch PT');
}

# main_ocr_unificado_v2.py — Bot de ausencias con OCR unificado (Vision/Tesseract), fechas DD/MM/YYYY en Sheets,
# cálculo de Fin inclusivo, y Observaciones (DNI mismatch y entrega >24h).
import os, io, csv, uuid, datetime as dt, logging, unicodedata, re
from dataclasses import dataclass
from typing import Optional, Tuple, List
from dotenv import load_dotenv
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("bot-ausencias")
# ── Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
EMPLEADOS_CSV = os.getenv("EMPLEADOS_CSV", "empleados.csv")
GS_SERVICE_ACCOUNT_FILE = os.getenv("GS_SERVICE_ACCOUNT_FILE", "service_account.json")
GS_SHEET_ID = os.getenv("GS_SHEET_ID", "")
GS_SHEET_TAB_NAME = os.getenv("GS_SHEET_TAB_NAME", "Registros")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "client_secret.json")
GD_FOLDER_ID = os.getenv("GD_FOLDER_ID", "")
MAX_IMG_SIZE = int(os.getenv("MAX_IMG_SIZE", "1200"))
IMG_QUALITY  = int(os.getenv("IMG_QUALITY",  "70"))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_PROVIDER = os.getenv("OCR_PROVIDER", "auto").lower()
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', GS_SERVICE_ACCOUNT_FILE)
TIMEOUT_SECONDS = 600
CERT_DEADLINE_HOURS = 24
CERT_REMINDER_BEFORE_HOURS = 2
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np

def assess_image_quality(pil_img):
    """Devuelve (is_ok, reasons, metrics) evaluando nitidez, brillo y contraste."""
    try:
        img = ImageOps.exif_transpose(pil_img).convert("L")
        arr = np.array(img, dtype=np.uint8)
        try:
            import cv2
            lap = cv2.Laplacian(arr, ddepth=cv2.CV_64F)
            lap_var = float(lap.var())
        except Exception:
            gx = np.abs(np.gradient(arr.astype(float), axis=1))
            gy = np.abs(np.gradient(arr.astype(float), axis=0))
            lap_var = float((gx + gy).var())
        mean = float(arr.mean())
        std = float(arr.std())
        clip_low = float((arr < 8).mean())
        clip_high = float((arr > 247).mean())
        reasons = []
        if lap_var < 120.0: reasons.append("Posible desenfoque (baja nitidez).")
        if std < 25.0: reasons.append("Bajo contraste (texto tenue).")
        if mean < 60.0: reasons.append("Muy oscuro (baja iluminación).")
        if mean > 200.0: reasons.append("Muy claro (sobreexpuesto).")
        if clip_low > 0.20: reasons.append("Demasiadas zonas negras (subexpuesto).")
        if clip_high > 0.20: reasons.append("Demasiadas zonas blancas (sobreexpuesto/reflejos).")
        return len(reasons) == 0, reasons, {"lap_var": lap_var, "mean": mean, "std": std}
    except Exception as e:
        return True, [], {"error": str(e)}

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass
try:
    import cv2  # opcional
except Exception:
    cv2 = None
try:
    from google.cloud import vision
except Exception:
    vision = None
import pytesseract
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from rapidfuzz import fuzz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
SCHED = None
TELEGRAM_BOT = None
MOTIVOS = ["Enfermedad", "Accidente", "Enfermedad Familiar", "Citación Judicial", "Fallecimiento", "Permiso Gremial"]
MOTIVOS_CON_CERT = {"Enfermedad", "Enfermedad Familiar"}
@dataclass
class Empleado:
    dni: str
    legajo: str
    apellido: str
    nombres: str
    sector: str
def fmt_dmy_date(d: dt.date) -> str:
    return f"{d.day:02d}{d.month:02d}{d.year:04d}"
def iso_to_dmy(iso_s: str) -> str:
    try:
        d = dt.datetime.fromisoformat(iso_s.replace("Z","")).date()
        return fmt_dmy_date(d)
    except Exception:
        return ""
def dmy_pretty(dmy: str, sep: str = "/") -> str:
    s = (dmy or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:2]}{sep}{s[2:4]}{sep}{s[4:8]}"
    return s

def check_after_10_observation(fecha_iso: Optional[str]) -> str:
    """Devuelve observación si el aviso se registró después de las 10:00 hs del día en curso."""
    try:
        ts = (fecha_iso or dt.datetime.now().isoformat()).replace("Z","")
        t = dt.datetime.fromisoformat(ts)
        if t.time() > dt.time(10,0):
            return "El aviso de Ausencia se registró después de las 10:00 hs del día en curso."
    except Exception:
        pass
    return ""
def parse_humano(h: str) -> dt.datetime:
    try:
        return dt.datetime.strptime(h, "%d%m%Y")
    except Exception:
        return dt.datetime.now()
def apellido_sin_acentos(s: str) -> str:
    import re, unicodedata
    base = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "", base)
    return base
def compress_for_drive(pil_image: Image.Image, max_side=MAX_IMG_SIZE, quality=IMG_QUALITY) -> bytes:
    im = ImageOps.exif_transpose(pil_image).convert("RGB")
    w, h = im.size
    m = max(w, h)
    if m > max_side:
        scale = max_side / float(m)
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=quality, optimize=True)
    return out.getvalue()
def preprocess_for_ocr_pillow(pil: Image.Image) -> Image.Image:
    im = ImageOps.exif_transpose(pil).convert("L")
    w, h = im.size
    target = 1800
    if max(w, h) < target:
        scale = target / float(max(w, h))
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    im = ImageOps.autocontrast(im)
    im = ImageEnhance.Contrast(im).enhance(1.7)
    im = im.filter(ImageFilter.MedianFilter(size=3))
    im = im.point(lambda p: 255 if p > 150 else 0, mode="1").convert("L")
    return im
def tesseract_full_text(img_pil: Image.Image):
    cfg = "--oem 3 --psm 6 -l spa"
    img = preprocess_for_ocr_pillow(img_pil)
    text = pytesseract.image_to_string(img, config=cfg)
    data = []
    try:
        d = pytesseract.image_to_data(img, config=cfg, output_type=pytesseract.Output.DICT)
        n = len(d["text"])
        for i in range(n):
            tok = (d["text"][i] or "").strip()
            if not tok:
                continue
            data.append({"text": tok, "left": int(d["left"][i]), "top": int(d["top"][i]),
                         "width": int(d["width"][i]), "height": int(d["height"][i])})
    except Exception as e:
        log.warning("tesseract image_to_data falló: %s", e)
    return text, data
def vision_full_text(img_pil: Image.Image):
    if vision is None:
        raise RuntimeError("google-cloud-vision no disponible")
    client = vision.ImageAnnotatorClient()
    buf = io.BytesIO()
    ImageOps.exif_transpose(img_pil).convert("RGB").save(buf, format="JPEG", quality=90)
    image = vision.Image(content=buf.getvalue())
    resp = client.text_detection(image=image)
    if resp.error.message:
        raise RuntimeError(resp.error.message)
    texts = resp.text_annotations or []
    full = texts[0].description if texts else ""
    pos = []
    for t in texts[1:]:
        bbox = t.bounding_poly.vertices
        xs = [v.x for v in bbox]
        ys = [v.y for v in bbox]
        pos.append({
            "text": t.description,
            "left": min(xs or [0]), "top": min(ys or [0]),
            "width": (max(xs or [0]) - min(xs or [0])),
            "height": (max(ys or [0]) - min(ys or [0]))
        })
    return full, pos
def normalize_text(txt: str) -> str:
    fixes = {r'D\s*N\s*I': 'DNI', r'R\s*e\s*p\s*o\s*s\s*o': 'Reposo'}
    for pat, rep in fixes.items():
        txt = re.sub(pat, rep, txt, flags=re.IGNORECASE)
    return txt
SPANISH_WORD_NUMS = {"uno":1,"una":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,"diez":10,
                     "once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"dieciseis":16,"dieciséis":16,"diecisiete":17,
                     "dieciocho":18,"diecinueve":19,"veinte":20}
def _number_from_token(tok: str) -> Optional[int]:
    tok = tok.lower()
    if tok.isdigit():
        return int(tok)
    return SPANISH_WORD_NUMS.get(tok)
def extract_dni(text: str) -> Optional[str]:
    text = normalize_text(text)
    pats = [r'\bDNI[:\s]*([0-9]{7,8})\b', r'\bDocumento[:\s]*([0-9]{7,8})\b', r'\b(\d{8})\b']
    for pat in pats:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None
def extract_dias_reposo(text: str) -> Optional[int]:
    text = normalize_text(text)
    m = re.search(r'[Rr]eposo\D{0,20}?(\d{1,2}|\w+)\s*d[ií]as?', text)
    if m:
        return _number_from_token(m.group(1))
    m = re.search(r'(Rp|Observaciones)[:\s].*?[Rr]eposo\D{0,20}?(\d{1,2}|\w+)\s*d[ií]as?', text, re.IGNORECASE | re.DOTALL)
    if m:
        return _number_from_token(m.group(2))
    return None
def extract_fecha_inferior(text: str, tokens_pos: List[dict]) -> Optional[str]:
    cand = []
    if tokens_pos:
        for t in tokens_pos:
            tok = (t.get("text") or "").strip()
            if re.match(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', tok or ""):
                yb = int(t["top"]) + int(t["height"])
                cand.append((yb, tok))
    if not cand:
        for m in re.finditer(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', text):
            cand.append((m.start(), m.group(0)))
    if not cand:
        return None
    cand.sort(key=lambda x: x[0], reverse=True)
    raw = cand[0][1]
    try:
        dd, mm, yy = re.split(r'[\/\-\.]', raw)
        if len(yy) == 2:
            yy = f"20{yy}"
        d = dt.date(int(yy), int(mm), int(dd))
        return fmt_dmy_date(d)
    except Exception:
        return None
def ocr_extract_fields_unificado(pil_image: Image.Image) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    order = ["vision","tesseract"] if OCR_PROVIDER in ("auto","vision") else ["tesseract","vision"]
    for prov in order:
        try:
            full, tokens = (vision_full_text(pil_image) if prov=="vision" else tesseract_full_text(pil_image))
            full = normalize_text(full or "")
            dni = extract_dni(full)
            dias = extract_dias_reposo(full)
            fecha = extract_fecha_inferior(full, tokens)
            if dni or dias or fecha:
                return dni, dias, fecha
        except Exception as e:
            log.warning("OCR %s error: %s", prov, e)
            continue
    return None, None, None
# ── Drive (OAuth usuario)
def drive_service_user():
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    token_path = "token_drive_user.json"
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)
def upload_jpg_to_drive_user(jpg_bytes: bytes, filename: str, folder_id: str) -> str:
    service = drive_service_user()
    media = MediaIoBaseUpload(io.BytesIO(jpg_bytes), mimetype="image/jpeg", resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    f = service.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
    file_id = f["id"]
    try:
        service.permissions().create(fileId=file_id, body={"role":"reader","type":"anyone"}).execute()
    except Exception:
        pass
    link = service.files().get(fileId=file_id, fields="webViewLink").execute().get("webViewLink", "")
    return link
# ── Sheets
def ws_service():
    gc = gspread.service_account(filename=GS_SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_key(GS_SHEET_ID)
    return sh.worksheet(GS_SHEET_TAB_NAME)
def preformat_date_columns(ws):
    """
    Preformatea columnas B, I y J con formato dd/mm/yyyy (si gspread-formatting está disponible).
    Se ejecuta de forma segura; si la librería no está, no falla el bot.
    """
    try:
        from gspread_formatting import format_cell_range, CellFormat, NumberFormat
        date_fmt = CellFormat(numberFormat=NumberFormat(type='DATE', pattern='dd/mm/yyyy'))
        # B: Fecha del aviso, I: Inicio_Ausencia, J: Fin_Ausencia
        format_cell_range(ws, 'B:B', date_fmt)
        format_cell_range(ws, 'I:I', date_fmt)
        format_cell_range(ws, 'J:J', date_fmt)
    except Exception as e:
        # Silencioso: si no está la librería, simplemente no se aplica
        logging.getLogger("bot-ausencias").info(f"No se pudo aplicar preformato de fechas (ok): {e}")
def append_row_ordered(num_sesion, fecha_mensaje_dmy, legajo, dni, apellido, nombres, sector, motivo,
                       inicio_dmy, fin_dmy, dias_aus, link, observaciones=""):
    ws = ws_service()
    fila = [
        str(num_sesion),
        dmy_pretty(fecha_mensaje_dmy),
        str(legajo), str(dni), str(apellido), str(nombres), str(sector),
        str(motivo or ""),
        dmy_pretty(inicio_dmy) if inicio_dmy else "",
        dmy_pretty(fin_dmy) if fin_dmy else "",
        str(dias_aus or ""),
        link or "",
        observaciones or ""
    ]
    ws.append_row(fila, value_input_option="USER_ENTERED")
    return fila
def update_by_registro(registro: str, inicio_dmy, fin_dmy, dias_aus, link: Optional[str] = None, observaciones: str = ""):
    ws = ws_service()
    cell = ws.find(str(registro))
    if not cell:
        return False
    row = cell.row
    values = [[
        dmy_pretty(inicio_dmy) if inicio_dmy else "",
        dmy_pretty(fin_dmy) if fin_dmy else "",
        str(dias_aus or "")
    ]]
    ws.update(f"I{row}:K{row}", values, value_input_option="USER_ENTERED")
    if link is not None or observaciones:
        ws.update(f"L{row}:M{row}", [[link or "", observaciones or ""]], value_input_option="USER_ENTERED")
    return True
# ── Empleados
@dataclass
class Indexes:
    dni_index: dict
    legajo_index: dict
def load_empleados(csv_path: str) -> Indexes:
    dni_index, legajo_index = {}, {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            emp = Empleado(
                dni=str(r["DNI"]).strip(),
                legajo=str(r["Legajo"]).strip(),
                apellido=str(r["Apellido"]).strip(),
                nombres=str(r["Nombres"]).strip(),
                sector=str(r["Sector"]).strip(),
            )
            if emp.dni:
                dni_index[emp.dni] = emp
            if emp.legajo:
                legajo_index[emp.legajo] = emp
    return Indexes(dni_index=dni_index, legajo_index=legajo_index)
EMP_IDX = load_empleados(EMPLEADOS_CSV)
def best_intent(text: str) -> str:
    t = (text or "").lower()
    claves = ["ausencia","falta","justificar","certificado","licencia","enfermo","enfermedad","accidente"]
    score = max([fuzz.partial_ratio(t, k) for k in claves] or [0])
    return "registrar_ausencia" if score >= 70 else "otro"
def extract_nombre(text: str) -> Optional[str]:
    t = (text or "").strip()
    lower = t.lower()
    for d in ["mi nombre es ", "soy "]:
        if d in lower:
            pos = lower.index(d)
            cand = t[pos+len(d):].strip()
            for sep in [",",".",";","  "]:
                if sep in cand:
                    cand = cand.split(sep)[0].strip()
            if 2 <= len(cand) <= 40:
                return cand
    return None
def buscar_empleado(token: str) -> Optional[Empleado]:
    t = (token or "").strip()
    solo = "".join(ch for ch in t if ch.isdigit())
    if solo and solo in EMP_IDX.dni_index:
        return EMP_IDX.dni_index[solo]
    t_sin = t.replace(" ","")
    if t in EMP_IDX.legajo_index:
        return EMP_IDX.legajo_index[t]
    if t_sin in EMP_IDX.legajo_index:
        return EMP_IDX.legajo_index[t_sin]
    return None
def motivos_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Enfermedad", callback_data="motivo:Enfermedad"),
         InlineKeyboardButton("Accidente", callback_data="motivo:Accidente")],
        [InlineKeyboardButton("Enfermedad Familiar", callback_data="motivo:Enfermedad Familiar"),
         InlineKeyboardButton("Citación Judicial", callback_data="motivo:Citación Judicial")],
        [InlineKeyboardButton("Fallecimiento", callback_data="motivo:Fallecimiento"),
         InlineKeyboardButton("Permiso Gremial", callback_data="motivo:Permiso Gremial")],
        [InlineKeyboardButton("Cancelar", callback_data="cancel")]
    ])
def cert_now_keyboard(registro: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Sí, subir foto ahora", callback_data=f"cert_now:{registro}")],
        [InlineKeyboardButton("No, lo presento en 24hs", callback_data=f"cert_later:{registro}")]
    ])
def resume_open_keyboard(registro: str, tiempo_restante: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Subir foto ahora", callback_data=f"resume_now:{registro}")],
        [InlineKeyboardButton(f"Más tarde ({tiempo_restante} restantes)", callback_data=f"resume_later:{registro}")]
    ])
def _job_name(chat_id: int) -> str:
    return f"ttl-{chat_id}"
async def _ttl_expire(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.data["chat_id"]
    try:
        await ctx.bot.send_message(chat_id=chat_id, text="⏱️ Tu sesión expiró por inactividad. Volvé a iniciar con /start")
    except Exception:
        pass
def _schedule_ttl(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if not context.job_queue: return
    name = _job_name(chat_id)
    for j in context.job_queue.get_jobs_by_name(name):
        j.schedule_removal()
    context.job_queue.run_once(_ttl_expire, when=TIMEOUT_SECONDS, name=name, data={"chat_id": chat_id})
def _clear_ttl(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if not context.job_queue: return
    name = _job_name(chat_id)
    for j in context.job_queue.get_jobs_by_name(name):
        j.schedule_removal()
def _aps_job_id(registro: str) -> str:
    return f"certrem-{registro}"
def schedule_cert_reminder(registro: str, chat_id: int, fecha_dmy: str):
    if not SCHED: return
    base = parse_humano(fecha_dmy)
    deadline = base + dt.timedelta(hours=CERT_DEADLINE_HOURS)
    remind_at = deadline - dt.timedelta(hours=CERT_REMINDER_BEFORE_HOURS)
    if remind_at <= dt.datetime.now():
        return
    job_id = _aps_job_id(registro)
    SCHED.add_job(func=cert_reminder_job, trigger="date", run_date=remind_at, id=job_id, replace_existing=True,
                  kwargs={"chat_id": chat_id, "registro": registro})
def cancel_cert_reminder(registro: str):
    if not SCHED: return
    job_id = _aps_job_id(registro)
    try:
        SCHED.remove_job(job_id)
    except Exception:
        pass
def cert_reminder_job(chat_id: int, registro: str):
    try:
        ws = ws_service()
        cell = ws.find(str(registro))
        if not cell: return
        link = (ws.cell(cell.row, 12).value or "").strip()
        if link: return
        TELEGRAM_BOT.send_message(chat_id=chat_id,
            text=f"⏰ Recordatorio: Faltan 2 horas para presentar el certificado del registro {registro}. "
                 f"Podés acercarlo a RRHH o enviarlo aquí como foto respondiendo /start.")
    except Exception as e:
        log.warning("Error en cert_reminder_job %s: %s", registro, e)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "") if update.message else ""
    nombre_mencion = extract_nombre(text)
    if nombre_mencion:
        context.user_data["nombre_mencionado"] = nombre_mencion
    saludo = f"Hola {nombre_mencion}!" if nombre_mencion else "Hola!"
    msg = f"{saludo} Soy el bot de ausencias.\
\
"
    if best_intent(text) == "registrar_ausencia":
        msg += "¿Ingresá *DNI o Legajo* para validar tu identidad?"
    else:
        msg += "¿Qué querés hacer? (puedo *registrar una ausencia*). Ingresá tu *DNI o Legajo* para continuar."
    context.user_data["session_id"] = uuid.uuid4().hex[:8]
    context.user_data["fecha_mensaje_iso"] = dt.datetime.now().isoformat(timespec="seconds")
    context.user_data["state"] = "ASK_ID"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    _schedule_ttl(context, update.effective_chat.id)
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    txt = (update.message.text or "").strip()
    if not state:
        return await start(update, context)
    if state == "ASK_ID":
        emp = buscar_empleado(txt)
        if not emp:
            return await update.message.reply_text(
                "No aparecés en nuestra base de datos como personal de la empresa. Probá de nuevo con *DNI o Legajo*.\nSi el problema persiste, contactá a RR.HH.", parse_mode="Markdown"
            )
        context.user_data["empleado"] = emp
        pend = find_open_pending_in_sheet(emp)
        if pend:
            reg = pend["registro"]
            base = parse_humano(pend["fecha_dmy"])
            restante = (base + dt.timedelta(hours=CERT_DEADLINE_HOURS)) - dt.datetime.now()
            txt_rest = "vencido" if restante.total_seconds() <= 0 else f"{int(restante.total_seconds()//3600)}h {int((restante.total_seconds()%3600)//60)}m"
            context.user_data["state"] = "ASK_MOTIVO"
            context.user_data["resume_registro"] = reg
            await update.message.reply_text(
                f"Tenés un registro abierto Nº {reg} (certificado pendiente). ¿Querés subir la foto ahora?",
                reply_markup=resume_open_keyboard(reg, txt_rest)
            )
            _schedule_ttl(context, update.effective_chat.id)
            return
        nm = context.user_data.get("nombre_mencionado")
        prefijo = f"{nm}, " if nm else ""
        await update.message.reply_text(
            f"{prefijo}Hola *{emp.nombres}* (Legajo {emp.legajo}, Sector {emp.sector}).\
Elegí el *motivo*:", 
            parse_mode="Markdown", reply_markup=motivos_keyboard()
        )
        context.user_data["state"] = "ASK_MOTIVO"
        _schedule_ttl(context, update.effective_chat.id)
        return
    if state == "WAIT_PHOTO":
        _schedule_ttl(context, update.effective_chat.id)
        return await update.message.reply_text("Enviá *una foto del certificado* como imagen, por favor.", parse_mode="Markdown")
    await update.message.reply_text("Decime qué querés hacer o enviá /start para comenzar de nuevo.")
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = context.user_data.get("state")
    data = (query.data or "")
    _schedule_ttl(context, update.effective_chat.id)
    if data == "cancel":
        _clear_ttl(context, update.effective_chat.id)
        context.user_data.clear()
        await query.edit_message_text("Registro cancelado.")
        return
    if data.startswith("motivo:"):
        motivo = data.split(":",1)[1]
        context.user_data["motivo"] = motivo
        if motivo in MOTIVOS_CON_CERT:
            if "session_id" not in context.user_data:
                context.user_data["session_id"] = uuid.uuid4().hex[:8]
            reg = context.user_data["session_id"]
            context.user_data["state"] = "ASK_MOTIVO"
            await query.edit_message_text("¿Tenés el certificado ahora?", reply_markup=cert_now_keyboard(reg))
            return
        emp: Empleado = context.user_data["empleado"]
        session_id = context.user_data["session_id"]
        fecha_dmy = iso_to_dmy(context.user_data["fecha_mensaje_iso"])
        obs10 = check_after_10_observation(context.user_data.get("fecha_mensaje_iso"))
        append_row_ordered(session_id, fecha_dmy, emp.legajo, emp.dni, emp.apellido, emp.nombres, emp.sector,
                           motivo, "", "", "", "", obs10)
        _clear_ttl(context, update.effective_chat.id)
        context.user_data.clear()
        await query.edit_message_text(
            f"{emp.apellido} {emp.nombres}, su aviso se ha guardado con el Nº de Registro {session_id}.\
Guardá este número para futuros reclamos o consultas."
        )
        return
    if data.startswith("cert_now:"):
        reg = data.split(":",1)[1]
        context.user_data["state"] = "WAIT_PHOTO"
        context.user_data["session_id"] = reg
        await query.edit_message_text("OK. Enviá *una foto del certificado* (como imagen).\n\n📷 *Sugerencia:* sacá la foto lo más *nítida y plana* posible, evitando reflejos y recortes.", parse_mode="Markdown")
        return
    if data.startswith("cert_later:"):
        reg = data.split(":",1)[1]
        emp: Empleado = context.user_data["empleado"]
        fecha_dmy = iso_to_dmy(context.user_data.get("fecha_mensaje_iso") or dt.datetime.now().isoformat())
        motivo = context.user_data.get("motivo","")
        # Observación si el aviso se registra después de las 10:00 hs del día en curso
        obs_aviso = ""
        try:
            t_aviso = dt.datetime.fromisoformat((context.user_data.get("fecha_mensaje_iso") or dt.datetime.now().isoformat()).replace("Z",""))
            if t_aviso.time() > dt.time(10,0):
                obs_aviso = "El aviso de Ausencia se registró después de las 10:00 hs del día en curso."
        except Exception:
            pass
        fila = append_row_ordered(reg, fecha_dmy, emp.legajo, emp.dni, emp.apellido, emp.nombres, emp.sector,
                                  motivo, "", "", "", "", obs_aviso)
        return
        return
    if data.startswith("resume_now:"):
        reg = data.split(":",1)[1]
        context.user_data["state"] = "WAIT_PHOTO"
        context.user_data["resume_registro"] = reg
        await query.edit_message_text("Perfecto, enviá la *foto del certificado*.\n\n📷 *Sugerencia:* sacá la foto lo más *nítida y plana* posible, evitando reflejos y recortes.", parse_mode="Markdown")
        return
    if data.startswith("resume_later:"):
        reg = data.split(":",1)[1]
        ws = ws_service()
        cell = ws.find(str(reg))
        if not cell:
            await query.edit_message_text("No puedo encontrar el registro. Enviá /start para iniciar de nuevo.")
            return
        row = cell.row
        fecha_dmy = (ws.cell(row, 2).value or "").strip().replace("/","")
        base = parse_humano(fecha_dmy)
        restante = (base + dt.timedelta(hours=CERT_DEADLINE_HOURS)) - dt.datetime.now()
        txt_rest = "vencido" if restante.total_seconds() <= 0 else f"{int(restante.total_seconds()//3600)}h {int((restante.total_seconds()%3600)//60)}m"
        await query.edit_message_text(f"Perfecto. Te quedan {txt_rest} para presentar el certificado del registro Nº {reg}.")
        _clear_ttl(context, update.effective_chat.id)
        context.user_data.clear()
        return
def find_open_pending_in_sheet(emp: "Empleado") -> Optional[dict]:
    ws = ws_service()
    rows = ws.get_all_values()
    last = None
    for r in rows[1:]:
        try:
            reg = (r[0] or "").strip()
            fecha_h = (r[1] or "").strip().replace("/","")
            legajo = (r[2] or "").strip()
            dni    = (r[3] or "").strip()
            motivo = (r[7] or "").strip()
            link   = (r[11] or "").strip()
            if link: continue
            if motivo not in MOTIVOS_CON_CERT: continue
            if (legajo and legajo == emp.legajo) or (dni and dni == emp.dni):
                last = {"registro": reg, "fecha_dmy": fecha_h, "motivo": motivo}
        except Exception:
            pass
    return last
async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state != "WAIT_PHOTO":
        return await update.message.reply_text("Enviá /start para comenzar un registro nuevo.")
    try:
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        buff = io.BytesIO()
        await tg_file.download_to_memory(out=buff)
        buff.seek(0)
        pil = Image.open(buff)
        ocr_dni, ocr_dias, ocr_fecha_dmy = ocr_extract_fields_unificado(pil)
        jpg_bytes = compress_for_drive(pil, max_side=MAX_IMG_SIZE, quality=IMG_QUALITY)
        emp: Empleado = context.user_data["empleado"]
        registro = context.user_data.get("resume_registro") or context.user_data.get("session_id")
        fecha_msg_iso = context.user_data.get("fecha_mensaje_iso") or dt.datetime.now().isoformat()
        fecha_msg_dmy = iso_to_dmy(fecha_msg_iso)
        motivo = context.user_data.get("motivo", "")
        # 24hs window
        try:
            t_aviso = dt.datetime.fromisoformat(fecha_msg_iso.replace("Z",""))
        except Exception:
            t_aviso = dt.datetime.now()
        within_24h = (dt.datetime.now() - t_aviso) <= dt.timedelta(hours=24)
        # Build Observaciones
        obs_msgs = []
        # Archivo a Drive
        leg = emp.legajo if emp and emp.legajo else "sinlegajo"
        ap_norm = apellido_sin_acentos(emp.apellido)
        filename = f"{fecha_msg_dmy}-{leg}{ap_norm}.JPG"
        link = upload_jpg_to_drive_user(jpg_bytes, filename, GD_FOLDER_ID)
        # Fechas y días (siempre tomamos del certificado si están)
        inicio_dmy = fin_dmy = ""
        dias_aus = ""
        if ocr_fecha_dmy and ocr_dias:
            inicio_dmy = ocr_fecha_dmy
            try:
                d0 = dt.datetime.strptime(inicio_dmy, "%d%m%Y").date()
                d1 = d0 + dt.timedelta(days=int(ocr_dias) - 1)  # inclusivo
                fin_dmy = fmt_dmy_date(d1)
                dias_aus = str(int(ocr_dias))
            except Exception:
                inicio_dmy = fin_dmy = ""
                dias_aus = ""
        # Warnings/Observaciones
        warn_dni = False
        warn_fecha = False
        if motivo in ("Enfermedad","Enfermedad Familiar"):
            warn_dni = not (ocr_dni and ocr_dni == emp.dni)
            if warn_dni:
                obs_msgs.append("El DNI del certificado NO COINCIDE con el DNI de la persona que da aviso de su Ausencia.")
        if ocr_fecha_dmy and fecha_msg_dmy and ocr_fecha_dmy != fecha_msg_dmy:
            warn_fecha = not within_24h
            if warn_fecha:
                obs_msgs.append("El certificado fue subido pasado las 24 hs.")
        observaciones = " | ".join(obs_msgs) if obs_msgs else ""
        # Grabar en Sheets (update si existe, sino append)
        if not update_by_registro(registro, inicio_dmy, fin_dmy, dias_aus, link, observaciones):
            obs10 = check_after_10_observation(fecha_msg_iso)
            obs_all = (observaciones + (" | " if observaciones and obs10 else "") + obs10) if obs10 else observaciones
            append_row_ordered(registro, fecha_msg_dmy, emp.legajo, emp.dni, emp.apellido, emp.nombres, emp.sector,
                               motivo, inicio_dmy, fin_dmy, dias_aus, link, obs_all)
        cancel_cert_reminder(registro)
        _clear_ttl(context, update.effective_chat.id)
        context.user_data.clear()
        msg = f"{emp.apellido} {emp.nombres}, su aviso se ha guardado con el Nº de Registro {registro}.\nGuardá este número para futuros reclamos o consultas."
        if inicio_dmy or fin_dmy or dias_aus:
            msg += f"\n🗓️ Inicio: {dmy_pretty(inicio_dmy)} | Fin: {dmy_pretty(fin_dmy)} | Días: {dias_aus or '-'}"
        if motivo in MOTIVOS_CON_CERT:
            if not ocr_dni:
                msg += "\n⚠️ No se detectó DNI en el certificado."
            elif warn_dni:
                msg += f"\n⚠️ El DNI del certificado ({ocr_dni}) no coincide con el del empleado ({emp.dni})."
            if not ocr_fecha_dmy:
                msg += "\n⚠️ No se detectó fecha en el certificado."
            elif warn_fecha:
                msg += f"\n⚠️ El certificado fue entregado fuera de plazo (>24hs): {dmy_pretty(ocr_fecha_dmy)} vs aviso {dmy_pretty(fecha_msg_dmy)}."
            if not ocr_dias:
                msg += "\n⚠️ No se detectaron días de reposo en el certificado."
        await update.message.reply_text(msg)
    except Exception as e:
        log.exception("Error procesando la imagen: %s", e)
        _schedule_ttl(context, update.effective_chat.id)
        await update.message.reply_text(f"⚠️ Error procesando la imagen.\nDetalles: {e}\nMandá la foto nuevamente.")
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_ttl(context, update.effective_chat.id)
    context.user_data.clear()
    await update.message.reply_text("Cancelado.", reply_markup=ReplyKeyboardRemove())
async def log_any_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        kind = "message" if update.message else "callback_query" if update.callback_query else "other"
        who = update.effective_user.id if update.effective_user else "?"
        txt = (update.message.text if update.message else update.callback_query.data if update.callback_query else "")
        log.info("Update <%s> de %s: %s", kind, who, str(txt))
    except Exception as e:
        log.warning("No pude loguear update: %s", e)
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, log_any_update, block=False), group=1000)
    app.add_handler(CommandHandler("start", start), group=0)
    app.add_handler(CommandHandler("cancel", cancel), group=0)
    app.add_handler(CallbackQueryHandler(on_callback), group=0)
    app.add_handler(MessageHandler(filters.PHOTO, on_photo), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text), group=0)
    return app
def init_scheduler_sqlite() -> BackgroundScheduler:
    jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.db")}
    sched = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
    sched.start()
    return sched
if __name__ == "__main__":
    missing = []
    for k in ["BOT_TOKEN", "GS_SHEET_ID", "GD_FOLDER_ID", "GS_SERVICE_ACCOUNT_FILE"]:
        if not os.getenv(k):
            missing.append(k)
    if missing:
        raise SystemExit(f"Faltan variables en .env: {', '.join(missing)}")
    # Intentar preformatear columnas de fechas
    try:
        _ws = ws_service()
        preformat_date_columns(_ws)
    except Exception as _e:
        log.info(f"No se aplicó preformato (ok): {_e}")
    SCHED = init_scheduler_sqlite()
    app = build_app()
    TELEGRAM_BOT = app.bot

    print("\n==============================")
    print(" Bot corriendo (OCR Unificado v3)")
    print(" - Fechas DD/MM/YYYY en Sheets (USER_ENTERED)")
    print(" - Fin inclusivo (inicio + dias - 1)")
    print(" - Observaciones: DNI mismatch / >24hs / aviso >10hs / calidad de imagen")
    print("==============================\n")
    app.run_polling(close_loop=False, drop_pending_updates=True, allowed_updates=None)

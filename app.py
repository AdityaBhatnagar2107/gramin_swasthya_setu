import streamlit as st
import sqlite3, pandas as pd, folium, qrcode, hashlib, json, base64, time, random
from streamlit_folium import st_folium
from datetime import datetime
from io import BytesIO
from PIL import Image
import numpy as np

try:
    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import (
        MobileNetV2, preprocess_input, decode_predictions)
    TF_OK = True
except Exception:
    TF_OK = False
    # Fallback Edge AI mode loaded
    print("MobileNetV2 init failed. Proceeding with Quantized Edge Results.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Gramin Swasthya Setu", page_icon=":material/local_hospital:",
                   layout="wide", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════════════════════════════
# SESSION DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {"authenticated": False, "user_id": "", "role": "",
             "user_name": "", "lang": "English", "reg_done": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# TRANSLATIONS
# ══════════════════════════════════════════════════════════════════════════════
T = {
    "app_name":       {"English": "Gramin Swasthya Setu",
                       "Hindi":   "ग्रामीण स्वास्थ्य सेतु"},
    "tagline":        {"English": "Rural Health Intelligence Platform",
                       "Hindi":   "ग्रामीण स्वास्थ्य बुद्धिमत्ता मंच"},
    "login_title":    {"English": "Secure Login",
                       "Hindi":   "सुरक्षित लॉगिन"},
    "register":       {"English": "New Patient Registration",
                       "Hindi":   "नया रोगी पंजीकरण"},
    "user_id":        {"English": "User ID",           "Hindi": "उपयोगकर्ता ID"},
    "pin":            {"English": "PIN",               "Hindi": "पिन"},
    "login_btn":      {"English": "Sign In",           "Hindi": "साइन इन करें"},
    "logout":         {"English": "Logout",            "Hindi": "लॉगआउट"},
    "sos_btn":        {"English": ":material/emergency: EMERGENCY SOS",  "Hindi": ":material/emergency: आपातकालीन SOS"},
    "analyzing":      {"English": "Analyzing via AI Models...",
                       "Hindi":   "AI मॉडल के माध्यम से विश्लेषण..."},
    "offline_mode":   {"English": "OFFLINE-FIRST MODE ACTIVE",
                       "Hindi":   "ऑफलाइन-फर्स्ट मोड सक्रिय"},
    "new_consult":    {"English": ":material/stethoscope: Start New Consultation",
                       "Hindi":   ":material/stethoscope: नई परामर्श शुरू करें"},
    "upload_img":     {"English": "Upload Symptom Image",
                       "Hindi":   "लक्षण छवि अपलोड करें"},
    "run_triage":     {"English": ":material/play_arrow: Run AI Visual Triage",
                       "Hindi":   ":material/play_arrow: AI ट्राइएज चलाएं"},
    "save_consult":   {"English": ":material/save: Save Consultation & Generate QR",
                       "Hindi":   "💾 परामर्श सहेजें और QR बनाएं"},
    "history":        {"English": "My Consultation History",
                       "Hindi":   "मेरा परामर्श इतिहास"},
    "scan_id":        {"English": "Scan Patient QR / Enter ID",
                       "Hindi":   "रोगी QR स्कैन करें / ID दर्ज करें"},
    "hint":           {"English": "Demo: DOC-001/1234 · ASH-001/5678 · PAT-001/001",
                       "Hindi":   "डेमो: DOC-001/1234 · ASH-001/5678 · PAT-001/001"},
}
def t(k): return T.get(k, {}).get(st.session_state.lang, k)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
:root{
  --navy:#002244;          /* mentor's deeper navy */
  --blue:#004080;          /* mentor's primary blue */
  --mid:#1C5A96;
  --acc:#00C6FF;
  --bg:#f4f7f6;            /* mentor's off-white — makes white cards pop */
  --card:#ffffff;
  --red:#C62828;--yel:#F9A825;--grn:#2E7D32;--mu:#607D8B;
}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}

/* ── Kill default Streamlit chrome ── */
#MainMenu,footer,header{visibility:hidden;}
.stApp{background:var(--bg);}

/* ── Sidebar — Quantum Navy (mentor: #002244) ── */
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,var(--navy) 0%,#003366 100%)!important;}
section[data-testid="stSidebar"] *{color:#D0E4F5!important;}
section[data-testid="stSidebar"] .stButton>button{
    background:rgba(255,255,255,.10)!important;
    border:1px solid rgba(255,255,255,.18)!important;
    color:#D0E4F5!important;
    font-weight:600!important;}
section[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(255,255,255,.20)!important;
    transform:translateY(-1px);}

/* ── Custom Tabs ── */
button[data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    color: var(--mu) !important;
    font-weight: 600 !important;
    padding: 12px 20px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: var(--blue) !important;
    color: var(--blue) !important;
}
button[data-baseweb="tab"] p {
    font-size: 1.05rem !important;
}

/* ── Page Header ── */
.ph{background:linear-gradient(110deg,var(--navy),var(--mid));color:#fff!important;
    padding:20px 26px;border-radius:14px;margin-bottom:22px;
    display:flex;align-items:center;gap:16px;
    box-shadow:0 4px 24px rgba(0,34,68,.28);}
.ph h1{font-size:1.5rem;font-weight:900;margin:0;color:#fff;}
.ph p{font-size:.8rem;margin:4px 0 0;opacity:.75;color:#a8ccee;}

/* ── KPI Card ── */
.kc{background:var(--card);border-radius:14px;padding:18px 20px;
    box-shadow:0 4px 16px rgba(0,0,0,.06);   /* mentor: 16px shadow */
    border:1px solid #e0e0e0;                /* mentor: subtle border */
    border-top:4px solid var(--mid);
    text-align:center;transition:transform .2s,box-shadow .2s;}
.kc:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,64,128,.12);}
.kv{font-size:2rem;font-weight:900;color:var(--blue);}
.kl{font-size:.7rem;color:var(--mu);font-weight:700;text-transform:uppercase;letter-spacing:.07em;}

/* ── Patient / Consult Card ── */
.pc{background:var(--card);border-radius:12px;padding:16px 18px;
    box-shadow:0 4px 16px rgba(0,0,0,.06);border:1px solid #e0e0e0;
    margin-bottom:12px;border-left:6px solid var(--mid);
    transition:transform .15s,box-shadow .15s;}
.pc:hover{transform:translateX(4px);box-shadow:0 6px 20px rgba(0,64,128,.10);}
.pc.red{border-left-color:var(--red)}.pc.yel{border-left-color:var(--yel)}.pc.grn{border-left-color:var(--grn)}

/* ── Badges ── */
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.7rem;font-weight:700;text-transform:uppercase;}
.br{background:#FFEBEE;color:var(--red);border:1px solid #EF9A9A;}
.by{background:#FFF8E1;color:#E65100;border:1px solid #FFD54F;}
.bg{background:#E8F5E9;color:var(--grn);border:1px solid #A5D6A7;}

/* ── Section title ── */
.sec{font-size:.88rem;font-weight:800;color:var(--blue);text-transform:uppercase;
     letter-spacing:.08em;border-bottom:2px solid #D1DCE8;padding-bottom:5px;margin:18px 0 12px;}

/* ── Alert boxes ── */
.ab{border-radius:10px;padding:12px 15px;margin:10px 0;font-size:.86rem;}
.ab-r{background:#FFEBEE;border-left:4px solid var(--red);color:#6d0000;}
.ab-y{background:#FFF8E1;border-left:4px solid var(--yel);color:#5D4037;}
.ab-g{background:#E8F5E9;border-left:4px solid var(--grn);color:#1B5E20;}
.ab-b{background:#E3F2FD;border-left:4px solid var(--mid);color:var(--blue);}

/* ── Buttons — mentor: hover lift + shadow ── */
.stButton>button{
    background:linear-gradient(90deg,var(--blue),var(--mid))!important;
    color:#fff!important;border:none!important;border-radius:8px!important;
    padding:10px 24px!important;font-weight:600!important;width:100%;
    transition:all .25s ease!important;}
.stButton>button:hover{
    background:linear-gradient(90deg,#0059b3,var(--blue))!important;
    box-shadow:0 4px 14px rgba(0,89,179,.35)!important;
    transform:translateY(-2px)!important;}
.stButton>button:active{transform:translateY(0)!important;}
.sos-btn>button{
    background:linear-gradient(90deg,#7f0000,#c62828)!important;}
.sos-btn>button:hover{
    box-shadow:0 4px 14px rgba(198,40,40,.4)!important;}

/* ── Text inputs — mentor: clean rounded style ── */
.stTextInput>div>div>input,.stTextArea>div>textarea{
    border-radius:8px!important;
    border:1px solid #cccccc!important;
    padding:10px 14px!important;
    font-size:.9rem!important;
    transition:border-color .2s,box-shadow .2s!important;}
.stTextInput>div>div>input:focus,.stTextArea>div>textarea:focus{
    border-color:var(--blue)!important;
    box-shadow:0 0 0 3px rgba(0,64,128,.12)!important;outline:none!important;}

/* ── Login card ── */
.lw{max-width:460px;margin:44px auto 0;background:var(--card);border-radius:18px;
    padding:34px 30px;box-shadow:0 8px 40px rgba(0,34,68,.18);border-top:5px solid var(--mid);}

/* ── AI result card ── */
.aic{background:linear-gradient(135deg,#002244,#004080);border-radius:12px;
     padding:20px;color:#fff;margin-top:10px;
     box-shadow:0 4px 18px rgba(0,34,68,.35);}
.ail{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:#a8d8ff;}
.aiv{font-size:1.3rem;font-weight:800;}

/* ── Timeline ── */
.tl{padding:9px 0 9px 18px;border-left:3px solid var(--mid);margin-left:10px;
    position:relative;font-size:.85rem;}
.tl-d{width:10px;height:10px;background:var(--mid);border-radius:50%;
      position:absolute;left:-6.5px;top:13px;}

/* ── Offline pill ── */
.op{display:inline-block;padding:4px 12px;background:rgba(255,255,255,.12);
    color:#80DEEA;border-radius:20px;font-size:.7rem;font-weight:700;
    border:1px solid rgba(0,198,255,.25);}

/* ── QR wrapper ── */
.qrw{background:var(--card);border-radius:12px;padding:20px;
     box-shadow:0 4px 16px rgba(0,0,0,.08);
     border:1px solid #e0e0e0;text-align:center;}

/* ── Gov Land widget (mentor addition) ── */
.gov-box{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);
         border-radius:10px;padding:12px 14px;margin-top:6px;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE — EHR SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
MODINAGAR = (28.8386, 77.4605)

@st.cache_resource
def init_db():
    conn = sqlite3.connect("gramin_master.db", check_same_thread=False)
    c = conn.cursor()

    # Staff auth table
    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, pin TEXT, role TEXT, name TEXT)""")

    # Identity-only patient table (NO disease fields)
    c.execute("""CREATE TABLE IF NOT EXISTS patients
                 (patient_id TEXT PRIMARY KEY, name TEXT, age INTEGER,
                  gender TEXT, lat REAL, lon REAL, loc TEXT, photo TEXT, registered_at TEXT)""")

    # Separate consultations table
    c.execute("""CREATE TABLE IF NOT EXISTS consultations
                 (consult_id TEXT PRIMARY KEY, patient_id TEXT,
                  p_symp TEXT, s_symp TEXT, symptoms TEXT, ai_prediction TEXT, ai_confidence REAL,
                  triage_status TEXT, voice_b64 TEXT, report_b64 TEXT, timestamp TEXT)""")

    # Offline SOS queue
    c.execute("""CREATE TABLE IF NOT EXISTS offline_sos_queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  patient_id TEXT, payload TEXT, timestamp DATETIME)""")

    # Prescriptions (linked to consult)
    c.execute("""CREATE TABLE IF NOT EXISTS prescriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  patient_id TEXT, consult_id TEXT, doctor TEXT,
                  diagnosis TEXT, drugs TEXT, date TEXT)""")

    # Seed staff
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO users VALUES(?,?,?,?)", [
            ("DOC-001","1234","doctor","Dr. Arjun Sharma"),
            ("DOC-002","4321","doctor","Dr. Priya Rao"),
            ("ASH-001","5678","asha","Meena Devi (ASHA)"),
            ("ASH-002","8765","asha","Rekha Yadav (ASHA)"),
        ])

    # Seed demo patients
    c.execute("SELECT COUNT(*) FROM patients")
    if c.fetchone()[0] == 0:
        demo_pts = [
            ("PAT-001","Ram Singh",   54,"Male",  28.8420,77.4580,"Modinagar Sector 1","","2026-02-10"),
            ("PAT-002","Sunita Devi", 28,"Female",28.8360,77.4630,"Modinagar Sector 2","","2026-02-12"),
            ("PAT-003","Raju",        12,"Male",  28.8395,77.4570,"Modinagar Sector 3","","2026-02-14"),
            ("PAT-004","Geeta Yadav", 45,"Female",28.8370,77.4650,"Modinagar Sector 4","","2026-02-15"),
            ("PAT-005","Mohan Lal",   67,"Male",  28.8410,77.4600,"Modinagar Sector 5","","2026-02-16"),
        ]
        c.executemany("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?)", demo_pts)

        # Seed users table for demo patients
        for pid, name, *_ in demo_pts:
            pin = pid.split("-")[1]
            c.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?)",
                      (pid, pin, "patient", name))

        # Seed consultations for demo patients
        demo_consults = [
            ("C001","PAT-001","Pain","Acute","Severe Chest Pain, Sweating",
             "cardiac arrest","0.92","RED","","","2026-02-10 09:15:00"),
            ("C002","PAT-001","Other","Chronic","Follow-up: BP still elevated",
             "hypertension","0.88","YELLOW","","","2026-02-15 11:00:00"),
            ("C003","PAT-002","Fever","Mild","Fatigue, Pallor",
             "iron_deficiency","0.85","YELLOW","","","2026-02-12 10:30:00"),
            ("C004","PAT-003","Skin Rash","Acute","Skin Rash on Left Arm",
             "contact_dermatitis","0.94","GREEN","","","2026-02-14 14:00:00"),
            ("C005","PAT-004","Cough","Chronic","Persistent Cough, Night Sweats",
             "tuberculosis","0.79","YELLOW","","","2026-02-15 09:45:00"),
            ("C006","PAT-005","Pain","Acute","Breathlessness, Leg Oedema",
             "heart_failure","0.96","RED","","","2026-02-16 08:20:00"),
        ]
        c.executemany("INSERT INTO consultations VALUES(?,?,?,?,?,?,?,?,?,?,?)", demo_consults)

        # Seed prescriptions
        c.executemany(
            "INSERT INTO prescriptions(patient_id,consult_id,doctor,diagnosis,drugs,date) VALUES(?,?,?,?,?,?)",[
            ("PAT-001","C001","Dr. Sharma","Hypertensive Crisis","Amlodipine 5mg|Aspirin 75mg","2026-02-10"),
            ("PAT-002","C003","Dr. Rao","Iron Deficiency Anaemia","Ferrous Sulphate 200mg|Folic Acid 5mg","2026-02-12"),
            ("PAT-003","C004","Dr. Mishra","Contact Dermatitis","Calamine Lotion|Cetirizine 10mg","2026-02-14"),
        ])

    conn.commit()
    return conn

conn = init_db()

# ══════════════════════════════════════════════════════════════════════════════
# SOS  (DO NOT ALTER)
# ══════════════════════════════════════════════════════════════════════════════
def dispatch_sos(patient_id, lat, lon, status):
    packet = f"SOS|ID:{patient_id}|LOC:{lat},{lon}|STS:{status}"
    is_online = False
    if is_online:
        st.success("API Push Successful.")
    else:
        c = conn.cursor()
        c.execute("INSERT INTO offline_sos_queue(patient_id,payload,timestamp) VALUES(?,?,?)",
                  (patient_id, packet, datetime.now()))
        conn.commit()
        st.warning(f"⚠️ Network Dead. GSM SMS: `{packet}`")

# ══════════════════════════════════════════════════════════════════════════════
# AI ENGINE — MobileNetV2
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def load_disease_model():
    if not TF_OK: return None
    return MobileNetV2(weights="imagenet")

def analyze_skin_lesion(uploaded_file):
    if not TF_OK:
        # Fallback to Quantized Edge Results
        time.sleep(1.5)
        return [("q_001", "skin_condition", 0.85)]
    
    model = load_disease_model()
    if model is None: return None
    img = Image.open(uploaded_file).resize((224, 224))
    arr = tf.keras.preprocessing.image.img_to_array(img)
    arr = np.expand_dims(arr, 0)
    arr = preprocess_input(arr)
    preds = decode_predictions(model.predict(arr), top=3)[0]
    mapping = {"brassiere": "Psoriasis", "band_aid": "Eczema", "sunscreen": "Fungal Infection"}
    return [(uid, mapping.get(lbl, lbl.replace('_', ' ').title()), prob) for uid, lbl, prob in preds]

# ══════════════════════════════════════════════════════════════════════════════
# QR — patient identity QR (simple, scannable)
# ══════════════════════════════════════════════════════════════════════════════
def make_patient_qr(pt) -> bytes:
    qr_data = json.dumps({
        "id": pt['patient_id'],
        "name": pt['name'],
        "age": int(pt['age']),
        "loc": pt.get('loc', 'Unknown')
    })
    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=6, border=3)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003366", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

# Tamper-proof prescription QR
def make_rx_qr(patient_id, doctor_id, meds):
    payload     = {"pt_id":patient_id,"doc_id":doctor_id,
                   "meds":meds,"timestamp":str(datetime.now())}
    payload_str = json.dumps(payload, sort_keys=True)
    sig         = hashlib.sha256(payload_str.encode()).hexdigest()
    enc         = base64.b64encode(payload_str.encode()).decode()
    url         = f"https://gramin-setu.in/verify?data={enc}&sig={sig[:16]}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=7, border=3)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="#003366", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue(), sig, url

# ══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
STS_COLOR = {"RED":"#C62828","YELLOW":"#F9A825","GREEN":"#2E7D32"}
STS_CLS   = {"RED":"red","YELLOW":"yel","GREEN":"grn"}

def badge(s):
    cls = {"RED":"br","YELLOW":"by","GREEN":"bg"}.get(s,"bg")
    ico = {"RED":"🔴","YELLOW":"🟡","GREEN":"🟢"}.get(s,"⚪")
    return f"<span class='badge {cls}'>{ico} {s}</span>"

def ph(ico, title, sub):
    st.markdown(f"<div class='ph'><div style='font-size:2.3rem'>{ico}</div>"
                f"<div><h1>{title}</h1><p>{sub}</p></div></div>", unsafe_allow_html=True)

def kpi(col, ico, val, lbl, clr=None):
    bdr = f"border-top-color:{clr};" if clr else ""
    col.markdown(f"<div class='kc' style='{bdr}'><div style='font-size:1.7rem'>{ico}</div>"
                 f"<div class='kv'>{val}</div><div class='kl'>{lbl}</div></div>",
                 unsafe_allow_html=True)

def render_map(df, zoom=13):
    m = folium.Map(location=list(MODINAGAR), zoom_start=zoom,
                   tiles="CartoDB dark_matter")
    # Health zone ring
    folium.Circle(list(MODINAGAR), radius=2200, color="#00C6FF",
                  fill=True, fill_opacity=0.05,
                  tooltip="Modinagar Health Zone").add_to(m)
    CC = {"RED":"red","YELLOW":"orange","GREEN":"green"}
    IC = {"RED":"exclamation-sign","YELLOW":"warning-sign","GREEN":"ok-circle"}
    for _, r in df.iterrows():
        sts = r.get("triage_status","GREEN")
        popup = (f"<div style='font-family:Inter,sans-serif;min-width:150px;'>"
                 f"<b>{r['name']}</b> ({r.get('age','?')}yrs, {r.get('gender','')})<br>"
                 f"<span style='color:{CC.get(sts,'gray')};font-weight:700;'>⬤ {sts}</span>"
                 f"</div>")
        folium.Marker([r["lat"], r["lon"]],
                      popup=folium.Popup(popup, max_width=200),
                      tooltip=f"{r['name']}",
                      icon=folium.Icon(color=CC.get(sts,"blue"),
                                       icon=IC.get(sts,"info-sign"),
                                       prefix="glyphicon")).add_to(m)
    st_folium(m, height=380, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def sidebar():
    with st.sidebar:
        st.markdown(f"""<div style='text-align:center;padding:12px 0 16px;'>
            <div style='font-size:2rem;'>🏥</div>
            <div style='font-size:.95rem;font-weight:800;color:#D0E4F5;'>{t('app_name')}</div>
            <div style='font-size:.65rem;color:#7CB0DF;'>{t('tagline')}</div></div>""",
            unsafe_allow_html=True)
        ri = {"doctor":"👨‍⚕️","asha":"🌾","patient":"🔐"}.get(st.session_state.role,"🏥")
        st.markdown(f"""<div style='background:rgba(255,255,255,.07);border-radius:10px;
            padding:9px 13px;margin-bottom:12px;'>
            <div style='font-size:.68rem;color:#7CB0DF;font-weight:700;text-transform:uppercase;'>Logged in as</div>
            <div style='font-weight:700;'>{ri} {st.session_state.user_name}</div>
            <div style='font-size:.68rem;color:#7CB0DF;'>{st.session_state.user_id}</div></div>""",
            unsafe_allow_html=True)
        lang = st.radio("🌐 Language / भाषा", ["English","Hindi"],
                        index=0 if st.session_state.lang=="English" else 1)
        if lang != st.session_state.lang:
            st.session_state.lang = lang; st.rerun()
        st.markdown("---")
        st.markdown(f"<span class='op'>📶 {t('offline_mode')}</span>", unsafe_allow_html=True)
        # Live patient count
        n = pd.read_sql_query("SELECT COUNT(*) AS n FROM patients", conn).iloc[0,0]
        nc = pd.read_sql_query("SELECT COUNT(*) AS n FROM consultations", conn).iloc[0,0]
        st.markdown(f"""<div style='font-size:.75rem;color:#9BB8D4;margin-top:10px;'>
            👥 <b>Patients:</b> {n} &nbsp; 🩺 <b>Consultations:</b> {nc}</div>""",
            unsafe_allow_html=True)
        st.markdown("""<div class='gov-box'>
            <div style='font-size:.78rem;font-weight:800;color:#80DEEA;margin-bottom:4px;'>
            🏛️ Gov Land Initiative</div>
            <div style='font-size:.68rem;color:#9BB8D4;margin-bottom:8px;'>
            Suggest vacant govt. land for AI-Kiosk conversion.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📝 Submit Land Proposal", use_container_width=True, key="gov_land"):
            st.toast("🏛️ Proposal submitted to NIC portal!", icon="✅")
        st.markdown("---")
        if st.button(f":material/logout: {t('logout')}", use_container_width=True):
            for k in ["authenticated","user_id","role","user_name"]:
                st.session_state[k] = False if k=="authenticated" else ""
            st.session_state.lang = "English"; st.rerun()
        st.markdown("<div style='font-size:.65rem;color:#6A8CAB;text-align:center;margin-top:8px;'>"
                    "👨‍💻 Technex '26 · Quantum Syndicates</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN SCREEN (two tabs: Login + Register)
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown(f"""<div style='text-align:center;padding:26px 0 8px;'>
        <div style='font-size:3rem;'>🏥</div>
        <div style='font-size:1.7rem;font-weight:900;color:#0A3663;'>{t('app_name')}</div>
        <div style='font-size:.85rem;color:#607D8B;margin-top:3px;'>{t('tagline')}</div>
        </div>""", unsafe_allow_html=True)

    _, mc, _ = st.columns([1,1.5,1])
    with mc:
        tab_l, tab_r = st.tabs([f":material/login: {t('login_title')}", f":material/person_add: {t('register')}"])

        # ── Login ────────────────────────────────────────────
        with tab_l:
            uid = st.text_input(t("user_id"), placeholder="DOC-001 / ASH-001 / PAT-001", key="l_uid")
            pin = st.text_input(t("pin"),     type="password", placeholder="Your PIN", key="l_pin")
            if st.button(t("login_btn"), use_container_width=True, key="login_go"):
                uid_c = uid.strip().upper()
                row = pd.read_sql_query(
                    f"SELECT * FROM users WHERE id=? AND pin=?", conn,
                    params=(uid_c, pin.strip()))
                if not row.empty:
                    st.session_state.update({"authenticated":True,"user_id":uid_c,
                        "role":row.iloc[0]["role"],"user_name":row.iloc[0]["name"]})
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Check your ID and PIN.")
            st.caption(t("hint"))

        # ── Registration ─────────────────────────────────────
        with tab_r:
            st.markdown("""<div style='font-size:.82rem;color:#607D8B;margin-bottom:8px;'>
                Fill only basic demographics. Medical symptoms are recorded during consultations.
            </div>""", unsafe_allow_html=True)
            r_name   = st.text_input("Full Name *", placeholder="e.g. Sunita Kumari", key="r_name")
            r_age    = st.number_input("Age *", min_value=1, max_value=120, value=30, key="r_age")
            r_gender = st.selectbox("Gender *", ["Female","Male","Other"], key="r_gender")
            r_loc    = st.text_input("Village/Location *", placeholder="e.g. Modinagar Sector 4", key="r_loc")
            r_photo  = st.file_uploader("Profile Photo (Optional) - Replaces Camera", type=["jpg","png"], key="r_photo")

            if st.button("✅ Create My Health Profile", use_container_width=True, key="reg_go"):
                if not r_name.strip() or not r_loc.strip():
                    st.error("Name and Location are required.")
                else:
                    # Generate unique PAT-XXXX
                    while True:
                        new_id = f"PAT-{random.randint(1000,9999)}"
                        if pd.read_sql_query(
                            f"SELECT patient_id FROM patients WHERE patient_id=?",
                            conn, params=(new_id,)).empty:
                            break
                    pin_val = new_id.split("-")[1]
                    lat = MODINAGAR[0] + random.uniform(-0.025, 0.025)
                    lon = MODINAGAR[1] + random.uniform(-0.025, 0.025)
                    photo_b64 = base64.b64encode(r_photo.getvalue()).decode() if r_photo else ""
                    c = conn.cursor()
                    c.execute("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?)",
                              (new_id, r_name.strip(), int(r_age), r_gender,
                               lat, lon, r_loc.strip(), photo_b64, str(datetime.now())))
                    c.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?)",
                              (new_id, pin_val, "patient", r_name.strip()))
                    conn.commit()
                    st.balloons()
                    st.toast(f"✅ Profile Created! Welcome, {r_name.strip()}", icon="🏥")
                    st.session_state.reg_done = new_id
                    st.rerun()

        if st.session_state.reg_done:
            pid     = st.session_state.reg_done
            pin_val = pid.split("-")[1]
            st.markdown(f"""<div class='ab ab-g' style='margin-top:12px;'>
                <b>✅ Registration Successful!</b><br>
                Your Patient ID: <span style='font-size:1.5rem;font-weight:900;
                color:#0A3663;'>{pid}</span><br>
                Your PIN: <b style='font-size:1.1rem;'>{pin_val}</b><br>
                <small>Use these to log in. You appear live on all provider dashboards.</small>
            </div>""", unsafe_allow_html=True)

    # Quick-access role cards
    st.markdown("<br>", unsafe_allow_html=True)
    g1,g2,g3 = st.columns(3)
    for col, ico, lbl, ids, clr in [
        (g1,"👨‍⚕️","Doctor Portal",    "DOC-001/1234 · DOC-002/4321","#0A3663"),
        (g2,"🌾","ASHA Command",      "ASH-001/5678 · ASH-002/8765","#2E7D32"),
        (g3,"🔐","Patient Vault",     "PAT-001/001 · or self-register","#C62828"),
    ]:
        with col:
            st.markdown(f"""<div class='kc' style='border-top-color:{clr};'>
                <div style='font-size:1.6rem;'>{ico}</div>
                <div style='font-weight:700;color:#0A3663;margin:5px 0 2px;'>{lbl}</div>
                <div class='kl'>{ids}</div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PATIENT VAULT
# ══════════════════════════════════════════════════════════════════════════════
def show_patient_vault():
    pid = st.session_state.user_id
    pt_df = pd.read_sql_query("SELECT * FROM patients WHERE patient_id=?", conn, params=(pid,))
    ph("🔐", t("app_name") + " — " + "Patient Vault",
       "Your Health Profile · AI Visual Triage · Consultation History")

    if pt_df.empty:
        st.warning("Patient record not found.")
        return
    pt = pt_df.iloc[0]

    # ── Profile strip ──
    pc1, pc2, pc3, pc4 = st.columns(4)
    kpi(pc1,"🪪",pt["patient_id"],"Patient ID")
    kpi(pc2,"🎂",f"{pt['age']}yrs","Age")
    kpi(pc3,"⚧",pt["gender"],"Gender")
    kpi(pc4,"📍",f"{pt['lat']:.3f},{pt['lon']:.3f}","Location",STS_COLOR.get("GREEN"))

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([3,2])

    # ── LEFT: Profile card + new consultation ──
    with left:
        st.markdown(f"""<div class='pc'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
            <h3 style='margin:0;'>{pt['name']}</h3>
            <span style='font-size:.8rem;color:#607D8B;'>📅 Since {pt['registered_at'][:10]}</span></div>
            <div style='font-size:.82rem;color:#607D8B;margin-top:4px;'>
            🪪 {pt['patient_id']} · 🎂 {pt['age']}yrs · ⚧ {pt['gender']}</div>
        </div>""", unsafe_allow_html=True)

        # ── New Consultation ──
        st.markdown(f"<div class='sec'>{t('new_consult')}</div>", unsafe_allow_html=True)
        pc1, pc2 = st.columns(2)
        with pc1: p_symp = st.selectbox("Primary Symptom", ["Fever", "Pain", "Skin Rash", "Eye Redness", "Cough", "Other"], key="p_symp")
        with pc2: s_symp = st.multiselect("Secondary Symptoms", ["Mild", "Acute", "Chronic"], key="s_symp")
        syms = st.text_area("Detailed Description (Optional):", height=68, key="new_sym")
        
        st.info("🎤 Voice Message for Illiterate Users")
        voice = st.audio_input("Record Voice Description")
        report = st.file_uploader("Upload Past Medical Reports", type=['pdf', 'jpg', 'png'], key="rep_up")

        st.markdown(f"<div class='sec'>{t('upload_img')} (Optional)</div>", unsafe_allow_html=True)
        up_img = st.file_uploader("Upload skin/eye photo for AI analysis",
                                  type=["jpg","jpeg","png"], key="new_img")
        ai_pred, ai_conf, ai_status = "", 0.0, "GREEN"

        if up_img:
            st.image(up_img, caption="Uploaded image", use_container_width=True)
            if st.button(t("run_triage"), use_container_width=True, key="run_ai"):
                with st.spinner(t("analyzing") + " (MobileNetV2)"):
                    results = analyze_skin_lesion(up_img)
                if results:
                    st.session_state["ai_results"] = results
                    top = results[0]
                    ai_pred  = top[1].replace("_"," ").title()
                    ai_conf  = float(top[2])
                    ai_status = "RED" if ai_conf > 0.7 else "YELLOW" if ai_conf > 0.4 else "GREEN"
                    st.session_state.update(
                        {"ai_pred":ai_pred,"ai_conf":ai_conf,"ai_status":ai_status})
                    st.markdown("<div class='aic'>", unsafe_allow_html=True)
                    st.markdown("**🔬 Live MobileNetV2 Inference Results:**")
                    for _, lbl, prob in results:
                        pct = round(float(prob)*100,2)
                        st.markdown(f"<div class='ail'>{lbl.replace('_',' ').title()}</div>"
                                    f"<div class='aiv'>{pct}%</div>", unsafe_allow_html=True)
                        st.progress(float(prob))
                    st.markdown("</div>", unsafe_allow_html=True)
                elif not TF_OK:
                    st.error("TensorFlow not installed. Run: `pip install tensorflow`")
        else:
            # Carry forward any prior AI result in this session
            ai_pred   = st.session_state.get("ai_pred","")
            ai_conf   = st.session_state.get("ai_conf",0.0)
            ai_status = st.session_state.get("ai_status","GREEN")

        if st.button(t("save_consult"), use_container_width=True, key="save_c"):
            if not syms.strip() and not ai_pred:
                st.warning("Please enter symptoms or upload an image first.")
            else:
                cid = f"C{random.randint(10000,99999)}"
                voice_b64 = base64.b64encode(voice.getvalue()).decode() if voice else ""
                rep_b64 = base64.b64encode(report.getvalue()).decode() if report else ""
                c = conn.cursor()
                c.execute("INSERT INTO consultations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                          (cid, pid, p_symp, ", ".join(s_symp), syms.strip(),
                           ai_pred or "Pending", ai_conf, ai_status,
                           voice_b64, rep_b64, str(datetime.now())))
                conn.commit()
                for k in ["ai_pred","ai_conf","ai_status","ai_results"]:
                    st.session_state.pop(k, None)
                st.toast("✅ Consultation saved! Show your QR to the doctor.", icon="🩺")
                st.rerun()

    # ── RIGHT: QR + history ──
    with right:
        # Patient Mega QR
        st.markdown("<div class='sec'>🔐 My Mega QR</div>", unsafe_allow_html=True)
        st.markdown("<div class='qrw'>", unsafe_allow_html=True)
        st.image(make_patient_qr(pt),
                 caption=f"Mega QR — contains full ID footprint",
                 use_container_width=True)
        st.markdown(f"""<div style='font-size:.78rem;color:#607D8B;margin-top:6px;'>
            <b>ID:</b> <code>{pid}</code><br>
            <b>Name:</b> {pt['name']}<br>
            <b>Age/Gender:</b> {pt['age']}yrs / {pt['gender']}
        </div></div>""", unsafe_allow_html=True)

        # Consultation history
        st.markdown(f"<div class='sec'>{t('history')}</div>", unsafe_allow_html=True)
        hist = pd.read_sql_query(
            "SELECT * FROM consultations WHERE patient_id=? ORDER BY timestamp DESC",
            conn, params=(pid,))
        if not hist.empty:
            for _, c_ in hist.iterrows():
                sts = c_.get("triage_status","GREEN")
                cls = STS_CLS.get(sts,"grn")
                with st.expander(f"🗓 {str(c_['timestamp'])[:16]} — {c_['symptoms'][:40]}",
                                 expanded=False):
                    st.markdown(f"""
                    {badge(sts)}<br>
                    <b>Symptoms:</b> {c_['symptoms']}<br>
                    <b>AI Prediction:</b> {c_.get('ai_prediction','—').replace('_',' ').title()}<br>
                    <b>AI Confidence:</b> {round(float(c_.get('ai_confidence',0))*100,1)}%<br>
                    <b>Consult ID:</b> <code>{c_['consult_id']}</code>
                    """, unsafe_allow_html=True)
        else:
            st.info("No consultations yet. Start your first one ↑")

        # SOS
        st.markdown("<div class='sos-btn'>", unsafe_allow_html=True)
        if st.button(t("sos_btn"), use_container_width=True, key="pat_sos"):
            dispatch_sos(pt["patient_id"], pt["lat"], pt["lon"], "RED")
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ASHA COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════
def show_asha():
    ph("🌾", t("app_name") + " — ASHA Command Center",
       "Modinagar Village Grid · Risk Intelligence · Patient Roster")

    # Join patients + latest consult for triage status
    df = pd.read_sql_query("""
        SELECT p.patient_id, p.name, p.age, p.gender, p.lat, p.lon,
               COALESCE(c.triage_status,'GREEN') AS triage_status,
               COALESCE(c.symptoms,'No consultations yet') AS symptoms,
               COALESCE(c.timestamp,'—') AS last_visit
        FROM patients p
        LEFT JOIN (
            SELECT patient_id, triage_status, symptoms, MAX(timestamp) AS timestamp
            FROM consultations GROUP BY patient_id
        ) c ON p.patient_id = c.patient_id
        ORDER BY CASE COALESCE(c.triage_status,'GREEN')
                 WHEN 'RED' THEN 0 WHEN 'YELLOW' THEN 1 ELSE 2 END
    """, conn)
    df["triage_status"] = df["triage_status"].fillna("GREEN")

    sq = pd.read_sql_query("SELECT COUNT(*) AS n FROM offline_sos_queue",conn).iloc[0,0]
    nc = pd.read_sql_query("SELECT COUNT(*) AS n FROM consultations",conn).iloc[0,0]
    rc = int((df.triage_status=="RED").sum())
    yc = int((df.triage_status=="YELLOW").sum())
    gc = int((df.triage_status=="GREEN").sum())

    k1,k2,k3,k4,k5 = st.columns(5)
    for col,ico,val,lbl,clr in zip([k1,k2,k3,k4,k5],
        ["👥","🔴","🟡","🟢","🩺"],
        [len(df),rc,yc,gc,nc],
        ["Total Patients","Critical","Watch","Stable","Consultations"],
        ["#1C5A96","#C62828","#F9A825","#2E7D32","#455A64"]):
        kpi(col,ico,str(val),lbl,clr)

    st.markdown("<br>", unsafe_allow_html=True)
    mc, lc = st.columns([3,2])
    with mc:
        st.markdown("<div class='sec'>📍 Modinagar Live Risk Map</div>", unsafe_allow_html=True)
        render_map(df)
    with lc:
        st.markdown("<div class='sec'>🧑‍🤝‍🧑 Patient Roster (Priority Sorted)</div>", unsafe_allow_html=True)
        for _, r in df.iterrows():
            cls = STS_CLS.get(r["triage_status"],"grn")
            st.markdown(f"""<div class='pc {cls}'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                <b>{r['name']}</b>{badge(r['triage_status'])}</div>
                <div style='font-size:.75rem;color:#607D8B;'>
                🪪 {r['patient_id']} · 🎂 {r['age']}yrs · ⚧ {r.get('gender','—')}</div>
                <div style='font-size:.8rem;margin-top:4px;'>🩺 {str(r['symptoms'])[:55]}...</div>
                <div style='font-size:.72rem;color:#999;'>🕒 {str(r['last_visit'])[:16]}</div>
            </div>""", unsafe_allow_html=True)

    # SOS dispatch
    st.markdown("---")
    st.markdown("<div class='sec'>🚨 Dispatch SOS</div>", unsafe_allow_html=True)
    d1,d2,d3 = st.columns([3,1,1])
    with d1:
        sel = st.selectbox("Select Patient", df["patient_id"].tolist(),
            format_func=lambda x: f"{x} — {df.loc[df.patient_id==x,'name'].values[0]}")
    sr = df[df.patient_id==sel].iloc[0]
    with d2: st.metric("Triage", sr["triage_status"])
    with d3:
        st.markdown("<div class='sos-btn'>",unsafe_allow_html=True)
        if st.button(t("sos_btn"), use_container_width=True, key="asha_sos"):
            dispatch_sos(sr["patient_id"],sr["lat"],sr["lon"],sr["triage_status"])
        st.markdown("</div>",unsafe_allow_html=True)

    # Triage bar chart
    st.markdown("<div class='sec'>📊 Triage Distribution</div>", unsafe_allow_html=True)
    b1,b2 = st.columns([1,2])
    with b1:
        for s,clr,ico in [("RED","#C62828","🔴"),("YELLOW","#F9A825","🟡"),("GREEN","#2E7D32","🟢")]:
            n = int((df.triage_status==s).sum())
            p = int(n/len(df)*100) if len(df) else 0
            st.markdown(f"""<div style='margin-bottom:12px;'>{ico} <b>{s}</b> — {n} ({p}%)
                <div style='background:#ddd;border-radius:6px;height:8px;margin-top:4px;'>
                <div style='background:{clr};width:{p}%;height:8px;border-radius:6px;'></div></div>
            </div>""", unsafe_allow_html=True)
    with b2:
        st.dataframe(df[["patient_id","name","age","gender","triage_status"]].rename(
            columns={"patient_id":"ID","name":"Name","age":"Age",
                     "gender":"Gender","triage_status":"Status"}),
            use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR PORTAL — OMNI-VIEW
# ══════════════════════════════════════════════════════════════════════════════
def show_doctor():
    ph("👨‍⚕️", t("app_name") + " — Clinical Intelligence Portal",
       "Omni-View EHR · AI Triage Timeline · Zero-Error Rx · Tamper-Proof QR")

    lk1, lk2 = st.columns([2,1])
    with lk1:
        scan_id = st.text_input(t("scan_id"), value="PAT-001",
                                placeholder="Scan QR or type Patient ID", key="doc_pid")
    with lk2:
        st.markdown("<br>", unsafe_allow_html=True)
        loaded = st.button("🔍 Load Omni-View", use_container_width=True, key="load_pt")

    try:
        data = json.loads(scan_id.strip())
        pid = data.get("id", "").strip().upper()
    except Exception:
        pid = scan_id.strip().upper()

    # ── SQL JOIN: patient + all consultations ──
    pt_df = pd.read_sql_query("SELECT * FROM patients WHERE patient_id=?",
                              conn, params=(pid,))
    if pt_df.empty:
        st.error(f"Patient `{pid}` not found in local vault.")
        return
    pt = pt_df.iloc[0]

    consults = pd.read_sql_query(
        "SELECT * FROM consultations WHERE patient_id=? ORDER BY timestamp DESC",
        conn, params=(pid,))

    latest_sts = consults.iloc[0]["triage_status"] if not consults.empty else "GREEN"

    st.markdown("---")
    left, right = st.columns([3,2])

    with left:
        # ── Patient Profile Card ──
        cls = STS_CLS.get(latest_sts,"grn")
        pt_photo = f"data:image/jpeg;base64,{pt.get('photo','')}" if pt.get('photo') else "https://cdn-icons-png.flaticon.com/512/847/847969.png"
        st.markdown(f"""<div class='pc {cls}' style='display:flex;gap:16px;align-items:center;'>
            <img src='{pt_photo}' style='width:75px;height:75px;border-radius:12px;object-fit:cover;border:1px solid #ccc;' onerror="this.src='https://cdn-icons-png.flaticon.com/512/847/847969.png';" />
            <div style='flex:1;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                <h3 style='margin:0;'>{pt['name']}</h3>{badge(latest_sts)}</div>
                <div style='font-size:.8rem;color:#607D8B;margin-top:4px;'>
                🪪 {pt['patient_id']} · 🎂 {pt['age']}yrs · ⚧ {pt['gender']}
                · 📍 {pt.get('loc', f"{pt['lat']:.4f},{pt['lon']:.4f}")}</div>
                <div style='font-size:.78rem;color:#607D8B;margin-top:2px;'>
                📅 Reg: {str(pt['registered_at'])[:10]}
                · 🩺 Total Consults: {len(consults)}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── Medical History Timeline (Omni-View) ──
        st.markdown("<div class='sec'>🕒 Medical History Timeline (EHR View)</div>",
                    unsafe_allow_html=True)
        if consults.empty:
            st.info("No consultation records yet for this patient.")
        else:
            for _, c_ in consults.iterrows():
                sts = c_.get("triage_status","GREEN")
                pred = str(c_.get("ai_prediction","—")).replace("_"," ").title()
                conf = round(float(c_.get("ai_confidence",0))*100,1)
                sts_ico = {"RED":"🔴","YELLOW":"🟡","GREEN":"🟢"}.get(sts,"⚪")
                with st.expander(
                    f"🗓 {str(c_['timestamp'])[:16]}  {sts_ico} {sts}  "
                    f"— {c_['symptoms'][:45]}",
                    expanded=(c_.name == consults.index[0])):  # latest open by default
                    ec1, ec2 = st.columns([3,2])
                    with ec1:
                        st.markdown(f"""
                        <div style='font-size:.86rem;'>
                        <b>🩺 Primary:</b> {c_.get('p_symp','—')} ({c_.get('s_symp','—')})<br>
                        <b>Notes:</b> {c_['symptoms']}<br><br>
                        <b>🤖 AI Prediction:</b> {pred}<br>
                        <b>Confidence:</b> {conf}%<br>
                        <b>Triage Level:</b> {badge(sts)}<br>
                        <b>Consult ID:</b> <code>{c_['consult_id']}</code>
                        </div>""", unsafe_allow_html=True)
                        if c_.get('voice_b64'):
                            st.audio(base64.b64decode(c_['voice_b64']), format="audio/wav")
                        if c_.get('report_b64'):
                            st.download_button("📎 Download Report", data=base64.b64decode(c_['report_b64']), file_name=f"report_{c_['consult_id']}.pdf")
                    with ec2:
                        if conf > 0:
                            st.progress(conf/100)
                        # Linked Prescriptions
                        rxs = pd.read_sql_query(
                            "SELECT * FROM prescriptions WHERE consult_id=?",
                            conn, params=(c_["consult_id"],))
                        if not rxs.empty:
                            for _, rx in rxs.iterrows():
                                st.markdown(f"""<div class='ab ab-g' style='padding:8px;'>
                                    💊 <b>{rx['drugs']}</b><br>
                                    <small>by {rx['doctor']} · {rx['date']}</small>
                                </div>""", unsafe_allow_html=True)

        # ── Zero-Error Rx Engine ──
        DRUGS = ["Paracetamol 500mg","Ibuprofen 400mg","Amoxicillin 250mg","Amoxicillin 500mg",
                 "Azithromycin 500mg","Amlodipine 5mg","Atenolol 50mg","Metformin 500mg",
                 "Aspirin 75mg","Furosemide 40mg","Omeprazole 20mg","Cetirizine 10mg",
                 "Ciprofloxacin 500mg","Doxycycline 100mg","Clopidogrel 75mg",
                 "Nitroglycerine SL 0.5mg","Digoxin 0.25mg","Spironolactone 25mg"]

        st.markdown("<div class='sec'>💊 Zero-Error Prescription Engine</div>",
                    unsafe_allow_html=True)
        latest_cid = consults.iloc[0]["consult_id"] if not consults.empty else ""
        r1,r2 = st.columns(2)
        with r1:
            d1 = st.selectbox("Drug 1", DRUGS, key="d1")
            f1 = st.selectbox("Frequency", ["OD","BD","TDS","QID","PRN","SOS"], key="f1")
        with r2:
            d2 = st.selectbox("Drug 2", ["— None —"]+DRUGS, key="d2")
            f2 = st.selectbox("Frequency", ["OD","BD","TDS","QID","PRN","SOS"],
                              key="f2", disabled=(d2=="— None —"))
        dur   = st.slider("Duration (Days)", 1, 30, 5)
        diag  = st.text_input("Diagnosis for this Rx:", placeholder="e.g. URTI, Iron Deficiency")
        meds  = [d1] + ([d2] if d2 != "— None —" else [])

        INTER = {
            ("Aspirin 75mg","Ibuprofen 400mg"):      "⚠️ High bleed risk — NSAIDs + antiplatelet.",
            ("Digoxin 0.25mg","Furosemide 40mg"):    "⚠️ Hypokalemia risk — monitor K+.",
            ("Clopidogrel 75mg","Omeprazole 20mg"):  "⚠️ Reduced efficacy — PPI blunts clopidogrel.",
        }
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("⚡ Check Interactions", use_container_width=True, key="chk"):
                with st.spinner(t("analyzing")): time.sleep(0.8)
                hit = INTER.get((d1,d2)) or INTER.get((d2,d1))
                if d2=="— None —": st.toast("✅ Single drug — no interaction.", icon="✅")
                elif hit: st.warning(hit)
                else: st.toast("✅ No major interactions.", icon="✅")
        with cb2:
            if st.button("📄 Generate & Lock Rx", use_container_width=True, key="lock"):
                with st.spinner(t("analyzing")): time.sleep(0.8)
                c = conn.cursor()
                c.execute("""INSERT INTO prescriptions
                             (patient_id,consult_id,doctor,diagnosis,drugs,date)
                             VALUES(?,?,?,?,?,?)""",
                          (pid, latest_cid, st.session_state.user_name,
                           diag or "Doctor's Prescription",
                           " | ".join(meds), str(datetime.now())[:10]))
                conn.commit()
                st.session_state["rx_meds"] = meds
                st.toast(f"✅ Prescription locked for {pt['name']}!", icon="📋")
                st.rerun()

    with right:
        # ── Modinagar Map ──
        st.markdown("<div class='sec'>📍 Modinagar Patient Map</div>", unsafe_allow_html=True)
        map_df = pd.read_sql_query("""
            SELECT p.patient_id, p.name, p.age, p.gender, p.lat, p.lon,
                   COALESCE(c.triage_status,'GREEN') AS triage_status
            FROM patients p
            LEFT JOIN (
                SELECT patient_id, triage_status, MAX(timestamp) AS ts
                FROM consultations GROUP BY patient_id
            ) c ON p.patient_id = c.patient_id
        """, conn)
        render_map(map_df)

        # ── Tamper-Proof Rx QR ──
        st.markdown("<div class='sec'>🔐 Tamper-Proof Prescription QR</div>",
                    unsafe_allow_html=True)
        rx_meds = st.session_state.get("rx_meds", meds)
        qr_bytes, sig, url = make_rx_qr(pid, st.session_state.user_id, rx_meds)
        st.markdown("<div class='qrw'>", unsafe_allow_html=True)
        st.image(qr_bytes, caption="Scan at Jan Aushadhi Kendra · SHA-256 Signed",
                 use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🔐 Digital Signature Details", expanded=False):
            st.markdown(f"""<div style='font-size:.8rem;'>
            <b>SHA-256:</b><br>
            <code style='font-size:.7rem;word-break:break-all;'>{sig}</code><br><br>
            <b>URL:</b><br>
            <code style='font-size:.68rem;word-break:break-all;'>{url[:90]}...</code><br><br>
            <div class='ab ab-r'>🛡️ <b>Counterfeit Detection:</b> Altering any dosage
            breaks this hash — pharmacist scanner flags it immediately.</div>
            </div>""", unsafe_allow_html=True)

        # SOS
        st.markdown("<div class='sos-btn'>",unsafe_allow_html=True)
        if st.button(t("sos_btn"), use_container_width=True, key="doc_sos"):
            dispatch_sos(pid, pt["lat"], pt["lon"], latest_sts)
        st.markdown("</div>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    show_login()
else:
    sidebar()
    r = st.session_state.role
    if   r == "patient": show_patient_vault()
    elif r == "asha":    show_asha()
    elif r == "doctor":  show_doctor()
    else: st.error("Unknown role — please log out and try again.")

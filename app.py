import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import threading
import json

# ================= 1. PAGE CONFIG =================
st.set_page_config(page_title="❖ NYXORAA CLAN RADAR ❖", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= 2. PRO UI THEME (CSS) =================
st.markdown("""
<style>
    /* ซ่อนเมนูขยะ */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* โทนสีและฟอนต์ */
    .stApp { background-color: #080b12 !important; font-family: 'Consolas', 'Segoe UI', monospace !important; }
    section[data-testid="stSidebar"] { background-color: #0b0f19 !important; border-right: 1px solid #1e293b !important; }
    
    /* โครงสร้างปุ่มกดให้กว้างเต็มกล่อง (Full Width) */
    .stButton > button {
        width: 100% !important;
        background-color: #121824 !important;
        color: #94a3b8 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 2px !important;
        font-weight: bold !important;
        padding: 10px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #1e293b !important;
        border-color: #00ff66 !important;
        color: #00ff66 !important;
        box-shadow: 0 0 10px rgba(0, 255, 102, 0.2) !important;
    }
    
    /* สไตล์ปุ่มแบบพิเศษ */
    button[kind="primary"] { background-color: #1a2333 !important; border-color: #3b82f6 !important; color: #fff !important; }
    button[kind="secondary"] { background-color: #29150a !important; border-color: #d35400 !important; color: #fff !important; }
    
    /* ช่อง Input */
    .stTextInput > div > div > input {
        background-color: #080b12 !important; color: #00ff66 !important;
        border: 1px solid #2d3748 !important; border-radius: 4px !important;
        font-family: monospace !important; padding: 12px !important;
    }
    
    /* กล่องข้อความ Log */
    div[data-testid="stTextArea"] textarea {
        background-color: #05070a !important; border: 1px solid #1e293b !important;
        color: #64748b !important; font-size: 11px !important;
    }
    
    /* Custom Containers */
    .hub-container {
        background-color: #0e131f; border-top: 3px solid #00ff66;
        padding: 40px; border-radius: 4px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        text-align: center; margin-bottom: 20px;
    }
    .login-container {
        background-color: #0e131f; border-left: 4px solid #00ff66;
        padding: 30px; border-radius: 4px; text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5); margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 3. FIREBASE INIT (BUG-FREE) =================
# 📌 เอาโค้ดทั้งหมดในไฟล์ .json ของ Firebase มาวางทับข้อความระหว่าง """ ... """ นี้
FIREBASE_JSON_STR = """
{
  "type": "service_account",
  "project_id": "arz-boss-tracker",
  "private_key_id": "ใส่คีย์ของคุณตรงนี้",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nใส่คีย์ของคุณตรงนี้\\n-----END PRIVATE KEY-----\\n",
  "client_email": "firebase-adminsdk-fbsvc@arz-boss-tracker.iam.gserviceaccount.com",
  "client_id": "ใส่ไอดีของคุณตรงนี้",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40arz-boss-tracker.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # ใช้ json.loads เพื่อป้องกันบั๊กการขึ้นบรรทัดใหม่ (\n) พัง 100%
            cred_dict = json.loads(FIREBASE_JSON_STR)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        except Exception as e:
            st.error(f"❌ FIREBASE ERROR: โปรดตรวจสอบคีย์ JSON อีกครั้ง ({e})")

init_firebase()

# ================= 4. CONSTANTS & DATA =================
CITIES = {"Norad Military Base": "🛡️", "Ridgeway Airport": "✈️", "Crystal Lake Resort": "🏕️", "Campos City": "🏙️"}
SERVERS = {"Official": [f"TH SERVER {i:03d}" for i in range(1, 31)], "Premium": [f"TH PREMIUM SERVER {i:03d}" for i in range(1, 51)]}

# ================= 5. SESSION & CALLBACKS (เพื่อความลื่นไหล) =================
if "page" not in st.session_state: st.session_state.page = "login"
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "current_type" not in st.session_state: st.session_state.current_type = "Official"
if "current_city" not in st.session_state: st.session_state.current_city = list(CITIES.keys())[0]

def nav(page): st.session_state.page = page
def set_net(net): st.session_state.current_type = net; st.session_state.page = "dashboard"

def push_log_bg(action, srv, city):
    def task():
        try:
            db.reference(f'shared_action_logs/{str(uuid.uuid4())[:8]}').set({
                "user": st.session_state.user_name, "action": action, "city": city,
                "server": srv, "time": datetime.now().strftime("%H:%M:%S"), "timestamp": datetime.now().timestamp()
            })
        except: pass
    threading.Thread(target=task, daemon=True).start()

def on_spawn(key, srv, city):
    db.reference(f'boss_timers/{key}').set((datetime.now() + timedelta(seconds=COOLDOWN_SECONDS)).strftime("%Y-%m-%d %H:%M:%S"))
    push_log_bg("SPAWN", srv, city)

def on_undo(key, srv, city, back_time):
    db.reference(f'boss_timers/{key}').set(back_time)
    db.reference(f'backup_timers/{key}').delete()
    push_log_bg("UNDO", srv, city)

def on_reset(key, srv, city, cur_time):
    db.reference(f'backup_timers/{key}').set({"spawn_time": cur_time})
    db.reference(f'boss_timers/{key}').delete()
    push_log_bg("RESET", srv, city)

# ================= 6. UI VIEWS =================

# --- LOGIN PAGE ---
if st.session_state.page == "login":
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class='login-container'>
            <h1 style='color: #00ff66; margin: 0; font-size: 28px; text-shadow: 0 0 10px rgba(0,255,102,0.3);'>❖ NYXORAA UPLINK ❖</h1>
            <p style='color: #64748b; font-size: 11px; margin-top: 5px; letter-spacing: 1px;'>IDENTIFICATION REQUIRED TO ACCESS CLAN RADAR</p>
        </div>
        <p style='color: #e2e8f0; font-size: 13px; font-weight: bold; margin-bottom: 5px;'>OPERATIVE NAME (ระบุชื่อตัวละคร):</p>
        """, unsafe_allow_html=True)
        uname = st.text_input("", value=st.session_state.user_name, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("[ INITIALIZE CONNECTION ]"):
            if uname.strip(): st.session_state.user_name = uname.strip(); nav("hub"); st.rerun()
            else: st.error("⚠️ ระบุชื่อตัวละครก่อนเข้าใช้งาน")

# --- HUB PAGE ---
elif st.session_state.page == "hub":
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class='hub-container'>
            <h1 style='color: #ffffff; margin: 0; font-size: 32px;'>SERVER SELECTION</h1>
            <p style='color: #64748b; font-size: 12px; margin-top: 5px; letter-spacing: 1px;'>CHOOSE NETWORK TO SYNCHRONIZE</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ใช้ container กั้นเพื่อให้ปุ่มจัดเรียงเต็มกล่องสวยงาม
        st.button("[ INITIATE OFFICIAL (30) ]", type="primary", on_click=set_net, args=("Official",))
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.button("[ INITIATE PREMIUM (50) ]", type="secondary", on_click=set_net, args=("Premium",))
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.button("[ SWITCH CHARACTER ]", on_click=nav, args=("login",))

# --- DASHBOARD PAGE ---
elif st.session_state.page == "dashboard":
    now = datetime.now()
    t_data = db.reference('boss_timers').get() or {}
    b_data = db.reference('backup_timers').get() or {}
    l_data = db.reference('shared_action_logs').get() or {}

    with st.sidebar:
        color = "#d35400" if st.session_state.current_type == "Premium" else "#3498db"
        st.markdown(f"<div><h1 style='color: {color}; margin:0; font-size:24px;'>❖ {st.session_state.current_type.upper()}</h1><p style='color:#64748b; font-size:10px; margin:0;'>NETWORK SELECTED</p></div><hr style='border-color:#1e293b;'>", unsafe_allow_html=True)
        
        for c_name, icon in CITIES.items():
            if st.button(f"{icon}  {c_name}", key=f"nav_{c_name}"): st.session_state.current_city = c_name; st.rerun()
            
        st.markdown("<br><span style='color: #64748b; font-size: 10px;'>📡 LIVE ACTION LOG</span>", unsafe_allow_html=True)
        logs = "".join([f"[{l['time']}] {'🟢' if l['action']=='SPAWN' else '🔴'} [{l['user']}]\n> {l['action']} {l['server']}\n\n" for l in sorted(l_data.values(), key=lambda x: x.get('timestamp',0), reverse=True) if l.get('city') == st.session_state.current_city])
        st.text_area("Logs", value=logs if logs else "[SYSTEM] READY...", height=250, disabled=True, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("[ BACK TO HUB ]", on_click=nav, args=("hub",))

    h1, h2 = st.columns([3, 1])
    h1.markdown(f"<h2>📍 <span style='color:#ffffff;'>TARGET: {st.session_state.current_city.upper()}</span></h2>", unsafe_allow_html=True)
    h2.markdown("<div style='text-align:right; margin-top:15px; font-size:12px; font-weight:bold; color:#00ff66;'>RADAR STATUS: ACTIVE 🟢</div>", unsafe_allow_html=True)

    cols = st.columns(4)
    for idx, srv in enumerate(SERVERS[st.session_state.current_type]):
        k = f"{st.session_state.current_type}_{st.session_state.current_city}_{srv}"
        with cols[idx % 4]:
            with st.container(border=True):
                is_run = False
                if k in t_data:
                    try:
                        t_sec = (datetime.strptime(t_data[k], "%Y-%m-%d %H:%M:%S") - now).total_seconds()
                        if t_sec > 0:
                            h, r = divmod(int(t_sec), 3600); m, s = divmod(r, 60)
                            st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:11px; font-weight:bold;'>{srv}</div><div style='text-align:center; color:#3498db; font-size:20px; font-weight:bold; margin:10px 0;'>{h:02d}:{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                            is_run = True
                        else:
                            st.markdown(f"<div style='text-align:center; color:#00ff66; font-size:11px; font-weight:bold;'>{srv}</div><div style='text-align:center; color:#00ff66; font-size:16px; font-weight:bold; margin:13px 0;'>[ SPAWNED ]</div>", unsafe_allow_html=True)
                    except: pass
                
                if not is_run and k not in t_data or (k in t_data and t_sec <= 0):
                    if k not in t_data: st.markdown(f"<div style='text-align:center; color:#475569; font-size:11px; font-weight:bold;'>{srv}</div><div style='text-align:center; color:#3b82f6; font-size:20px; font-weight:bold; margin:10px 0;'>--:--:--</div>", unsafe_allow_html=True)
                
                b1, b2, b3 = st.columns(3)
                with b1: st.button("SPAWN", key=f"s_{k}", disabled=is_run, on_click=on_spawn, args=(k, srv, st.session_state.current_city))
                with b2: st.button("UNDO", key=f"u_{k}", disabled=not b_data.get(k), on_click=on_undo, args=(k, srv, st.session_state.current_city, b_data.get(k, {}).get("spawn_time")))
                with b3: st.button("RESET", key=f"r_{k}", disabled=not is_run, on_click=on_reset, args=(k, srv, st.session_state.current_city, t_data.get(k)))

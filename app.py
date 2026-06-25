import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import threading

# ================= 1. ตั้งค่าหน้าเว็บ =================
st.set_page_config(page_title="❖ NYXORAA CLAN RADAR ❖", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= 2. CUSTOM UI THEME =================
st.markdown("""
<style>
    /* ซ่อนเมนูขยะ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* โทนสีพื้นหลังและฟอนต์ */
    .stApp { background-color: #080b12 !important; font-family: 'Consolas', 'Segoe UI', monospace !important; }
    section[data-testid="stSidebar"] { background-color: #0e131f !important; border-right: 1px solid #1e293b !important; }
    h1, h2, h3, p, div, span { color: #e2e8f0; }
    
    /* กล่องข้อมูล / การ์ดบอส */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background: linear-gradient(145deg, #121824 0%, #0a0f18 100%);
        border-color: #1e293b !important;
        border-radius: 4px !important;
    }
    
    /* ช่องกรอกข้อความ */
    .stTextInput input {
        background-color: #080b12 !important; color: #00ff66 !important;
        border: 1px solid #2d3748 !important; border-radius: 2px !important;
        text-align: left; padding: 10px !important; font-weight: bold;
    }
    .stTextInput input:focus { border-color: #00ff66 !important; box-shadow: 0 0 8px rgba(0,255,102,0.3) !important; }
    
    /* ปุ่มกดทั่วไป */
    .stButton>button {
        background-color: #131a28 !important; color: #94a3b8 !important;
        border: 1px solid #2d3748 !important; border-radius: 2px !important;
        font-weight: bold !important; width: 100%; transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1e293b !important; border-color: #00ff66 !important; color: #00ff66 !important;
    }
    
    /* กล่อง Log */
    div[data-testid="stTextArea"] textarea {
        background-color: #080b12 !important; border: 1px solid #1e293b !important;
        color: #94a3b8 !important; font-size: 12px !important; border-radius: 2px !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 3. FIREBASE INIT (CACHE) =================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # 📌 วางคีย์ Firebase ของน้องหวือลงไปตรงนี้ (แนะนำให้ใช้ st.secrets ในอนาคต)
            FIREBASE_CRED_DICT = {
                "type": "service_account",
                "project_id": "arz-boss-tracker",
                "private_key_id": "YOUR_PRIVATE_KEY_ID_HERE",
                "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n".replace('\\n', '\n'),
                "client_email": "firebase-adminsdk-fbsvc@arz-boss-tracker.iam.gserviceaccount.com",
                "client_id": "YOUR_CLIENT_ID_HERE",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40arz-boss-tracker.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }
            cred = credentials.Certificate(FIREBASE_CRED_DICT)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        except Exception as e:
            st.error(f"❌ FIREBASE ERROR: {e}")

init_firebase()

# ================= 4. ตัวแปรคงที่ (DATA) =================
CITIES = {
    "Norad Military Base": "🛡️",
    "Ridgeway Airport": "✈️",
    "Crystal Lake Resort": "🏕️",
    "Campos City": "🏙️"
}

SERVERS = {
    "Official": [f"TH SERVER {i:03d}" for i in range(1, 31)],
    "Premium": [f"TH PREMIUM SERVER {i:03d}" for i in range(1, 51)]
}

# ================= 5. SESSION STATE =================
if "page" not in st.session_state: st.session_state.page = "login" # หน้าปัจจุบัน (login, hub, dashboard)
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "current_type" not in st.session_state: st.session_state.current_type = "Official"
if "current_city" not in st.session_state: st.session_state.current_city = list(CITIES.keys())[0]

# ================= 6. FAST CALLBACK FUNCTIONS (ลดอาการค้าง) =================
def set_page(page_name):
    st.session_state.page = page_name

def select_network(network_type):
    st.session_state.current_type = network_type
    st.session_state.page = "dashboard"

def push_log_bg(action, server_name, city):
    # ยิง Log แบบ Background Thread ไม่ให้หน้าจอหลักสะดุด
    def task():
        now_str = datetime.now().strftime("%H:%M:%S")
        log_id = str(uuid.uuid4())[:8]
        log_data = {
            "id": log_id, "user": st.session_state.user_name, "action": action,
            "city": city, "server": server_name, "time": now_str, "timestamp": datetime.now().timestamp()
        }
        try: db.reference(f'shared_action_logs/{log_id}').set(log_data)
        except: pass
    threading.Thread(target=task, daemon=True).start()

def action_spawn(db_key, server_name, city):
    next_spawn = datetime.now() + timedelta(seconds=COOLDOWN_SECONDS)
    db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
    push_log_bg("SPAWN", server_name, city)

def action_undo(db_key, server_name, city, backup_time):
    db.reference(f'boss_timers/{db_key}').set(backup_time)
    db.reference(f'backup_timers/{db_key}').delete()
    push_log_bg("UNDO", server_name, city)

def action_reset(db_key, server_name, city, current_time):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.reference(f'backup_timers/{db_key}').set({"spawn_time": current_time, "deleted_at": now_str})
    db.reference(f'boss_timers/{db_key}').delete()
    push_log_bg("RESET", server_name, city)

# ================= 7. RENDER VIEWS =================

# ----------------- PAGE 1: LOGIN -----------------
if st.session_state.page == "login":
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c2:
        st.markdown("""
        <div style='background-color: #0f1522; border-left: 4px solid #00ff66; padding: 30px; text-align: center; border-radius: 4px;'>
            <h1 style='color: #00ff66; margin: 0; font-size: 32px;'>❖ NYXORAA UPLINK ❖</h1>
            <p style='color: #64748b; font-size: 12px; margin-top: 5px; letter-spacing: 1px;'>IDENTIFICATION REQUIRED TO ACCESS CLAN RADAR</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        input_name = st.text_input("OPERATIVE NAME (ระบุชื่อตัวละคร):", value=st.session_state.user_name)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("[ INITIALIZE CONNECTION ]"):
            if input_name.strip() == "":
                st.error("⚠️ ข้อมูลไม่ครบ: กรุณาระบุชื่อตัวละคร")
            else:
                st.session_state.user_name = input_name.strip()
                set_page("hub")
                st.rerun()

# ----------------- PAGE 2: HUB (SERVER SELECTION) -----------------
elif st.session_state.page == "hub":
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c2:
        st.markdown("""
        <div style='background-color: #0f1522; border-top: 3px solid #00ff66; padding: 40px 20px; text-align: center; border-radius: 4px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);'>
            <h1 style='color: #ffffff; margin: 0; font-size: 36px; text-transform: uppercase;'>SERVER SELECTION</h1>
            <p style='color: #64748b; font-size: 14px; margin-top: 5px; letter-spacing: 1px;'>CHOOSE NETWORK TO SYNCHRONIZE</p>
            <br><br>
        """, unsafe_allow_html=True)
        
        st.button("[ INITIATE OFFICIAL (30) ]", on_click=select_network, args=("Official",))
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("[ INITIATE PREMIUM (50) ]", on_click=select_network, args=("Premium",))
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.button("[ SWITCH CHARACTER ]", on_click=set_page, args=("login",))
        
        st.markdown("</div>", unsafe_allow_html=True)

# ----------------- PAGE 3: DASHBOARD -----------------
elif st.session_state.page == "dashboard":
    now = datetime.now()
    
    # 📌 ดึงข้อมูลรวดเดียว (Batch Fetching) ลดการค้างหน้าจอ 100%
    timers_data = db.reference('boss_timers').get() or {}
    backup_data = db.reference('backup_timers').get() or {}
    raw_logs = db.reference('shared_action_logs').get() or {}

    # === SIDEBAR ===
    with st.sidebar:
        # Network Header
        color = "#ff6b00" if st.session_state.current_type == "Premium" else "#3498db"
        st.markdown(f"""
        <div style='padding: 10px 0;'>
            <h1 style='color: {color}; margin: 0; font-size: 28px;'>❖ {st.session_state.current_type.upper()}</h1>
            <p style='color: #64748b; font-size: 12px; margin: 0;'>NETWORK SELECTED</p>
        </div>
        <hr style='border-color: #1e293b; margin: 10px 0 20px 0;'>
        """, unsafe_allow_html=True)
        
        # Cities Navigation
        for city_name, icon in CITIES.items():
            # ใช้ CSS แบบเนียนๆ แบ่งสีปุ่มที่กำลังเลือกอยู่
            if st.session_state.current_city == city_name:
                st.markdown(f"<button style='width:100%; background:#e65c00; color:#fff; border:none; padding:10px; border-radius:3px; margin-bottom:10px; font-weight:bold; text-align:left;'>{icon} &nbsp; {city_name}</button>", unsafe_allow_html=True)
            else:
                if st.button(f"{icon}  {city_name}", key=f"nav_{city_name}"):
                    st.session_state.current_city = city_name
                    st.rerun()
                    
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Action Log Box
        st.markdown("<span style='color: #64748b; font-size: 12px;'>📡 LIVE ACTION LOG</span>", unsafe_allow_html=True)
        log_text = ""
        if raw_logs and isinstance(raw_logs, dict):
            sorted_logs = sorted(raw_logs.values(), key=lambda x: x.get('timestamp', 0), reverse=True)
            for l in sorted_logs:
                if l.get('city') == st.session_state.current_city:
                    icon = "🟢" if l['action'] == "SPAWN" else "🔴" if l['action'] == "RESET" else "⏪"
                    log_text += f"[{l['time']}] {icon} [{l['user']}]\n> {l['action']} {l['server']}\n\n"
                    
        st.text_area("Logs", value=log_text if log_text else "[SYSTEM] READY...", height=250, disabled=True, label_visibility="collapsed")
        
        # Back Button
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("[ BACK TO HUB ]", on_click=set_page, args=("hub",))

    # === MAIN CONTENT ===
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown(f"<h2>📍 <span style='color: #ffffff;'>TARGET: {st.session_state.current_city.upper()}</span></h2>", unsafe_allow_html=True)
    with header_col2:
        st.markdown(f"<div style='text-align: right; margin-top: 15px; font-size: 14px; font-weight: bold; color: #00ff66;'>RADAR STATUS: ACTIVE 🟢</div>", unsafe_allow_html=True)

    srv_list = SERVERS[st.session_state.current_type]
    grid_cols = st.columns(4)
    
    # วาดการ์ด 4 แถว (ใช้ Loop ดึงข้อมูลจาก Memory ไม่ดึงเน็ต)
    for idx, server_name in enumerate(srv_list):
        db_key = f"{st.session_state.current_type}_{st.session_state.current_city}_{server_name}"
        col_target = grid_cols[idx % 4]
        
        with col_target:
            with st.container(border=True):
                # ส่วนหัวและเวลา
                if db_key in timers_data:
                    try:
                        spawn_time = datetime.strptime(timers_data[db_key], "%Y-%m-%d %H:%M:%S")
                        total_secs = (spawn_time - now).total_seconds()
                        
                        if total_secs > 0:
                            h, r = divmod(int(total_secs), 3600)
                            m, s = divmod(r, 60)
                            st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; font-weight:bold;'>{server_name}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='text-align:center; color:#3498db; font-size:24px; font-weight:bold; margin: 10px 0;'>{h:02d}:{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                            is_running = True
                            is_spawned = False
                        else:
                            st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; font-weight:bold;'>{server_name}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='text-align:center; color:#00ff66; font-size:24px; font-weight:bold; margin: 10px 0;'>- - : - - : - -</div>", unsafe_allow_html=True)
                            is_running = False
                            is_spawned = True
                    except:
                        is_running = False
                        is_spawned = False
                else:
                    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; font-weight:bold;'>{server_name}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; color:#3498db; font-size:24px; font-weight:bold; margin: 10px 0;'>- - : - - : - -</div>", unsafe_allow_html=True)
                    is_running = False
                    is_spawned = False

                # ส่วนปุ่มกด 3 ปุ่ม (ใช้ Callback สั่งงานตรง ไม่รันลูปใหม่)
                b1, b2, b3 = st.columns(3)
                
                # ปุ่ม SPAWN
                with b1:
                    if is_running:
                        st.button("SPAWN", key=f"sp_dis_{db_key}", disabled=True)
                    else:
                        st.button("SPAWN", key=f"sp_{db_key}", on_click=action_spawn, args=(db_key, server_name, st.session_state.current_city))
                
                # ปุ่ม UNDO
                with b2:
                    if backup_data.get(db_key):
                        st.button("UNDO", key=f"un_{db_key}", on_click=action_undo, args=(db_key, server_name, st.session_state.current_city, backup_data[db_key]["spawn_time"]))
                    else:
                        st.button("UNDO", key=f"un_dis_{db_key}", disabled=True)
                        
                # ปุ่ม RESET
                with b3:
                    if is_running:
                        st.button("RESET", key=f"rs_{db_key}", on_click=action_reset, args=(db_key, server_name, st.session_state.current_city, timers_data[db_key]))
                    else:
                        st.button("RESET", key=f"rs_dis_{db_key}", disabled=True)

import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import threading
import json
import time
from functools import lru_cache

# ================= 1. PAGE CONFIG =================
st.set_page_config(
    page_title="❖ NYXORAA CLAN RADAR ❖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

COOLDOWN_SECONDS = 3600
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"
REFRESH_INTERVAL = 1  # Auto-refresh every 1 second for smooth countdown

# ================= 2. ADVANCED UI THEME (CSS) =================
CUSTOM_CSS = """
<style>
    * { box-sizing: border-box; }
    
    /* Hide UI Elements */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    [data-testid="stStatusWidget"] {display: none;}
    
    /* Global Theme */
    .stApp { 
        background-color: #0a0e14 !important; 
        font-family: 'JetBrains Mono', 'Consolas', monospace !important; 
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { 
        background: linear-gradient(135deg, #0b0f19 0%, #0e131f 100%) !important; 
        border-right: 2px solid #1a2f4f !important; 
    }
    
    /* Main Container */
    .main > div:first-child { 
        background-color: #0a0e14 !important; 
        padding-top: 20px !important;
    }
    
    /* Button Styling - Full Width */
    .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #0f1419 0%, #151d2b 100%) !important;
        color: #94a3b8 !important;
        border: 1.5px solid #2d3748 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 12px 16px !important;
        font-size: 13px !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1a2f4f 0%, #0f4b88 100%) !important;
        border-color: #3b82f6 !important;
        color: #60a5fa !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.4), inset 0 0 10px rgba(59, 130, 246, 0.1) !important;
        transform: translateY(-2px) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Primary Button */
    button[kind="primary"] { 
        background: linear-gradient(135deg, #1a3a5f 0%, #2563eb 100%) !important;
        border-color: #3b82f6 !important; 
        color: #fff !important; 
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.5), inset 0 0 15px rgba(59, 130, 246, 0.2) !important;
    }
    
    /* Secondary Button (Premium) */
    button[kind="secondary"] { 
        background: linear-gradient(135deg, #5a2a0a 0%, #dc2626 100%) !important;
        border-color: #d35400 !important; 
        color: #fff !important; 
    }
    button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.5), inset 0 0 15px rgba(220, 38, 38, 0.2) !important;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background-color: #0f1419 !important; 
        color: #00ff88 !important;
        border: 1.5px solid #1e3a5f !important; 
        border-radius: 6px !important;
        font-family: monospace !important; 
        padding: 12px 14px !important;
        font-size: 13px !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.3) !important;
        color: #60a5fa !important;
    }
    
    /* Text Area (Logs) */
    .stTextArea textarea {
        background-color: #050709 !important; 
        border: 1.5px solid #1a2f4f !important;
        color: #64748b !important; 
        font-size: 11px !important;
        border-radius: 6px !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Container Styles */
    .hub-container {
        background: linear-gradient(135deg, #0e131f 0%, #0b0f19 100%);
        border-top: 3px solid #00ff88;
        border-radius: 8px;
        padding: 50px 40px;
        box-shadow: 0 15px 40px rgba(0, 255, 136, 0.1), inset 0 1px 1px rgba(255,255,255,0.1);
        text-align: center;
        margin-bottom: 30px;
    }
    
    .login-container {
        background: linear-gradient(135deg, #0e131f 0%, #1a1f2e 100%);
        border-left: 4px solid #00ff88;
        border-radius: 8px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255,255,255,0.05);
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
    }
    
    .server-card {
        background: linear-gradient(135deg, #0f1419 0%, #141820 100%) !important;
        border: 1.5px solid #1a2f4f !important;
        border-radius: 8px !important;
        padding: 16px !important;
        transition: all 0.3s ease !important;
    }
    
    .server-card:hover {
        border-color: #3b82f6 !important;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25) !important;
        transform: translateY(-2px) !important;
    }
    
    .server-card.active {
        border-color: #00ff88 !important;
        box-shadow: 0 8px 25px rgba(0, 255, 136, 0.3) !important;
    }
    
    /* Timer Text */
    .timer-text {
        font-weight: 700;
        letter-spacing: 1px;
        font-family: 'Courier New', monospace;
    }
    
    .timer-running {
        color: #3b82f6;
        font-size: 24px;
    }
    
    .timer-spawned {
        color: #00ff88;
        font-size: 18px;
        text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
    }
    
    .timer-idle {
        color: #64748b;
        font-size: 20px;
    }
    
    /* HR Styling */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, #1a2f4f, transparent) !important;
        margin: 15px 0 !important;
    }
    
    /* Sidebar Navigation */
    .nav-city-btn {
        text-align: left !important;
        border-left: 3px solid transparent !important;
        transition: all 0.2s ease !important;
        padding-left: 15px !important;
    }
    
    .nav-city-btn:hover {
        border-left-color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.1) !important;
    }
    
    .nav-city-btn.active {
        border-left-color: #00ff88 !important;
        background-color: rgba(0, 255, 136, 0.1) !important;
        color: #00ff88 !important;
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    .status-active {
        background-color: rgba(0, 255, 136, 0.2);
        color: #00ff88;
        border: 1px solid #00ff88;
    }
    
    .status-warning {
        background-color: rgba(255, 193, 7, 0.2);
        color: #ffc107;
        border: 1px solid #ffc107;
    }
    
    .scrollable-log {
        max-height: 300px;
        overflow-y: auto;
    }
    
    /* Divider Text */
    .divider-text {
        color: #475569;
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 600;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ================= 3. FIREBASE INIT =================
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
    """Initialize Firebase with error handling"""
    if not firebase_admin._apps:
        try:
            cred_dict = json.loads(FIREBASE_JSON_STR)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            return True
        except json.JSONDecodeError:
            st.error("❌ Firebase JSON ไม่ถูกต้อง โปรดตรวจสอบการ config")
            return False
        except Exception as e:
            st.error(f"❌ Firebase Error: {str(e)}")
            return False
    return True

firebase_ready = init_firebase()

# ================= 4. CONSTANTS & DATA =================
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

# ================= 5. UTILITY FUNCTIONS =================
@lru_cache(maxsize=32)
def format_time_remaining(seconds):
    """Format seconds to HH:MM:SS efficiently"""
    if seconds <= 0:
        return "READY"
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def safe_firebase_call(func, *args, **kwargs):
    """Safely execute Firebase calls with error handling"""
    try:
        if not firebase_ready:
            return None
        return func(*args, **kwargs)
    except Exception as e:
        st.warning(f"⚠️ Firebase sync issue: {str(e)[:50]}")
        return None

def push_log_bg(action, srv, city):
    """Push action log to Firebase in background thread"""
    def task():
        safe_firebase_call(
            lambda: db.reference(f'shared_action_logs/{str(uuid.uuid4())[:8]}').set({
                "user": st.session_state.user_name,
                "action": action,
                "city": city,
                "server": srv,
                "time": datetime.now().strftime("%H:%M:%S"),
                "timestamp": datetime.now().timestamp()
            })
        )
    threading.Thread(target=task, daemon=True).start()

def on_spawn(key, srv, city):
    """Handle spawn action"""
    new_time = (datetime.now() + timedelta(seconds=COOLDOWN_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
    safe_firebase_call(lambda: db.reference(f'boss_timers/{key}').set(new_time))
    push_log_bg("SPAWN", srv, city)

def on_undo(key, srv, city, back_time):
    """Handle undo action"""
    if back_time:
        safe_firebase_call(lambda: db.reference(f'boss_timers/{key}').set(back_time))
        safe_firebase_call(lambda: db.reference(f'backup_timers/{key}').delete())
        push_log_bg("UNDO", srv, city)

def on_reset(key, srv, city, cur_time):
    """Handle reset action"""
    if cur_time:
        safe_firebase_call(lambda: db.reference(f'backup_timers/{key}').set({"spawn_time": cur_time}))
        safe_firebase_call(lambda: db.reference(f'boss_timers/{key}').delete())
        push_log_bg("RESET", srv, city)

# ================= 6. SESSION STATE MANAGEMENT =================
if "page" not in st.session_state:
    st.session_state.page = "login"
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "current_type" not in st.session_state:
    st.session_state.current_type = "Official"
if "current_city" not in st.session_state:
    st.session_state.current_city = list(CITIES.keys())[0]
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

def nav(page):
    st.session_state.page = page

def set_net(net):
    st.session_state.current_type = net
    st.session_state.page = "dashboard"

# ================= 7. PAGE: LOGIN =================
if st.session_state.page == "login":
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("""
        <div class='login-container'>
            <h1 style='color: #00ff88; margin: 0; font-size: 32px; text-shadow: 0 0 15px rgba(0,255,136,0.4); letter-spacing: 2px;'>❖ NYXORAA UPLINK ❖</h1>
            <p style='color: #64748b; font-size: 12px; margin-top: 8px; letter-spacing: 1.5px; text-transform: uppercase;'>▸ IDENTIFICATION REQUIRED ◂</p>
            <p style='color: #475569; font-size: 11px; margin-top: 4px;'>ACCESSING CLAN RADAR SYSTEM</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='color: #e2e8f0; font-size: 12px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>📡 OPERATIVE NAME:</p>", unsafe_allow_html=True)
        
        uname = st.text_input(
            "",
            value=st.session_state.user_name,
            label_visibility="collapsed",
            placeholder="Enter your character name..."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("[ INITIALIZE ]", use_container_width=True, key="login_btn"):
                if uname.strip():
                    st.session_state.user_name = uname.strip()
                    nav("hub")
                    st.rerun()
                else:
                    st.error("⚠️ Please enter character name")
        
        with col2:
            st.markdown("<p></p>", unsafe_allow_html=True)

# ================= 8. PAGE: HUB =================
elif st.session_state.page == "hub":
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2.5, 1])
    
    with col:
        st.markdown("""
        <div class='hub-container'>
            <h1 style='color: #ffffff; margin: 0; font-size: 36px; letter-spacing: 1px;'>⬢ SERVER SELECTION ⬢</h1>
            <p style='color: #64748b; font-size: 13px; margin-top: 8px; letter-spacing: 1px; text-transform: uppercase;'>CHOOSE YOUR NETWORK</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button(
                "[ OFFICIAL ]\\n30 SERVERS",
                type="primary",
                key="btn_official",
                use_container_width=True
            ):
                set_net("Official")
                st.rerun()
        
        with c2:
            if st.button(
                "[ PREMIUM ]\\n50 SERVERS",
                type="secondary",
                key="btn_premium",
                use_container_width=True
            ):
                set_net("Premium")
                st.rerun()
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if st.button("[ SWITCH CHARACTER ]", use_container_width=True, key="btn_switch"):
            nav("login")
            st.rerun()

# ================= 9. PAGE: DASHBOARD =================
elif st.session_state.page == "dashboard":
    if not firebase_ready:
        st.error("❌ Firebase connection failed. Please check configuration.")
        st.stop()
    
    # Fetch data from Firebase
    now = datetime.now()
    t_data = safe_firebase_call(lambda: db.reference('boss_timers').get()) or {}
    b_data = safe_firebase_call(lambda: db.reference('backup_timers').get()) or {}
    l_data = safe_firebase_call(lambda: db.reference('shared_action_logs').get()) or {}
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        # Header
        color = "#dc2626" if st.session_state.current_type == "Premium" else "#3b82f6"
        st.markdown(f"""
        <div style='text-align: center; padding: 15px 0;'>
            <h2 style='color: {color}; margin: 0 0 5px 0; font-size: 22px; letter-spacing: 1px;'>
                ❖ {st.session_state.current_type.upper()} ❖
            </h2>
            <p style='color: #64748b; font-size: 11px; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;'>
                📡 NETWORK ACTIVE
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # City Navigation
        st.markdown("<p class='divider-text'>📍 TARGET LOCATIONS</p>", unsafe_allow_html=True)
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        
        for c_name, icon in CITIES.items():
            is_active = c_name == st.session_state.current_city
            btn_class = "active" if is_active else ""
            
            if st.button(
                f"{icon}  {c_name}",
                key=f"nav_{c_name}",
                use_container_width=True
            ):
                st.session_state.current_city = c_name
                st.rerun()
        
        st.divider()
        
        # Live Action Log
        st.markdown("<p class='divider-text'>⚡ ACTION LOG (LIVE)</p>", unsafe_allow_html=True)
        
        # Filter logs by city
        city_logs = [
            l for l in (l_data.values() if l_data else [])
            if l.get('city') == st.session_state.current_city
        ]
        city_logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        log_text = ""
        if city_logs:
            for log in city_logs[:20]:  # Show last 20 logs
                action_icon = "🟢" if log['action'] == 'SPAWN' else ("🔄" if log['action'] == 'UNDO' else "⏹️")
                log_text += f"[{log['time']}] {action_icon}\n{log['user']} • {log['action']}\n\n"
        
        st.text_area(
            "Logs",
            value=log_text if log_text else "[ SYSTEM ] READY FOR OPERATIONS...",
            height=280,
            disabled=True,
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("[ BACK TO HUB ]", use_container_width=True, key="btn_back_hub"):
            nav("hub")
            st.rerun()
    
    # ========== MAIN AREA ==========
    # Header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
        <h2 style='margin: 0 0 15px 0; font-size: 24px; letter-spacing: 0.5px;'>
            📍 <span style='color: #00ff88;'>{st.session_state.current_city.upper()}</span>
        </h2>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='text-align: right; margin-top: 5px; padding: 8px 12px; background: rgba(0, 255, 136, 0.1); border: 1px solid #00ff88; border-radius: 6px; display: inline-block;'>
            <span style='color: #00ff88; font-size: 12px; font-weight: bold; letter-spacing: 1px;'>
                ◆ ACTIVE ◆
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Server Cards Grid
    server_list = SERVERS[st.session_state.current_type]
    
    # Create dynamic columns based on screen size
    cols = st.columns(4)
    
    for idx, srv in enumerate(server_list):
        k = f"{st.session_state.current_type}_{st.session_state.current_city}_{srv}"
        
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"<div style='text-align: center; color: #94a3b8; font-size: 12px; font-weight: bold; margin-bottom: 12px;'>{srv}</div>", unsafe_allow_html=True)
                
                # Timer Display
                timer_status = "idle"
                display_time = "--:--:--"
                
                if k in t_data:
                    try:
                        timer_dt = datetime.strptime(t_data[k], "%Y-%m-%d %H:%M:%S")
                        time_diff = (timer_dt - now).total_seconds()
                        
                        if time_diff > 0:
                            display_time = format_time_remaining(time_diff)
                            timer_status = "running"
                        else:
                            timer_status = "spawned"
                            display_time = "SPAWNED"
                    except Exception as e:
                        st.warning(f"Time parse error: {srv}")
                
                # Render timer based on status
                if timer_status == "spawned":
                    st.markdown(f"<div style='text-align: center; color: #00ff88; font-size: 16px; font-weight: bold; margin: 15px 0; text-shadow: 0 0 10px rgba(0,255,136,0.3);'>[ {display_time} ]</div>", unsafe_allow_html=True)
                else:
                    color = "#3b82f6" if timer_status == "running" else "#64748b"
                    st.markdown(f"<div style='text-align: center; color: {color}; font-size: 20px; font-weight: bold; margin: 12px 0; font-family: monospace;'>{display_time}</div>", unsafe_allow_html=True)
                
                # Action Buttons
                b1, b2, b3 = st.columns(3)
                
                with b1:
                    st.button(
                        "SPAWN",
                        key=f"s_{k}",
                        disabled=(timer_status == "running"),
                        on_click=on_spawn,
                        args=(k, srv, st.session_state.current_city),
                        use_container_width=True
                    )
                
                with b2:
                    has_backup = k in b_data
                    st.button(
                        "UNDO",
                        key=f"u_{k}",
                        disabled=(not has_backup),
                        on_click=on_undo,
                        args=(k, srv, st.session_state.current_city, b_data.get(k, {}).get("spawn_time")),
                        use_container_width=True
                    )
                
                with b3:
                    st.button(
                        "RESET",
                        key=f"r_{k}",
                        disabled=(timer_status != "running"),
                        on_click=on_reset,
                        args=(k, srv, st.session_state.current_city, t_data.get(k)),
                        use_container_width=True
                    )
    
    # Auto-refresh
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Display last updated time
    st.markdown(f"""
    <div style='text-align: center; color: #64748b; font-size: 10px; margin-top: 20px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 6px;'>
        ⟳ Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh enabled
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh every second
    import streamlit.components.v1 as components
    components.html("""
    <script>
        setTimeout(() => {
            window.parent.document.querySelector('button[kind="secondary"]').click();
        }, 1000);
    </script>
    """, height=0)

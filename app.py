import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import urllib.request
import urllib.parse
import json

# 📌 ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง และซ่อน UI ขยะของ Streamlit
st.set_page_config(page_title="❖ NYXORAA CLAN RADAR ❖", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxLuBcnupdwj1ippurn9t18kE5pnGucV4Q-CTBr9f7vLApYa_NhwncLTH6FRmJI24u0lw/exec"
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= CUSTOM UI THEME (Nyxoraa Style) =================
st.markdown("""
<style>
    /* ซ่อนเมนูขยะของ Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* พื้นหลังและโทนสีหลัก */
    .stApp {
        background-color: #0b0f19 !important;
        font-family: 'Consolas', 'Segoe UI', monospace !important;
    }
    
    /* สไตล์แถบ Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #121826 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* หัวข้อและตัวหนังสือ */
    h1, h2, h3 {
        color: #e2e8f0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* การ์ดเวลากำลังวิ่ง (สีแดง Tactical) */
    .boss-card-running {
        background: linear-gradient(145deg, #1a0f14 0%, #11141d 100%) !important;
        border-top: 3px solid #ff3b3b !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        box-shadow: 0 10px 15px -3px rgba(255, 59, 59, 0.1) !important;
        margin-bottom: 15px !important;
    }
    
    /* การ์ดเวลาบอสเกิด (สีเขียวนีออน) */
    .boss-card-spawned {
        background: linear-gradient(145deg, #0d1f16 0%, #11141d 100%) !important;
        border-top: 3px solid #00ff66 !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.2) !important;
        margin-bottom: 15px !important;
        animation: glow 1.5s infinite alternate;
    }
    
    /* การ์ดสถานะว่างเปล่า (สีฟ้าเทา) */
    .boss-card-empty {
        background-color: #131a28 !important;
        border-top: 3px solid #3b82f6 !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
    }
    
    /* กล่องข้อความกรอกข้อมูล */
    .stTextInput input {
        background-color: #0b0f19 !important;
        color: #00ff66 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 2px !important;
        font-family: monospace !important;
    }
    .stTextInput input:focus {
        border-color: #00ff66 !important;
        box-shadow: 0 0 5px rgba(0,255,102,0.3) !important;
    }
    
    /* ปุ่มกดสไตล์ Nyxoraa */
    .stButton>button {
        background-color: #1a2235 !important;
        color: #94a3b8 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 2px !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1e293b !important;
        border-color: #00ff66 !important;
        color: #00ff66 !important;
        box-shadow: 0 0 10px rgba(0, 255, 102, 0.2) !important;
    }
    
    /* ตู้ข้อความประวัติ Log */
    div[data-testid="stTextArea"] textarea {
        background-color: #0b0f19 !important;
        border: 1px solid #1e293b !important;
        color: #94a3b8 !important;
        font-family: 'Consolas', monospace !important;
        border-radius: 2px !important;
    }
    
    @keyframes glow {
        0% { box-shadow: 0 0 10px rgba(0, 255, 102, 0.1); }
        100% { box-shadow: 0 0 25px rgba(0, 255, 102, 0.4); }
    }
</style>
""", unsafe_allow_html=True)

# ================= FIREBASE INITIALIZATION =================
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            fb_cred = dict(st.secrets["firebase"])
            cred = credentials.Certificate(fb_cred)
        else:
            cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")

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

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "current_type" not in st.session_state: st.session_state.current_type = "Official"
if "current_city" not in st.session_state: st.session_state.current_city = list(CITIES.keys())[0]

# ================= FUNCTIONS =================
def verify_key(key, username):
    try:
        # 📌 บนเว็บใช้ "ชื่อตัวละคร" เป็นตัวล็อก Hardware ID เพื่อหลบข้อจำกัดของเบราว์เซอร์
        url = f"{GOOGLE_SHEET_WEBAPP_URL}?key={urllib.parse.quote(key)}&hwid={urllib.parse.quote(username)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.read().decode('utf-8').strip() == "APPROVED"
    except: return False

def push_shared_log(action, server_name, city):
    now_str = datetime.now().strftime("%H:%M:%S")
    log_id = str(uuid.uuid4())[:8]
    log_data = {
        "id": log_id, "user": st.session_state.user_name, "action": action,
        "city": city, "server": server_name, "time": now_str, "timestamp": datetime.now().timestamp()
    }
    try:
        db.reference(f'shared_action_logs/{log_id}').set(log_data)
        # เคลียร์ Log เก่าเกิน 150 รายการ
        ref = db.reference('shared_action_logs')
        all_logs = ref.get()
        if all_logs and isinstance(all_logs, dict) and len(all_logs) > 150:
            sorted_items = sorted(all_logs.items(), key=lambda x: x[1].get('timestamp', 0))
            for i in range(len(sorted_items) - 150):
                ref.child(sorted_items[i][0]).delete()
    except: pass

# ================= INTERFACE VIEW =================

# 1. หน้าต่างกรอก KEY 
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # รูปแบนเนอร์เท่ๆ (Nyxoraa Style)
        st.markdown("""
        <div style='background: linear-gradient(90deg, #11141d 0%, #1a2235 100%); border-left: 4px solid #ff3b3b; padding: 30px; border-radius: 4px; text-align: center;'>
            <h1 style='color: #ff3b3b; margin-bottom: 5px; text-shadow: 0 0 10px rgba(255,59,59,0.3);'>❖ UPLINK SECURITY ❖</h1>
            <p style='color: #64748b; font-size: 14px; letter-spacing: 2px;'>AUTHORIZATION REQUIRED TO ACCESS RADAR</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        input_name = st.text_input("OPERATIVE NAME (ชื่อตัวละคร):", value=st.session_state.user_name)
        input_key = st.text_input("ACCESS LICENSE KEY (รหัสคีย์):", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("[ INITIALIZE CONNECTION ]", use_container_width=True):
            if not input_name.strip() or not input_key.strip():
                st.error("กรุณากรอกข้อมูลให้ครบถ้วนก่อนเข้าใช้งาน!")
            else:
                with st.spinner(">> DECRYPTING PAYLOAD..."):
                    # ส่ง Key และ Username ไปตรวจสอบ
                    if verify_key(input_key.strip(), input_name.strip()):
                        st.session_state.authenticated = True
                        st.session_state.user_name = input_name.strip()
                        st.rerun()
                    else: st.error("ACCESS DENIED: รหัสคีย์ไม่ถูกต้อง หรือถูกระงับสิทธิ์แล้ว!")

# 2. หน้าจอกระดานเรดาร์บอส
else:
    with st.sidebar:
        st.markdown(f"""
        <div style='background-color: #0b0f19; border: 1px solid #00ff66; padding: 15px; border-radius: 4px; text-align: center; box-shadow: inset 0 0 10px rgba(0,255,102,0.1);'>
            <span style='color: #64748b; font-size: 12px; letter-spacing: 1px;'>ACTIVE OPERATIVE</span><br>
            <strong style='color: #00ff66; font-size: 18px;'>{st.session_state.user_name}</strong>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        st.session_state.current_type = st.radio("📡 NETWORK TYPE:", ["Official", "Premium"])
        st.markdown("<hr style='border-color: #1e293b;'>", unsafe_allow_html=True)
        
        st.markdown("🎯 **SELECT SECTOR:**")
        for city_name, icon in CITIES.items():
            if st.button(f"{icon}  {city_name}", use_container_width=True):
                st.session_state.current_city = city_name
                st.rerun()
                
        st.markdown("<br><hr style='border-color: #1e293b;'><br>", unsafe_allow_html=True)
        if st.button("🔌 DISCONNECT (LOGOUT)", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown(f"<h2>📍 <span style='color: #64748b;'>SECTOR:</span> <span style='color: #00ff66;'>{st.session_state.current_city.upper()}</span> <span style='font-size: 14px; color: #3b82f6;'>[{st.session_state.current_type.upper()}]</span></h2>", unsafe_allow_html=True)
    
    now = datetime.now()
    timers_data = db.reference('boss_timers').get() or {}
    
    col_cards, col_logs = st.columns([3, 1])
    
    with col_cards:
        srv_list = SERVERS[st.session_state.current_type]
        grid_cols = st.columns(4)
        
        for idx, server_name in enumerate(srv_list):
            col_target = grid_cols[idx % 4]
            db_key = f"{st.session_state.current_type}_{st.session_state.current_city}_{server_name}"
            
            with col_target:
                if db_key in timers_data:
                    try:
                        spawn_time = datetime.strptime(timers_data[db_key], "%Y-%m-%d %H:%M:%S")
                        total_secs = (spawn_time - now).total_seconds()
                        
                        if total_secs > 0:
                            hours, remainder = divmod(int(total_secs), 3600)
                            mins, secs = divmod(remainder, 60)
                            st.markdown(f"""
                            <div class='boss-card-running'>
                                <div style='font-size: 11px; color: #64748b;'>{server_name}</div>
                                <div style='font-size: 28px; font-weight: bold; color: #ff3b3b; margin: 5px 0; text-shadow: 0 0 8px rgba(255,59,59,0.5);'>{hours:02d}:{mins:02d}:{secs:02d}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.button("SPAWN", key=f"sp_{db_key}", disabled=True, use_container_width=True)
                        else:
                            st.markdown(f"""
                            <div class='boss-card-spawned'>
                                <div style='font-size: 11px; color: #00ff66;'>{server_name}</div>
                                <div style='font-size: 24px; font-weight: bold; color: #00ff66; margin: 8px 0; text-shadow: 0 0 10px rgba(0,255,102,0.8);'>[ SPAWNED ]</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("SPAWN", key=f"sp_act_{db_key}", use_container_width=True):
                                next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                                db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                                push_shared_log("SPAWN", server_name, st.session_state.current_city)
                                st.rerun()
                    except: pass
                else:
                    st.markdown(f"""
                    <div class='boss-card-empty'>
                        <div style='font-size: 11px; color: #64748b;'>{server_name}</div>
                        <div style='font-size: 28px; font-weight: bold; color: #3b82f6; margin: 5px 0;'>--:--:--</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("SPAWN", key=f"sp_fresh_{db_key}", use_container_width=True):
                        next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                        db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                        push_shared_log("SPAWN", server_name, st.session_state.current_city)
                        st.rerun()
                
                c_undo, col_rst = st.columns(2)
                with c_undo:
                    has_backup = db.reference(f'backup_timers/{db_key}').get()
                    if has_backup:
                        if st.button("UNDO", key=f"un_{db_key}", use_container_width=True):
                            db.reference(f'boss_timers/{db_key}').set(has_backup["spawn_time"])
                            db.reference(f'backup_timers/{db_key}').delete()
                            push_shared_log("UNDO", server_name, st.session_state.current_city)
                            st.rerun()
                    else: st.button("UNDO", key=f"un_dis_{db_key}", disabled=True, use_container_width=True)
                        
                with col_rst:
                    if db_key in timers_data:
                        if st.button("RESET", key=f"rs_{db_key}", use_container_width=True):
                            db.reference(f'backup_timers/{db_key}').set({"spawn_time": timers_data[db_key], "deleted_at": now.strftime("%Y-%m-%d %H:%M:%S")})
                            db.reference(f'boss_timers/{db_key}').delete()
                            push_shared_log("RESET", server_name, st.session_state.current_city)
                            st.rerun()
                    else: st.button("RESET", key=f"rs_dis_{db_key}", disabled=True, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

    with col_logs:
        st.markdown("<h3 style='font-size: 16px; color: #94a3b8; border-bottom: 1px solid #1e293b; padding-bottom: 10px;'>>_ TERMINAL LOGS</h3>", unsafe_allow_html=True)
        raw_logs = db.reference('shared_action_logs').get() or {}
        log_box_content = ""
        if raw_logs and isinstance(raw_logs, dict):
            sorted_logs = sorted(raw_logs.values(), key=lambda x: x.get('timestamp', 0), reverse=True)
            for l in sorted_logs:
                if l.get('city') == st.session_state.current_city:
                    action_icon = "🟢" if l['action'] == "SPAWN" else "🔴" if l['action'] == "RESET" else "⏪"
                    log_box_content += f"[{l['time']}] {action_icon} [{l['user']}]\n> {l['action']} {l['server']}\n\n"
                    
        st.text_area("LOG_VIEW", value=log_box_content if log_box_content else "[SYSTEM] MONITORING ACTIVE...", height=600, disabled=True, label_visibility="collapsed")
        if st.button("🔄 REFRESH UPLINK", use_container_width=True):
            st.rerun()

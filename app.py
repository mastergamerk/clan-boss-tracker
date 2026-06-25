import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import random
import urllib.request
import urllib.parse
import os

# 📌 ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง และเปิดโหมดดาร์กตั้งแต่เริ่มโหลด
st.set_page_config(page_title="CHECK TIMER BOSS PIRIYA", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxLuBcnupdwj1ippurn9t18kE5pnGucV4Q-CTBr9f7vLApYa_NhwncLTH6FRmJI24u0lw/exec"
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= CUSTOM UI THEME (CSS) =================
# ยัดโค้ดตกแต่งสไตล์ Dark Cyberpunk คล้ายเว็บ Nyxora
st.markdown("""
<style>
    /* พื้นหลังและโทนสีหลักของเว็บ */
    .stApp {
        background-color: #05070f !important;
        font-family: 'Segoe UI', monospace !important;
    }
    
    /* สไตล์แถบ Sidebar ด้านซ้าย */
    section[data-testid="stSidebar"] {
        background-color: #0b0e14 !important;
        border-right: 1px solid #1f293d !important;
    }
    
    /* การ์ดเวลากำลังวิ่ง (สีแดงเรืองแสง) */
    .boss-card-running {
        background: linear-gradient(135deg, #120a0d 0%, #0c0e17 100%) !important;
        border: 1px solid #ff4747 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 0 15px rgba(255, 71, 73, 0.15) !important;
        margin-bottom: 15px !important;
    }
    
    /* การ์ดเวลาบอสเกิด (สีเขียวนีออนกระพริบเรืองแสง) */
    .boss-card-spawned {
        background: linear-gradient(135deg, #091a10 0%, #0c0e17 100%) !important;
        border: 2px solid #39ff14 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 0 25px rgba(57, 255, 20, 0.3) !important;
        margin-bottom: 15px !important;
        animation: pulse 1.5s infinite alternate;
    }
    
    /* การ์ดสถานะว่างเปล่า (สีฟ้านีออน) */
    .boss-card-empty {
        background-color: #0d111a !important;
        border: 1px solid #1f293d !important;
        border-radius: 8px !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
    }
    
    /* ปุ่มกดสไตล์สปอร์ตหรู Cyberpunk */
    .stButton>button {
        background-color: #0f141c !important;
        color: #ffffff !important;
        border: 1px solid #2d3748 !important;
        border-radius: 4px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        border-color: #39ff14 !important;
        box-shadow: 0 0 10px rgba(57, 255, 20, 0.5) !important;
        color: #39ff14 !important;
    }
    
    /* ตู้ข้อความประวัติ Log */
    div[data-testid="stTextArea"] textarea {
        background-color: #070a14 !important;
        border: 1px solid #1f293d !important;
        color: #a0aec0 !important;
        font-family: 'Consolas', monospace !important;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 15px rgba(57, 255, 20, 0.2); }
        100% { box-shadow: 0 0 30px rgba(57, 255, 20, 0.5); }
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
if "browser_id" not in st.session_state: st.session_state.browser_id = str(uuid.getnode())

# ================= FUNCTIONS =================
def verify_key(key):
    try:
        url = f"{GOOGLE_SHEET_WEBAPP_URL}?key={urllib.parse.quote(key)}&hwid={urllib.parse.quote(st.session_state.browser_id)}"
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
    try: db.reference(f'shared_action_logs/{log_id}').set(log_data)
    except: pass

# ================= INTERFACE VIEW =================

# 1. หน้าต่างกรอก KEY (สไตล์ความปลอดภัยขั้นสูง)
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='background-color: #0b0e14; border: 1px solid #ff4747; padding: 30px; border-radius: 8px; box-shadow: 0 0 20px rgba(255,71,71,0.15);'>
            <h2 style='text-align: center; color: #ff4747; margin-bottom: 5px;'>❖ ANTI-LEAK SECURITY SYSTEM ❖</h2>
            <p style='text-align: center; color: #718096; font-size: 13px; font-family: monospace;'>ENTER YOUR LICENSE KEY TO UNLOCK RADAR</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        input_name = st.text_input("OPERATIVE NAME (ชื่อตัวละคร):", value=st.session_state.user_name)
        input_key = st.text_input("ACCESS LICENSE KEY (รหัสคีย์):", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("[ ACTIVATE LICENSE SYSTEM ]", use_container_width=True):
            if not input_name.strip():
                st.error("กรุณากรอกชื่อตัวละครก่อนเข้าใช้งาน!")
            else:
                with st.spinner("กำลังตรวจสอบคีย์ของแคลน..."):
                    if verify_key(input_key):
                        st.session_state.authenticated = True
                        st.session_state.user_name = input_name.strip()
                        st.rerun()
                    else: st.error("รหัสคีย์ไม่ถูกต้อง หรือถูกผู้บริหารแคลนระงับสิทธิ์แล้ว!")

# 2. หน้าจอกระดานเรดาร์บอส (เมื่อล็อกอินเสร็จ)
else:
    with st.sidebar:
        st.markdown(f"<div style='border: 1px solid #39ff14; padding: 10px; border-radius: 4px; text-align: center;'><span style='color: #39ff14; font-weight: bold;'>👤 OPERATIVE:</span> <code style='color: #fff;'>{st.session_state.user_name}</code></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.session_state.current_type = st.radio("NETWORK TYPE:", ["Official", "Premium"])
        st.markdown("---")
        st.markdown("🎯 **SELECT TARGET CITY:**")
        for city_name, icon in CITIES.items():
            if st.button(f"{icon}  {city_name}", use_container_width=True):
                st.session_state.current_city = city_name
                st.rerun()
        st.markdown("---")
        if st.button("🚪 LOGOUT / SWITCH OPERATIVE", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown(f"<h2>📍 TARGET MAP: <span style='color: #39ff14;'>{st.session_state.current_city.upper()}</span> <span style='font-size: 16px; color: #718096;'>({st.session_state.current_type.upper()})</span></h2>", unsafe_allow_html=True)
    
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
                            # สภาพเวลากำลังนับถอยหลัง (ขอบแดง)
                            hours, remainder = divmod(int(total_secs), 3600)
                            mins, secs = divmod(remainder, 60)
                            st.markdown(f"""
                            <div class='boss-card-running'>
                                <div style='font-size: 11px; color: #a0aec0;'>{server_name}</div>
                                <div style='font-size: 26px; font-weight: bold; color: #ff4747; font-family: monospace; margin: 5px 0;'>{hours:02d}:{mins:02d}:{secs:02d}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.button("SPAWN", key=f"sp_{db_key}", disabled=True, use_container_width=True)
                        else:
                            # สภาพบอสเกิดแล้ว (ขอบเขียวนีออนกระพริบ)
                            st.markdown(f"""
                            <div class='boss-card-spawned'>
                                <div style='font-size: 11px; color: #39ff14;'>{server_name}</div>
                                <div style='font-size: 22px; font-weight: bold; color: #39ff14; font-family: monospace; margin: 7px 0;'>[ SPAWNED ]</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("SPAWN", key=f"sp_act_{db_key}", use_container_width=True):
                                next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                                db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                                push_shared_log("SPAWN", server_name, st.session_state.current_city)
                                st.rerun()
                    except: pass
                else:
                    # สภาพห้องว่างยังไม่มีการเซ็ตเวลา (ขอบมืดขีดฟ้า)
                    st.markdown(f"""
                    <div class='boss-card-empty'>
                        <div style='font-size: 11px; color: #4a5568;'>{server_name}</div>
                        <div style='font-size: 26px; font-weight: bold; color: #3182ce; font-family: monospace; margin: 5px 0;'>--:--:--</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("SPAWN", key=f"sp_fresh_{db_key}", use_container_width=True):
                        next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                        db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                        push_shared_log("SPAWN", server_name, st.session_state.current_city)
                        st.rerun()
                
                # โซนปุ่ม UNDO / RESET ท้ายการ์ด
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
        st.markdown("### 📡 LIVE ACTION LOG")
        raw_logs = db.reference('shared_action_logs').get() or {}
        log_box_content = ""
        if raw_logs:
            sorted_logs = sorted(raw_logs.values(), key=lambda x: x.get('timestamp', 0), reverse=True)
            for l in sorted_logs:
                if l.get('city') == st.session_state.current_city:
                    action_icon = "🟢" if l['action'] == "SPAWN" else "🔴" if l['action'] == "RESET" else "⏪"
                    log_box_content += f"[{l['time']}] {action_icon} [{l['user']}]\n> {l['action']} {l['server']}\n\n"
                    
        st.text_area("LOG_VIEW", value=log_box_content if log_box_content else "[SYSTEM] RADAR STABLE...", height=520, disabled=True, label_visibility="collapsed")
        if st.button("🔄 REFRESH RADAR TIMERS", use_container_width=True):
            st.rerun()

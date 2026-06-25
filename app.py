import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import json
import os
import tempfile

# 📌 ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง และซ่อน UI ขยะของ Streamlit ทั้งหมด
st.set_page_config(page_title="❖ NYXORAA CLAN RADAR ❖", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= CUSTOM UI THEME (Nyxoraa Style) =================
st.markdown("""
<style>
    /* ซ่อนเมนูระบบที่ไม่จำเป็น */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* โทนสีและฟอนต์หลัก */
    .stApp {
        background-color: #080b12 !important;
        font-family: 'Consolas', 'Segoe UI', monospace !important;
    }
    
    /* แถบด้านซ้าย */
    section[data-testid="stSidebar"] {
        background-color: #0e131f !important;
        border-right: 1px solid #1e293b !important;
    }
    
    h1, h2, h3, p, div {
        color: #e2e8f0;
    }
    
    /* การ์ดเวลากำลังวิ่ง (ขอบแดง Tactical) */
    .boss-card-running {
        background: linear-gradient(145deg, #160a0f 0%, #0c0f17 100%) !important;
        border-top: 3px solid #ff3b3b !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        box-shadow: 0 5px 15px rgba(255, 59, 59, 0.08) !important;
        margin-bottom: 15px !important;
    }
    
    /* การ์ดบอสเกิดแล้ว (ขอบเขียวนีออนกระพริบ) */
    .boss-card-spawned {
        background: linear-gradient(145deg, #091a13 0%, #0c0f17 100%) !important;
        border-top: 3px solid #00ff66 !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.15) !important;
        margin-bottom: 15px !important;
        animation: glow 1.5s infinite alternate;
    }
    
    /* การ์ดสถานะห้องว่าง (ขอบฟ้า) */
    .boss-card-empty {
        background-color: #0f1522 !important;
        border-top: 3px solid #3b82f6 !important;
        border-bottom: 1px solid #1e293b !important;
        border-left: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-radius: 4px !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
    }
    
    /* ช่องกรอกข้อมูลสุดล้ำ */
    .stTextInput input {
        background-color: #080b12 !important;
        color: #00ff66 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 2px !important;
        font-family: monospace !important;
        padding: 10px !important;
    }
    .stTextInput input:focus {
        border-color: #00ff66 !important;
        box-shadow: 0 0 8px rgba(0,255,102,0.3) !important;
    }
    
    /* ปุ่มกดแข็งแรง ดุดัน */
    .stButton>button {
        background-color: #131a28 !important;
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
        box-shadow: 0 0 12px rgba(0, 255, 102, 0.2) !important;
    }
    
    /* ตู้ประวัติ Log */
    div[data-testid="stTextArea"] textarea {
        background-color: #080b12 !important;
        border: 1px solid #1e293b !important;
        color: #94a3b8 !important;
        font-family: 'Consolas', monospace !important;
        border-radius: 2px !important;
    }
    
    @keyframes glow {
        0% { box-shadow: 0 0 10px rgba(0, 255, 102, 0.05); }
        100% { box-shadow: 0 0 20px rgba(0, 255, 102, 0.3); }
    }
</style>
""", unsafe_allow_html=True)

# ================= 100% BUG-FREE FIREBASE INITIALIZATION =================
# แก้ไขคีย์ที่พิมพ์ผิด และใช้ระบบ Tempfile เพื่อให้ Linux อ่านคีย์ได้สมบูรณ์แบบ
FIREBASE_CRED_DICT = {
    "type": "service_account",
    "project_id": "arz-boss-tracker",
    "private_key_id": "b5c18b7ee40e5e05986ab24c745607ee70bc4393",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC5t/H4iq97/8SO\nmT0Sf6P2Q7/Na9QUa4r7PKppUN+eo/qcaK0zQZ8w9SmFKg82WEiQEbIvnmtRrKEJ\ncvCthK+9RtQjmvZXY7XdXPirBD+U9fNUtN2WzjzJJXuLqhG3V4MmnP80r8fsy8Cc\nTnNXk7PhQPMKWzuQGDtrRw0pAzXMkFhjarlJrj3+lHrXvpH1FqkFvodm/LYJID61\nQ2DQX8mrRSHvgjB4kLlURDvOswpwm2rsvsuX2uYTIVte8jWSeuzzJ9UtEaCGdcNX\nLv94JRuMJVsVes1wLca+x4iDC54AeiqTzO/uL0u3hm1aFUhQ6ODV56wo7WojSQnA\nNkLVZFspAgMBAAECggEARy5D3TVWfgmxLdB40mK+lpAv7s1Ru0PewF1nmTbohnam\nApWyMI+Jsqt8bvAIZZVftmw55btruaGXFTaLHY5aBwsjGsR1f1gVp9LO8kkOD4tW\n6JPrzDWeoZ+uowCbirBNcZrBy9FFqLINUDtXRO01B/QrUsBV62wGNh9E4X+7+nt+\nTCNXLtg3faWd95uGhWNP7eJDUKzX05eZlWybUyECFuVq3hyWRqUkPHlO8+ddDL1D\nDu+qUkCqjJ1mgA1bf+nxraM5iZ6YyeUCtmw9zqr+OT2Vb/MUBQYpkc1U1USa5TTK\noRgwrSSa6B/00ZLOcPAw/GTAMWmpPNwfrqwaazC8+wKBgQD0qJMvaUGNu7Q5gt5v\nLQ5BZFwvXwGtL6pO++Q8+u/9+2hxO41dzT/94f/zCe/D20/vZn0cdPF5TD+2y/Od\nnVAKY8yTRRQ9Hl8HhnEvm4s11NQc2YHlTcQv+Goym8gKcCjcMFb/scoHtSwEHdc2\nmf4D7LlkEhG45yXzwdzBLC5zCwKBgQDCU+omgsjJlCs+l8DkVSn6ZNQJBpuzk4QP\ncL5jlJLJXowu8neww6DkHXiuNFAPIl11JxGp0TCbD0DNMEYt833W3olmBvNmwTET\n/U9oemayBC9f0hXnBw+qrfoVF+jX3YM9+Iqf8o3MKan2gIaIL3K4DT8sZuKDnd8n\nG4PtsJ5LGwKBgD9D9EOXUUdIWZNhnwlaukv4msn5JGLXZ4/jHSMTtMmVoG1fe+/c\nqoaJUXlUgXbBGIuMkh+wsdyu9e7cEJQaYN8+7WDLxS8E0ogMoOoxq67w6STIrglQ\nscHB2BxcIj9ov3go2+Zk4BxcIhSybruE2KXFKi+RaJnK1AqTf/VH6n7/AoGBAKYN\nUJsBzJM7kkxVHlW+VDWLbQgdZnTni8Qp4fZzoY6CxSTkudQJBnWGnXW2a+bSxaty\n7AwBHhiRyxzKsF1ZoGE4HY5aSCi40rgzD2TGmvRo0RZ/DYoxpXiCW50kpim3NguB\nUutkNziLLZner5a1fMC7SQ0nCU3QXDwtrekwr8KbAoGBANwycIWBbXGVaG2l/K2a\njWOrA666TRl2SUfQZ2SD74GhdVTVTJm+qdyG0my/L0NJUCnFK1E/+RH/wxAsGOaA\nCznQHFSOrErOHEZ3f+jZ7qv4AdL/hnUleuJatJTUtdhMzZ/F5z5mduiBzzRKf3Hu\nnJ48TKeCjxsI76smBmutnDLJ\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@arz-boss-tracker.iam.gserviceaccount.com",
    "client_id": "116216819259088173761",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40arz-boss-tracker.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

if not firebase_admin._apps:
    try:
        # สร้างไฟล์จำลองเพื่อป้อนข้อมูลให้ Firebase โดยไม่เกิดบัคเครื่องหมาย \n
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, 'w') as f:
            json.dump(FIREBASE_CRED_DICT, f)
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
    except Exception as e:
        st.error(f"❌ CONNECTION ERROR: {e}")

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
def push_shared_log(action, server_name, city):
    now_str = datetime.now().strftime("%H:%M:%S")
    log_id = str(uuid.uuid4())[:8]
    log_data = {
        "id": log_id, "user": st.session_state.user_name, "action": action,
        "city": city, "server": server_name, "time": now_str, "timestamp": datetime.now().timestamp()
    }
    try:
        db.reference(f'shared_action_logs/{log_id}').set(log_data)
        ref = db.reference('shared_action_logs')
        all_logs = ref.get()
        if all_logs and isinstance(all_logs, dict) and len(all_logs) > 150:
            sorted_items = sorted(all_logs.items(), key=lambda x: x[1].get('timestamp', 0))
            for i in range(len(sorted_items) - 150):
                ref.child(sorted_items[i][0]).delete()
    except: pass

# ================= INTERFACE VIEW =================

# 1. หน้าต่างเข้าสู่ระบบ (กรอกแค่ชื่อเท่ๆ พอ)
if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(90deg, #11151e 0%, #161e30 100%); border-left: 4px solid #00ff66; padding: 35px; border-radius: 4px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.5);'>
            <h1 style='color: #00ff66; margin-bottom: 5px; text-shadow: 0 0 15px rgba(0,255,102,0.4); font-size: 32px;'>❖ NYXORAA UPLINK ❖</h1>
            <p style='color: #64748b; font-size: 13px; letter-spacing: 2px;'>IDENTIFICATION REQUIRED TO ACCESS CLAN RADAR</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        input_name = st.text_input("OPERATIVE NAME (ระบุชื่อตัวละคร):", value=st.session_state.user_name)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("[ INITIALIZE CONNECTION ]", use_container_width=True):
            if not input_name.strip():
                st.error("⚠️ ACCESS DENIED: กรุณาระบุชื่อตัวละครก่อนเข้าใช้งาน!")
            else:
                st.session_state.authenticated = True
                st.session_state.user_name = input_name.strip()
                st.rerun()

# 2. หน้าจอกระดานเรดาร์บอส
else:
    with st.sidebar:
        st.markdown(f"""
        <div style='background-color: #0b0f19; border: 1px solid #00ff66; padding: 15px; border-radius: 4px; text-align: center; box-shadow: inset 0 0 15px rgba(0,255,102,0.08); margin-bottom: 20px;'>
            <span style='color: #64748b; font-size: 11px; letter-spacing: 1px;'>ACTIVE OPERATIVE</span><br>
            <strong style='color: #00ff66; font-size: 20px; text-transform: uppercase;'>{st.session_state.user_name}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state.current_type = st.radio("📡 NETWORK ALIGNMENT:", ["Official", "Premium"])
        st.markdown("<hr style='border-color: #1e293b; margin: 15px 0;'>", unsafe_allow_html=True)
        
        st.markdown("<span style='color: #94a3b8; font-size: 14px;'>🎯 <b>SELECT SECTOR:</b></span>", unsafe_allow_html=True)
        for city_name, icon in CITIES.items():
            if st.button(f"{icon}  {city_name}", use_container_width=True):
                st.session_state.current_city = city_name
                st.rerun()
                
        st.markdown("<hr style='border-color: #1e293b; margin: 25px 0 15px 0;'>", unsafe_allow_html=True)
        if st.button("🔌 DISCONNECT", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown(f"<h2>📍 <span style='color: #64748b;'>SECTOR:</span> <span style='color: #00ff66; text-shadow: 0 0 10px rgba(0,255,102,0.3);'>{st.session_state.current_city.upper()}</span> <span style='font-size: 15px; color: #3b82f6;'>[{st.session_state.current_type.upper()}]</span></h2>", unsafe_allow_html=True)
    
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
                                <div style='font-size: 11px; color: #64748b; margin-bottom: 5px;'>{server_name}</div>
                                <div style='font-size: 26px; font-weight: bold; color: #ff3b3b; text-shadow: 0 0 10px rgba(255,59,59,0.5);'>{hours:02d}:{mins:02d}:{secs:02d}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.button("SPAWN", key=f"sp_{db_key}", disabled=True, use_container_width=True)
                        else:
                            st.markdown(f"""
                            <div class='boss-card-spawned'>
                                <div style='font-size: 11px; color: #00ff66; margin-bottom: 5px;'>{server_name}</div>
                                <div style='font-size: 22px; font-weight: bold; color: #00ff66; text-shadow: 0 0 12px rgba(0,255,102,0.8);'>[ SPAWNED ]</div>
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
                        <div style='font-size: 11px; color: #475569; margin-bottom: 5px;'>{server_name}</div>
                        <div style='font-size: 26px; font-weight: bold; color: #3b82f6;'>--:--:--</div>
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
        st.markdown("""
        <div style='border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 15px;'>
            <h3 style='font-size: 15px; color: #94a3b8; margin: 0;'>>_ LIVE TERMINAL</h3>
        </div>
        """, unsafe_allow_html=True)
        
        raw_logs = db.reference('shared_action_logs').get() or {}
        log_box_content = ""
        if raw_logs and isinstance(raw_logs, dict):
            sorted_logs = sorted(raw_logs.values(), key=lambda x: x.get('timestamp', 0), reverse=True)
            for l in sorted_logs:
                if l.get('city') == st.session_state.current_city:
                    action_icon = "🟢" if l['action'] == "SPAWN" else "🔴" if l['action'] == "RESET" else "⏪"
                    log_box_content += f"[{l['time']}] {action_icon} [{l['user']}]\n> {l['action']} {l['server']}\n\n"
                    
        st.text_area("LOG_VIEW", value=log_box_content if log_box_content else "[SYSTEM] RADAR ONLINE...", height=620, disabled=True, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 REFRESH UPLINK", use_container_width=True):
            st.rerun()

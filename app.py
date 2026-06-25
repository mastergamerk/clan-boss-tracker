import streamlit as st
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
import uuid
import random
import urllib.request
import urllib.parse
import os
import json

# 📌 ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง (Wide Mode) และธีมดาร์ก
st.set_page_config(page_title="CHECK TIMER BOSS PIRIYA", layout="wide", initial_sidebar_state="expanded")

COOLDOWN_SECONDS = 3600
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxLuBcnupdwj1ippurn9t18kE5pnGucV4Q-CTBr9f7vLApYa_NhwncLTH6FRmJI24u0lw/exec"
DATABASE_URL = "https://arz-boss-tracker-default-rtdb.firebaseio.com/"

# ================= SYSTEM INITIALIZATION =================
# สำหรับระบบเว็บ เราจะอ่าน Firebase Key ผ่าน Streamlit Secrets เพื่อความปลอดภัย (ไม่ให้คนอื่นเห็นไฟล์ JSON)
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            # ใช้ข้อมูลจาก Secrets บนระบบ Cloud
            fb_cred = dict(st.secrets["firebase"])
            cred = credentials.Certificate(fb_cred)
        else:
            # ใช้ไฟล์โลคอลสำหรับทดสอบในเครื่องคอมตัวเอง
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

# กำหนดค่าตัวแปรประจำ Session ของผู้ใช้งานเว็บแต่ละคน
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "current_type" not in st.session_state: st.session_state.current_type = "Official"
if "current_city" not in st.session_state: st.session_state.current_city = list(CITIES.keys())[0]

# ฟังก์ชันดึง HWID/จำลอง ID สำหรับระบบเว็บ (เว็บบราวเซอร์จะไม่มีสิทธิ์อ่านค่าเครื่องตรงๆ จึงต้องใช้ระบบจำลอง Session ID)
if "browser_id" not in st.session_state:
    st.session_state.browser_id = str(uuid.getnode())

# ================= HELPER FUNCTIONS =================
def verify_key(key):
    try:
        url = f"{GOOGLE_SHEET_WEBAPP_URL}?key={urllib.parse.quote(key)}&hwid={urllib.parse.quote(st.session_state.browser_id)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            result = response.read().decode('utf-8').strip()
            return result == "APPROVED"
    except:
        return False

def push_shared_log(action, server_name, city):
    now_str = datetime.now().strftime("%H:%M:%S")
    log_id = str(uuid.uuid4())[:8]
    log_data = {
        "id": log_id,
        "user": st.session_state.user_name,
        "action": action,
        "city": city,
        "server": server_name,
        "time": now_str,
        "timestamp": datetime.now().timestamp()
    }
    try:
        db.reference(f'shared_action_logs/{log_id}').set(log_data)
    except: pass

# ================= UI INTERFACE =================

# 1. หน้าจอตรวจเช็ค LICENSE KEY
if not st.session_state.authenticated:
    st.title("❖ ANTI-LEAK SECURITY SYSTEM ❖")
    st.write("ENTER YOUR LICENSE KEY TO ACCESS THE CLAN RADAR")
    
    input_name = st.text_input("ชื่อตัวละครของคุณ:", value=st.session_state.user_name)
    input_key = st.text_input("รหัสคีย์คุมระบบ:", type="password")
    
    if st.button("[ ACTIVATE LICENSE ]"):
        if input_name.strip() == "":
            st.error("กรุณากรอกชื่อตัวละครก่อนเข้าใช้งาน!")
        else:
            with st.spinner("กำลังยืนยันสิทธิ์จากเซิร์ฟเวอร์หลัก..."):
                if verify_key(input_key):
                    st.session_state.authenticated = True
                    st.session_state.user_name = input_name.strip()
                    st.success("ยืนยันสิทธิ์สำเร็จ!")
                    st.rerun()
                else:
                    st.error("รหัสคีย์ไม่ถูกต้อง หรือถูกระงับสิทธิ์ใช้งานแล้ว!")

# 2. หน้าจอหลักของโปรแกรม (เมื่อยืนยันสิทธิ์ผ่านแล้ว)
else:
    # ส่วนของแถบเมนูด้านซ้าย (Sidebar)
    with st.sidebar:
        st.markdown(f"### 👤 OPERATIVE: `{st.session_state.user_name}` 🟢")
        st.markdown("---")
        
        # เลือกประเภทเซิร์ฟเวอร์
        st.session_state.current_type = st.radio("NETWORK TYPE:", ["Official", "Premium"])
        st.markdown("---")
        
        # เลือกเมืองเป้าหมาย
        st.markdown("🎯 **SELECT TARGET CITY:**")
        for city_name, icon in CITIES.items():
            if st.button(f"{icon} {city_name}", use_container_width=True):
                st.session_state.current_city = city_name
                st.rerun()
                
        st.markdown("---")
        if st.button("🚪 LOGOUT / SWITCH CHAR"):
            st.session_state.authenticated = False
            st.rerun()

    # พื้นที่กระดานหลัก (Main Dashboard)
    st.title(f"📍 TARGET: {st.session_state.current_city.upper()} ({st.session_state.current_type.upper()})")
    
    # ดึงเวลาปัจจุบันมาเปรียบเทียบ
    now = datetime.now()
    
    # ดึงข้อมูลตัวนับเวลาทั้งหมดจาก Firebase แบบ Real-time ทุกครั้งที่หน้าเว็บรีเฟรช
    timers_data = db.reference('boss_timers').get() or {}
    backup_data = db.reference('backup_timers').get() or {}
    
    # ดึงคลังข้อมูลส่วนกลางมาจัดแสดงในตู้ Live Log Side
    col_cards, col_logs = st.columns([3, 1])
    
    with col_cards:
        # วาดการ์ดเซิร์ฟเวอร์ 4 คอลัมน์แบบ Grid เหมือนแอปเดิม
        srv_list = SERVERS[st.session_state.current_type]
        grid_cols = st.columns(4)
        
        for idx, server_name in enumerate(srv_list):
            col_target = grid_cols[idx % 4]
            db_key = f"{st.session_state.current_type}_{st.session_state.current_city}_{server_name}"
            
            with col_target:
                st.markdown(f"#### 🖥️ {server_name}")
                
                # ตรรกะคำนวณเวลานับถอยหลัง
                if db_key in timers_data:
                    try:
                        spawn_time = datetime.strptime(timers_data[db_key], "%Y-%m-%d %H:%M:%S")
                        total_secs = (spawn_time - now).total_seconds()
                        
                        if total_secs > 0:
                            hours, remainder = divmod(int(total_secs), 3600)
                            mins, secs = divmod(remainder, 60)
                            st.error(f"⏱️ {hours:02d}:{mins:02d}:{secs:02d}")
                            
                            # ปุ่มล็อกห้ามกดทับจนกว่าเวลาจะหมด
                            st.button("SPAWN", key=f"sp_{db_key}", disabled=True, use_container_width=True)
                        else:
                            st.success("💀 [ SPAWNED ]")
                            if st.button("SPAWN", key=f"sp_act_{db_key}", use_container_width=True):
                                next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                                db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                                push_shared_log("SPAWN", server_name, st.session_state.current_city)
                                st.rerun()
                    except:
                        st.info("--:--:--")
                else:
                    st.info("⏱️ --:--:--")
                    if st.button("SPAWN", key=f"sp_fresh_{db_key}", use_container_width=True):
                        next_spawn = now + timedelta(seconds=COOLDOWN_SECONDS)
                        db.reference(f'boss_timers/{db_key}').set(next_spawn.strftime("%Y-%m-%d %H:%M:%S"))
                        push_shared_log("SPAWN", server_name, st.session_state.current_city)
                        st.rerun()
                
                # ปุ่มฟังก์ชันจัดการเสริมด้านล่างของการ์ด (UNDO / RESET)
                c_undo, col_rst = st.columns(2)
                with c_undo:
                    # ตรวจสอบสิทธิ์การกด Undo 10 นาที
                    has_backup = db.reference(f'backup_timers/{db_key}').get()
                    if has_backup:
                        if st.button("UNDO", key=f"un_{db_key}", use_container_width=True):
                            db.reference(f'boss_timers/{db_key}').set(has_backup["spawn_time"])
                            db.reference(f'backup_timers/{db_key}').delete()
                            push_shared_log("UNDO", server_name, st.session_state.current_city)
                            st.rerun()
                    else:
                        st.button("UNDO", key=f"un_dis_{db_key}", disabled=True, use_container_width=True)
                        
                with col_rst:
                    if db_key in timers_data:
                        if st.button("RESET", key=f"rs_{db_key}", use_container_width=True):
                            db.reference(f'backup_timers/{db_key}').set({"spawn_time": timers_data[db_key], "deleted_at": now.strftime("%Y-%m-%d %H:%M:%S")})
                            db.reference(f'boss_timers/{db_key}').delete()
                            push_shared_log("RESET", server_name, st.session_state.current_city)
                            st.rerun()
                    else:
                        st.button("RESET", key=f"rs_dis_{db_key}", disabled=True, use_container_width=True)
                st.markdown("---")

    # ส่วนของตู้แสดงข้อมูลประวัติสากล (Live Action Log) ด้านขวา
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
                    
        st.text_area("LOG_VIEW", value=log_box_content if log_box_content else "[SYSTEM] READY...", height=500, disabled=True, label_visibility="collapsed")
        
        # ปุ่มสำหรับบังคับรีเฟรชหน้าจออัปเดตเวลาบนเว็บด้วยมือ
        if st.button("🔄 REFRESH RADAR", use_container_width=True):
            st.rerun()
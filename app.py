import streamlit as st
import sqlite3
import os
import datetime
import time
import pandas as pd
import io
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="STAFF6 COMMAND CENTER", layout="wide")

UPLOAD_DIR = "uploads"
DB_DIR = "database"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# ================= LOGIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "login" not in st.session_state:
    st.session_state["login"] = False

# ================= UNITS =================
UNITS = ["พล.1 รอ.", "พล.ร.2 รอ.", "พล.ม.2 รอ.", "กรม ทย.รอ.อย."]

# ================= STATUS =================
STATUS = [
    "ยังไม่ดำเนินการ 🔴",
    "กำลังดำเนินการ 🟡",
    "เสร็จสิ้น 🟢"
]

# ================= NORMALIZE =================
def norm(s):
    if not s:
        return "ยังไม่ดำเนินการ 🔴"

    s = str(s)
    if "เสร็จ" in s:
        return "เสร็จสิ้น 🟢"
    if "ดำเนิน" in s:
        return "กำลังดำเนินการ 🟡"

    return "ยังไม่ดำเนินการ 🔴"

# ================= DB =================
def safe(u):
    return u.replace(" ", "_").replace(".", "")

def db_path(unit):
    folder = os.path.join(DB_DIR, safe(unit))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "data.db")

def connect(unit):
    conn = sqlite3.connect(db_path(unit), check_same_thread=False)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit TEXT,
        task TEXT,
        detail TEXT,
        progress INTEGER,
        status TEXT,
        problem TEXT,
        images TEXT,
        report_date TEXT,
        time TEXT
    )
    """)

    conn.commit()
    return conn, c

# ================= USER =================
def user_app():

    st.title("📌 พื้นที่สำหรับหน่วยรายงาน")

    unit = st.selectbox("เลือกหน่วย", UNITS)
    conn, c = connect(unit)

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")
    progress = st.number_input("ความคืบหน้า (%)", 0, 100)
    status = st.selectbox("สถานะ", STATUS)
    problem = st.text_area("ปัญหา")

    files = st.file_uploader("📸 แนบรูป", accept_multiple_files=True)

    images = []

    if files:
        for f in files:
            name = f"{time.time()}_{f.name}"
            path = os.path.join(UPLOAD_DIR, name)
            with open(path, "wb") as w:
                w.write(f.getbuffer())
            images.append(path)

    if st.button("📤 ส่งรายงาน"):

        c.execute("""
        INSERT INTO reports VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            unit, task, detail, progress,
            norm(status), problem,
            ",".join(images),
            str(datetime.date.today()),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# ================= LOAD ALL =================
def load_all():

    data = []

    for u in UNITS:
        conn, c = connect(u)
        rows = c.execute("SELECT * FROM reports").fetchall()

        for r in rows:
            r = list(r)
            r[5] = norm(r[5])
            data.append(r)

    return data

# ================= DELETE =================
def delete(unit, rid):
    conn, c = connect(unit)
    c.execute("DELETE FROM reports WHERE id=?", (rid,))
    conn.commit()

# ================= ADMIN =================
def admin_app():

    st.title("🚨 STAFF6 COMMAND CENTER")

    # ================= FILTER PANEL =================
    with st.sidebar:
        st.markdown("## CONTROL PANEL")

        if st.button("🚪 Logout"):
            st.session_state["login"] = False
            st.rerun()

        unit_filter = st.selectbox("📌 หน่วย", ["ทั้งหมด"] + UNITS)

        from_date = st.date_input("📅 จากวันที่", datetime.date.today())
        to_date = st.date_input("📅 ถึงวันที่", datetime.date.today())

    data = load_all()

    # ================= FILTER =================
    filtered = []

    for d in data:
        try:
            d_date = datetime.datetime.strptime(d[8], "%Y-%m-%d").date()
        except:
            continue

        if unit_filter != "ทั้งหมด" and d[1] != unit_filter:
            continue

        if not (from_date <= d_date <= to_date):
            continue

        filtered.append(d)

    # ================= KPI =================
    st.subheader("📊 KPI")

    status_list = [norm(x[5]) for x in filtered]

    total = len(status_list)
    todo = status_list.count("ยังไม่ดำเนินการ 🔴")
    doing = status_list.count("กำลังดำเนินการ 🟡")
    done = status_list.count("เสร็จสิ้น 🟢")

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 ทั้งหมด", total)
    c2.metric("🟡 ดำเนินการ", doing)
    c3.metric("🟢 เสร็จสิ้น", done)

    st.markdown("---")

    # ================= REPORT (FULL DETAIL + IMAGE) =================
    st.subheader("📄 รายงานทั้งหมด")

    for d in filtered:

        col1, col2 = st.columns([3, 1])

        with col1:

            st.markdown(f"""
### 🏷 {d[1]} | {d[2]} | {norm(d[5])}

📄 {d[3]}  

📊 Progress: {d[4]}%  
⚠️ ปัญหา: {d[6]}  
📅 วันที่: {d[8]}  
""")

            if d[7]:
                imgs = d[7].split(",")

                img_cols = st.columns(min(len(imgs), 3))

                for i, img in enumerate(imgs):
                    if os.path.exists(img):
                        img_cols[i % 3].image(img, use_container_width=True)

        with col2:
            if st.button("🗑 ลบ", key=f"del_{d[0]}"):
                delete(d[1], d[0])
                st.rerun()

    # ================= RAW DATA =================
    st.markdown("---")
    st.subheader("🧠 RAW DATABASE")

    df = pd.DataFrame(filtered, columns=[
        "ID","หน่วย","งาน","รายละเอียด","%","สถานะ",
        "ปัญหา","รูป","วันที่","เวลา"
    ])

    st.dataframe(df, use_container_width=True)

# ================= LOGIN =================
def login_page():

    st.title("🔐 STAFF6 LOGIN")

    u = st.text_input("User")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("Login ไม่ถูกต้อง")

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

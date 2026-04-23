import streamlit as st
import sqlite3
import os
import datetime
import time
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="COMMAND CENTER", layout="wide")

UPLOAD_DIR = "uploads"
DB_DIR = "database"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# ================= LOGIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "login" not in st.session_state:
    st.session_state["login"] = False

# ================= UNIT (มีจุดได้) =================
UNITS = [
    "พล.1 รอ.",
    "พล.ร.2 รอ.",
    "พล.ม.2 รอ.",
    "กรม ทย.รอ.อย."
]

STATUS = ["ค้าง 🔴", "กำลังดำเนินการ 🟡", "เสร็จสิ้น 🟢"]

# ================= SAFE NAME =================
def safe_unit(unit):
    return unit.replace(" ", "_").replace(".", "")

# ================= DB PATH =================
def get_db_path(unit):
    folder = os.path.join(DB_DIR, safe_unit(unit))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "reports.db")

# ================= DB CONNECT =================
def connect_db(unit):
    conn = sqlite3.connect(get_db_path(unit), check_same_thread=False)
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

    conn, c = connect_db(unit)

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")
    progress = st.number_input("ความคืบหน้า (%)", 0, 100)
    status = st.selectbox("สถานะ", STATUS)
    problem = st.text_area("ปัญหา")

    # ================= 📸 UPLOAD =================
    files = st.file_uploader("แนบรูป", accept_multiple_files=True)

    images = []

    if files:
        for f in files:
            filename = f"{time.time()}_{f.name}"
            path = os.path.join(UPLOAD_DIR, filename)

            with open(path, "wb") as w:
                w.write(f.getbuffer())

            images.append(path)

    # ================= SAVE =================
    if st.button("ส่งรายงาน"):

        c.execute("""
        INSERT INTO reports VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            unit, task, detail, progress,
            status, problem,
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
        conn, c = connect_db(u)
        rows = c.execute("SELECT * FROM reports").fetchall()
        data.extend(rows)

    return data

# ================= DELETE =================
def delete(unit, rid):
    conn, c = connect_db(unit)
    c.execute("DELETE FROM reports WHERE id=?", (rid,))
    conn.commit()

# ================= ADMIN =================
def admin_app():

    st.title("🚨 กกร.ฉก.ทม.รอ.904 COMMAND CENTER")

    data = load_all()

    unit_filter = st.selectbox("เลือกหน่วย", ["ทั้งหมด"] + UNITS)

    filtered = []

    for d in data:
        if unit_filter == "ทั้งหมด" or d[1] == unit_filter:
            filtered.append(d)

    # ================= KPI =================
    st.subheader("📊 KPI")

    total = len(filtered)
    done = len([x for x in filtered if x[5] == "เสร็จสิ้น 🟢"])

    c1, c2 = st.columns(2)
    c1.metric("ทั้งหมด", total)
    c2.metric("เสร็จสิ้น", done)

    st.markdown("---")

    # ================= REPORT =================
    st.subheader("📄 รายงาน")

    for d in filtered:

        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"**{d[1]} | {d[2]} | {d[5]}**")
            st.write(d[3])
            st.write("📅", d[8])

            # 📸 SHOW IMAGES
            if d[7]:
                imgs = d[7].split(",")
                for img in imgs:
                    if os.path.exists(img):
                        st.image(img, width=250)

        with col2:
            if st.button("🗑 ลบ", key=f"del_{d[0]}"):
                delete(d[1], d[0])
                st.rerun()

    st.markdown("---")

    # ================= DATABASE VIEW =================
    st.subheader("🧠 DATABASE VIEW")

    df = pd.DataFrame(filtered, columns=[
        "ID","หน่วย","งาน","รายละเอียด","%","สถานะ",
        "ปัญหา","รูป","วันที่","เวลา"
    ])

    st.dataframe(df, use_container_width=True)

# ================= LOGIN =================
def login_page():

    st.title("🔐 ADMIN LOGIN")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("ผิด")

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

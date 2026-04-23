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
st.set_page_config(page_title="WAR ROOM COMMAND CENTER", layout="wide")

UPLOAD_DIR = "uploads"
DB_DIR = "database"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# ================= LOGIN =================
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

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

# ================= NORMALIZE (กัน KPI พัง 100%) =================
def norm(s):
    if not s:
        return "ยังไม่ดำเนินการ 🔴"

    s = str(s)

    if "เสร็จ" in s or "done" in s.lower():
        return "เสร็จสิ้น 🟢"
    if "ดำเนิน" in s or "progress" in s.lower():
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

# ================= LOAD =================
def load_all():

    data = []

    for u in UNITS:
        conn, c = connect(u)
        rows = c.execute("SELECT * FROM reports").fetchall()

        for r in rows:
            r = list(r)
            r[5] = norm(r[5])   # 🔥 FIX KPI ทุก record
            data.append(r)

    return data

# ================= DELETE =================
def delete(unit, rid):
    conn, c = connect(unit)
    c.execute("DELETE FROM reports WHERE id=?", (rid,))
    conn.commit()

# ================= EXPORT PPT (16:9) =================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    status_count = {
        "ยังไม่ดำเนินการ 🔴": 0,
        "กำลังดำเนินการ 🟡": 0,
        "เสร็จสิ้น 🟢": 0
    }

    for d in data:
        status_count[norm(d[5])] += 1

    # GRAPH
    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    plt.tight_layout()
    plt.savefig("bar.png")
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    plt.savefig("pie.png")
    plt.close()

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "WAR ROOM SUMMARY"

    slide.shapes.add_textbox(
        Inches(0.5), Inches(1), Inches(6), Inches(3)
    ).text = f"""
TOTAL: {len(data)}
🔴 ยังไม่ดำเนินการ: {status_count['ยังไม่ดำเนินการ 🔴']}
🟡 กำลังดำเนินการ: {status_count['กำลังดำเนินการ 🟡']}
🟢 เสร็จสิ้น: {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_picture("bar.png", Inches(6), Inches(1), width=Inches(3))
    slide.shapes.add_picture("pie.png", Inches(6), Inches(4), width=Inches(3))

    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"{d[1]} | {d[2]}"

        text = f"""
หน่วย: {d[1]}
งาน: {d[2]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {norm(d[5])}
ปัญหา: {d[6]}
วันที่: {d[8]}
"""

        slide.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(6), Inches(4)
        ).text = text

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

# ================= ADMIN =================
def admin_app():

    st.title("🚨 WAR ROOM COMMAND CENTER")

    with st.sidebar:
        st.markdown("## CONTROL")

        if st.button("🚪 Logout"):
            st.session_state["login"] = False
            st.rerun()

        unit_filter = st.selectbox("หน่วย", ["ทั้งหมด"] + UNITS)

    data = load_all()

    if unit_filter != "ทั้งหมด":
        data = [d for d in data if d[1] == unit_filter]

    # ================= KPI =================
    st.subheader("📊 KPI")

    total = len(data)
    doing = len([x for x in data if norm(x[5]) == "กำลังดำเนินการ 🟡"])
    done = len([x for x in data if norm(x[5]) == "เสร็จสิ้น 🟢"])
    todo = len([x for x in data if norm(x[5]) == "ยังไม่ดำเนินการ 🔴"])

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 ทั้งหมด", total)
    c2.metric("🟡 กำลังดำเนินการ", doing)
    c3.metric("🟢 เสร็จสิ้น", done)

    st.markdown("---")

    # ================= REPORT =================
    st.subheader("📄 REPORT")

    for d in data:

        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"**{d[1]} | {d[2]} | {norm(d[5])}**")
            st.write(d[3])
            st.write("📅", d[8])

        with col2:
            if st.button("🗑 ลบ", key=f"del_{d[0]}"):
                delete(d[1], d[0])
                st.rerun()

    # ================= EXPORT =================
    st.markdown("---")

    if st.button("📤 EXPORT PPTX 16:9"):

        ppt = export_ppt(data)

        st.download_button(
            "📥 ดาวน์โหลด PPT",
            ppt,
            file_name="WAR_ROOM.pptx"
        )

    # ================= DB VIEW =================
    st.markdown("---")
    st.subheader("🧠 DATABASE VIEW")

    df = pd.DataFrame(data, columns=[
        "ID","หน่วย","งาน","รายละเอียด","%","สถานะ",
        "ปัญหา","รูป","วันที่","เวลา"
    ])

    st.dataframe(df, use_container_width=True)

# ================= LOGIN =================
def login_page():

    st.title("🔐 LOGIN")

    u = st.text_input("User")
    p = st.text_input("Pass", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("ไม่ถูกต้อง")

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

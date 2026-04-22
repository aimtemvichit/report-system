import streamlit as st
import sqlite3
import datetime
import time
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("reports.db", check_same_thread=False)
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
    time TEXT
)
""")
conn.commit()

# ================= HIDE SIDEBAR =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ================= ADMIN LOGIN =================
ADMIN_USER = "kgr"
ADMIN_PASS = "1234"

if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

# =====================================================
# 🔵 USER MODE (NO LOGIN)
# =====================================================
def user_app():

    st.title("📌 ระบบรายงานหน่วย (Field Report)")

    st.info("👷 โหมดหน่วย: กรอกข้อมูลได้ทันที")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    task = st.text_input("งาน/ภารกิจ")
    detail = st.text_area("รายละเอียดงาน")

    progress = st.slider("ความคืบหน้า (%)", 0, 100, 0)

    status = st.selectbox("สถานะ", [
        "ค้าง",
        "กำลังดำเนินการ",
        "เสร็จสิ้น"
    ])

    problem = st.text_area("⚠️ ปัญหา / ข้อขัดข้อง")

    if st.button("📤 ส่งรายงาน"):

        c.execute("""
            INSERT INTO reports (unit, task, detail, progress, status, problem, time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            unit, task, detail, progress, status, problem,
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# =====================================================
# 🔴 ADMIN LOGIN PAGE
# =====================================================
def admin_login_page():

    st.title("🔐 กกร. Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):

        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.admin_login = True
            st.rerun()
        else:
            st.error("รหัสไม่ถูกต้อง")

# =====================================================
# 🔴 ADMIN DASHBOARD (REAL TIME + FULL CONTROL)
# =====================================================
def admin_app():

    st.title("📊 กกร. Command Center (Real-Time)")

    data = c.session_state = None  # กัน cache
    data = c.execute("SELECT * FROM reports").fetchall()

    # ================= SUMMARY =================
    st.metric("จำนวนรายงานทั้งหมด", len(data))

    # ================= GROUP BY UNIT =================
    st.subheader("📌 ภาพรวมแยกตามหน่วย")

    unit_count = {}

    for d in data:
        unit_count[d[1]] = unit_count.get(d[1], 0) + 1

    st.bar_chart(unit_count)

    # ================= FILTER BY UNIT =================
    st.subheader("🔍 รายงานแยกตามหน่วย")

    if unit_count:
        selected_unit = st.selectbox("เลือกหน่วย", list(unit_count.keys()))

        filtered = [d for d in data if d[1] == selected_unit]

        for d in filtered:
            st.write("---")
            st.write("งาน:", d[2])
            st.write("รายละเอียด:", d[3])
            st.write("ความคืบหน้า:", d[4], "%")
            st.write("สถานะ:", d[5])
            st.write("ปัญหา:", d[6])

    # ================= AUTO REFRESH =================
    st.caption("🔄 ระบบ real-time (auto refresh)")

    time.sleep(2)
    st.rerun()

    # ================= EXPORT =================
    st.subheader("📑 Export PowerPoint")

    if st.button("สร้าง PPT"):

        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        for d in data:

            slide = prs.slides.add_slide(prs.slide_layouts[5])
            slide.shapes.title.text = d[2]

            txt = f"""
หน่วย: {d[1]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
ปัญหา: {d[6]}
"""

            slide.shapes.add_textbox(
                Inches(1), Inches(1.5),
                Inches(8), Inches(4)
            ).text = txt

        prs.save("report.pptx")
        st.success("Export สำเร็จ")

# =====================================================
# 🔥 ROUTER
# =====================================================

# ADMIN FLOW
if st.session_state.admin_login:
    admin_app()

else:
    # ถ้าไม่ใช่ admin → เข้า login หรือ user
    mode = st.query_params.get("mode", "user")

    if isinstance(mode, list):
        mode = mode[0]

    if mode == "admin":
        admin_login_page()
    else:
        user_app()

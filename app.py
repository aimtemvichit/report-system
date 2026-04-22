import streamlit as st
import sqlite3
import datetime
import time
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= ADMIN LOGIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

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

# ================= UI CLEAN =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 👷 USER MODE (NO LOGIN)
# =====================================================
def user_app():

    st.title("📌 ระบบรายงานหน่วย")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    task = st.text_input("งาน/ภารกิจ")
    detail = st.text_area("รายละเอียด")

    # 🔥 number input (ตามที่ต้องการ)
    progress = st.number_input("ความคืบหน้า (%)", 0, 100, step=1)

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
# 🔐 ADMIN LOGIN
# =====================================================
def admin_login():

    st.title("🔐 กกร. Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):

        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.admin_login = True
            st.rerun()
        else:
            st.error("Username หรือ Password ไม่ถูกต้อง")

# =====================================================
# 📊 REAL-TIME ADMIN DASHBOARD
# =====================================================
def admin_app():

    st.title("📊 กกร. Command Center (Real-Time)")

    placeholder = st.empty()

    while True:

        with placeholder.container():

            data = c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

            # ================= SUMMARY =================
            st.metric("จำนวนรายงานทั้งหมด", len(data))

            # ================= BY UNIT =================
            st.subheader("📌 สถานะรายหน่วย")

            unit_map = {}
            for d in data:
                unit_map[d[1]] = unit_map.get(d[1], 0) + 1

            st.bar_chart(unit_map)

            # ================= FILTER BY UNIT =================
            st.subheader("🔍 รายงานล่าสุด (10 รายการ)")

            for d in data[:10]:

                st.write("---")
                st.write("หน่วย:", d[1])
                st.write("งาน:", d[2])
                st.write("ความคืบหน้า:", d[4], "%")
                st.write("สถานะ:", d[5])
                st.write("ปัญหา:", d[6])

            st.caption("🔄 อัปเดตอัตโนมัติทุก 3 วินาที")

        time.sleep(3)

# =====================================================
# 📑 EXPORT POWERPOINT (16:9 + DATE RANGE)
# =====================================================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Summary
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Executive Summary"

    slide.shapes.add_textbox(
        Inches(1), Inches(1.5),
        Inches(10), Inches(4)
    ).text = f"จำนวนรายการ: {len(data)}"

    # Details
    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = d[2]

        txt = f"""
หน่วย: {d[1]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
ปัญหา: {d[6]}
เวลา: {d[7]}
"""

        slide.shapes.add_textbox(
            Inches(1), Inches(1.5),
            Inches(10), Inches(4)
        ).text = txt

    prs.save("report.pptx")
    st.success("Export สำเร็จ")

# =====================================================
# 🔐 ADMIN PAGE (LOGIN + CONTROL)
# =====================================================
def admin_page():

    st.title("📊 กกร. Control Panel")

    data = c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

    # ================= DATE FILTER =================
    st.subheader("📅 เลือกช่วงวันที่ Export")

    col1, col2 = st.columns(2)

    with col1:
        from_date = st.date_input("From")

    with col2:
        to_date = st.date_input("To")

    filtered = []

    for d in data:
        try:
            t = datetime.datetime.fromisoformat(d[7]).date()
            if from_date <= t <= to_date:
                filtered.append(d)
        except:
            pass

    st.metric("รายการในช่วง", len(filtered))

    st.subheader("📄 ข้อมูลดิบ")

    st.dataframe(filtered)

    if st.button("📑 Export PowerPoint"):

        export_ppt(filtered)

# =====================================================
# 🔥 ROUTER
# =====================================================
if st.session_state.admin_login:
    admin_page()
else:
    admin_login()
    user_app()

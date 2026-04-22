import streamlit as st
import sqlite3
import datetime
import time
import os
import io
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= ADMIN LOGIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

# ================= IMAGE STORAGE =================
UPLOAD_DIR = r"C:\Users\WICHIT_AIMTEM\OneDrive\เดสก์ท็อป\report-system\uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    images TEXT,
    time TEXT
)
""")
conn.commit()

# ================= STATUS STYLE =================
STATUS_OPTIONS = [
    "ค้าง 🔴",
    "กำลังดำเนินการ 🟡",
    "เสร็จสิ้น 🟢"
]

# ================= UI CLEAN =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 👷 USER MODE
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

    progress = st.number_input("ความคืบหน้า (%)", 0, 100, step=1)

    status = st.selectbox("สถานะ", STATUS_OPTIONS)

    problem = st.text_area("⚠️ ปัญหา / ข้อขัดข้อง")

    # ================= IMAGE UPLOAD =================
    files = st.file_uploader("📷 แนบรูป (หลายรูปได้)", accept_multiple_files=True)

    image_paths = []

    if files:
        for f in files:
            file_path = os.path.join(UPLOAD_DIR, f.name)
            with open(file_path, "wb") as out:
                out.write(f.getbuffer())
            image_paths.append(file_path)

    # ================= SUBMIT =================
    if st.button("📤 ส่งรายงาน"):

        c.execute("""
            INSERT INTO reports (unit, task, detail, progress, status, problem, images, time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unit, task, detail, progress, status, problem,
            ",".join(image_paths),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# =====================================================
# 🔐 LOGIN
# =====================================================
def login_page():

    st.title("🔐 กกร. Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):

        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.admin_login = True
            st.rerun()
        else:
            st.error("Login ไม่ถูกต้อง")

# =====================================================
# 📑 EXPORT POWERPOINT
# =====================================================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # summary
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Executive Summary"

    slide.shapes.add_textbox(
        Inches(1), Inches(1.5),
        Inches(10), Inches(4)
    ).text = f"จำนวนรายการ: {len(data)}"

    # details
    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = d[2]

        text = f"""
หน่วย: {d[1]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
ปัญหา: {d[6]}
เวลา: {d[8]}
"""

        slide.shapes.add_textbox(
            Inches(0.8), Inches(1.2),
            Inches(6), Inches(4)
        ).text = text

        # images
        if d[7]:
            imgs = d[7].split(",")
            x = 7
            y = 1.2

            for img in imgs[:2]:
                if os.path.exists(img):
                    slide.shapes.add_picture(img, Inches(x), Inches(y), width=Inches(2))
                    y += 2

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)

    st.download_button(
        "📥 ดาวน์โหลด PowerPoint",
        output,
        file_name="report.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# =====================================================
# 🧠 ADMIN DASHBOARD (REAL TIME + EXPORT)
# =====================================================
def admin_app():

    st.title("📊 กกร. Command Center (Real-Time)")

    placeholder = st.empty()

    while True:

        with placeholder.container():

            data = c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

            st.metric("จำนวนรายงานทั้งหมด", len(data))

            # chart
            st.subheader("📌 ภาพรวมรายหน่วย")

            unit_map = {}
            for d in data:
                unit_map[d[1]] = unit_map.get(d[1], 0) + 1

            st.bar_chart(unit_map)

            # latest
            st.subheader("📄 รายงานล่าสุด")

            for d in data[:10]:

                st.write("---")
                st.write("หน่วย:", d[1])
                st.write("งาน:", d[2])
                st.write("ความคืบหน้า:", f"{d[4]}%")
                st.write("สถานะ:", d[5])
                st.write("ปัญหา:", d[6])

                if d[7]:
                    imgs = d[7].split(",")
                    for img in imgs[:1]:
                        if os.path.exists(img):
                            st.image(img, width=200)

            # ================= EXPORT =================
            st.subheader("📑 Export PowerPoint")

            from_date = st.date_input("From")
            to_date = st.date_input("To")

            filtered = []

            for d in data:
                try:
                    t = datetime.datetime.fromisoformat(d[8]).date()
                    if from_date <= t <= to_date:
                        filtered.append(d)
                except:
                    pass

            st.write(f"📊 รายการในช่วง: {len(filtered)}")

            if st.button("📤 Export PPT"):

                export_ppt(filtered)

            st.caption("🔄 อัปเดตอัตโนมัติทุก 3 วินาที")

        time.sleep(3)

# =====================================================
# 🔥 ROUTER
# =====================================================
if st.session_state.admin_login:
    admin_app()
else:
    login_page()
    user_app()

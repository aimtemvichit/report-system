import streamlit as st
import sqlite3
import datetime
import os
import io
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= ADMIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

# 🔥 SESSION LOGIN (สำคัญ)
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

# ================= UPLOAD =================
UPLOAD_DIR = r"C:\Users\WICHIT_AIMTEM\OneDrive\เดสก์ท็อป\report-system\uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= DB =================
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
    report_date TEXT,
    time TEXT
)
""")
conn.commit()

# ================= STATUS =================
STATUS_OPTIONS = [
    "ค้าง 🔴",
    "กำลังดำเนินการ 🟡",
    "เสร็จสิ้น 🟢"
]

# ================= UI =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 👷 USER MODE
# =====================================================
def user_app():

    st.title("📌 ระบบรายงานหน่วย")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.ร.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    report_date = st.date_input("📅 วันที่รายงาน")

    task = st.text_input("งาน/ภารกิจ")
    detail = st.text_area("รายละเอียด")

    progress = st.number_input("ความคืบหน้า (%)", 0, 100)

    status = st.selectbox("สถานะ", STATUS_OPTIONS)

    problem = st.text_area("⚠️ ปัญหา / ข้อขัดข้อง")

    files = st.file_uploader("📷 แนบรูป (หลายภาพ)", accept_multiple_files=True)

    image_paths = []

    if files:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f.name)
            with open(path, "wb") as out:
                out.write(f.getbuffer())
            image_paths.append(path)

    if st.button("📤 ส่งรายงาน"):

        c.execute("""
            INSERT INTO reports (
                unit, task, detail, progress,
                status, problem, images, report_date, time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unit,
            task,
            detail,
            progress,
            status,
            problem,
            ",".join(image_paths),
            str(report_date),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# =====================================================
# 🔐 LOGIN PAGE
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
# 📑 EXPORT PPT
# =====================================================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    total = len(data)
    units = set([d[1] for d in data])

    status_count = {
        "ค้าง 🔴": 0,
        "กำลังดำเนินการ 🟡": 0,
        "เสร็จสิ้น 🟢": 0
    }

    for d in data:
        if d[5] in status_count:
            status_count[d[5]] += 1

    # ================= GRAPH =================
    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    bar_path = "bar.png"
    plt.savefig(bar_path)
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    pie_path = "pie.png"
    plt.savefig(pie_path)
    plt.close()

    # ================= SLIDE 1 =================
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "📊 Executive Dashboard"

    text = f"""
จำนวนรายงาน: {total}
หน่วย: {len(units)}

🔴 ค้าง: {status_count['ค้าง 🔴']}
🟡 กำลังดำเนินการ: {status_count['กำลังดำเนินการ 🟡']}
🟢 เสร็จสิ้น: {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_textbox(
        Inches(0.5), Inches(1),
        Inches(5), Inches(5)
    ).text = text

    if os.path.exists(bar_path):
        slide.shapes.add_picture(bar_path, Inches(6), Inches(1), width=Inches(3.5))

    if os.path.exists(pie_path):
        slide.shapes.add_picture(pie_path, Inches(6), Inches(4), width=Inches(3.5))

    # ================= DETAIL =================
    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"{d[1]} - {d[2]}"

        text = f"""
หน่วย: {d[1]}
วันที่: {d[8]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
ปัญหา: {d[6]}
"""

        slide.shapes.add_textbox(
            Inches(0.8), Inches(1.2),
            Inches(6), Inches(4)
        ).text = text

        if d[7]:
            imgs = d[7].split(",")
            y = 1.2

            for img in imgs:
                if os.path.exists(img):
                    slide.shapes.add_picture(img, Inches(7), Inches(y), width=Inches(2))
                    y += 2

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)

    st.download_button(
        "📥 Export PowerPoint",
        output,
        file_name="report.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# =====================================================
# 🧠 ADMIN DASHBOARD
# =====================================================
def admin_app():

    st.title("📊 กกร. Command Center")

    # 🔥 LOGOUT (สำคัญ)
    with st.sidebar:
        st.title("🔐 Admin")
        if st.button("🚪 Logout"):
            st.session_state.admin_login = False
            st.rerun()

    data = c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

    st.metric("จำนวนรายงาน", len(data))

    st.subheader("📄 รายงานล่าสุด")

    for d in data[:10]:

        st.write("---")
        st.write("หน่วย:", d[1])
        st.write("วันที่:", d[8])
        st.write("งาน:", d[2])
        st.write("ความคืบหน้า:", f"{d[4]}%")
        st.write("สถานะ:", d[5])
        st.write("ปัญหา:", d[6])

        if d[7]:
            imgs = d[7].split(",")
            cols = st.columns(3)

            for i, img in enumerate(imgs):
                if os.path.exists(img):
                    cols[i % 3].image(img, use_container_width=True)

    if st.button("📤 Export PPT"):

        export_ppt(data)

# =====================================================
# 🔥 ROUTER (FIX SESSION LOGIN)
# =====================================================
if st.session_state.admin_login:
    admin_app()
else:
    login_page()
    user_app()

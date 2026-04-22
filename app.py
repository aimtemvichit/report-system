import streamlit as st
import sqlite3
import datetime
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= ROUTE =================
mode = st.query_params.get("mode", "user")
if isinstance(mode, list):
    mode = mode[0]

is_admin = (mode == "admin")

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
    time TEXT
)
""")
conn.commit()

# ================= FORCE HIDE SIDEBAR =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 🔵 USER MODE (กรอกอย่างเดียว)
# =====================================================
def user_app():

    st.title("📌 ระบบรายงาน (หน่วย)")

    st.warning("🔒 โหมดหน่วย: ใช้กรอกข้อมูลเท่านั้น")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    task = st.text_input("ชื่องาน")
    detail = st.text_area("รายละเอียดงาน")
    progress = st.number_input("ความคืบหน้า (%)", 0, 100)

    status = st.selectbox("สถานะ", [
        "ค้าง",
        "กำลังดำเนินการ",
        "เสร็จสิ้น"
    ])

    if st.button("ส่งรายงาน"):

        c.execute("""
            INSERT INTO reports (unit, task, detail, progress, status, time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            unit, task, detail, progress, status,
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# =====================================================
# 🔴 ADMIN MODE (ครบทุกอย่าง)
# =====================================================
def admin_app():

    st.title("📊 กกร. Control Center")

    data = c.execute("SELECT * FROM reports").fetchall()

    # ================= MENU =================
    menu = st.radio("เมนู", [
        "Dashboard",
        "ค้นหางาน",
        "รายละเอียด",
        "Export PowerPoint"
    ])

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.metric("จำนวนงานทั้งหมด", len(data))

        avg = sum([d[4] for d in data]) / len(data) if data else 0
        st.metric("ความคืบหน้าเฉลี่ย", f"{avg:.2f}%")

        status = {"ค้าง":0, "กำลังดำเนินการ":0, "เสร็จสิ้น":0}

        for d in data:
            if "ค้าง" in d[5]:
                status["ค้าง"] += 1
            elif "ดำเนิน" in d[5]:
                status["กำลังดำเนินการ"] += 1
            else:
                status["เสร็จสิ้น"] += 1

        st.bar_chart(status)

    # ================= SEARCH =================
    elif menu == "ค้นหางาน":

        key = st.text_input("ค้นหา")

        results = [d for d in data if key.lower() in str(d).lower()]

        st.write(f"พบ {len(results)} รายการ")

        for r in results:
            st.write("---")
            st.write("หน่วย:", r[1])
            st.write("งาน:", r[2])
            st.write("ความคืบหน้า:", r[4], "%")

    # ================= DETAIL =================
    elif menu == "รายละเอียด":

        for d in data:
            st.write("---")
            st.write("หน่วย:", d[1])
            st.write("งาน:", d[2])
            st.write("รายละเอียด:", d[3])
            st.write("ความคืบหน้า:", d[4], "%")
            st.write("สถานะ:", d[5])

    # ================= EXPORT PPT =================
    elif menu == "Export PowerPoint":

        if st.button("สร้างไฟล์ PPT"):

            prs = Presentation()
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)

            # Slide 1 summary
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            slide.shapes.title.text = "Executive Summary"

            summary = prs.slides.add_slide(prs.slide_layouts[5])
            summary.shapes.title.text = f"รวม {len(data)} รายการ"

            # Slides per task
            for d in data:

                slide = prs.slides.add_slide(prs.slide_layouts[5])
                slide.shapes.title.text = d[2]

                txt = f"""
หน่วย: {d[1]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
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
if is_admin:
    admin_app()
else:
    user_app()

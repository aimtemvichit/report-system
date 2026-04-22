import streamlit as st
import sqlite3
import datetime
import os
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ระบบรายงานระดับกอง", layout="wide")

# ---------------- DATABASE ----------------
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

# ---------------- UI ----------------
st.title("📊 ระบบรายงาน กกร.ฉก.ทม.รอ.904 (ระดับกอง)")

menu = st.sidebar.radio("เมนู", [
    "ส่งรายงาน",
    "Dashboard",
    "ค้นหางาน",
    "Export PowerPoint"
])

# ---------------- 1. FORM ----------------
if menu == "ส่งรายงาน":
    st.header("📌 ส่งรายงานหน่วย")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.ร.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    task = st.text_input("ชื่องาน")
    detail = st.text_area("รายละเอียด")

    progress = st.number_input("ความคืบหน้า (%)", 0, 100, step=1)

    status = st.selectbox("สถานะงาน", [
        "🟥 ค้าง",
        "🟨 กำลังดำเนินการ",
        "🟩 เสร็จสิ้น"
    ])

    problem = st.text_area("ปัญหา/ข้อขัดข้อง")

    images = st.file_uploader(
        "แนบรูป (หลายรูปได้)",
        type=["jpg", "png"],
        accept_multiple_files=True
    )

    if st.button("ส่งข้อมูล"):

        img_paths = []

        if images:
            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            for img in images:
                path = f"uploads/{datetime.datetime.now().timestamp()}_{img.name}"
                with open(path, "wb") as f:
                    f.write(img.read())
                img_paths.append(path)

        c.execute("""
            INSERT INTO reports (unit, task, detail, progress, status, problem, images, time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unit,
            task,
            detail,
            progress,
            status,
            problem,
            ",".join(img_paths),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งข้อมูลสำเร็จ")

# ---------------- 2. DASHBOARD ----------------
elif menu == "Dashboard":
    st.header("📊 Dashboard ระดับกอง")

    data = c.execute("SELECT * FROM reports").fetchall()

    if data:

        total = len(data)
        avg = sum([d[4] for d in data]) / total

        col1, col2 = st.columns(2)

        with col1:
            st.metric("📌 งานทั้งหมด", total)

        with col2:
            st.metric("📈 ความคืบหน้าเฉลี่ย", f"{avg:.2f}%")

        # ---------------- STATUS ----------------
        st.subheader("📊 สถานะงาน")

        status_count = {
            "ค้าง": 0,
            "กำลังดำเนินการ": 0,
            "เสร็จสิ้น": 0
        }

        for d in data:
            if "ค้าง" in d[5]:
                status_count["ค้าง"] += 1
            elif "ดำเนิน" in d[5]:
                status_count["กำลังดำเนินการ"] += 1
            else:
                status_count["เสร็จสิ้น"] += 1

        st.bar_chart(status_count)

        # ---------------- UNIT ----------------
        st.subheader("📌 แยกตามหน่วย")

        unit_data = {}

        for d in data:
            unit_data[d[1]] = unit_data.get(d[1], 0) + d[4]

        st.bar_chart(unit_data)

        # ---------------- LIST ----------------
        st.subheader("📋 รายการงาน")

        for d in data:
            st.write("---")
            st.write("หน่วย:", d[1])
            st.write("งาน:", d[2])
            st.write("สถานะ:", d[5])
            st.write("ความคืบหน้า:", f"{d[4]}%")
            st.write("รายละเอียด:", d[3])

            if d[7]:
                for img in d[7].split(","):
                    if os.path.exists(img):
                        st.image(img, width=250)

# ---------------- 3. SEARCH ----------------
elif menu == "ค้นหางาน":
    st.header("🔍 ค้นหางาน")

    key = st.text_input("ค้นหา")

    if key:
        data = c.execute("""
            SELECT * FROM reports
            WHERE task LIKE ? OR detail LIKE ?
        """, (f"%{key}%", f"%{key}%")).fetchall()

        for d in data:
            st.write("---")
            st.write("หน่วย:", d[1])
            st.write("งาน:", d[2])
            st.write("สถานะ:", d[5])
            st.write("ความคืบหน้า:", f"{d[4]}%")

# ---------------- 4. EXPORT PPT ----------------
elif menu == "Export PowerPoint":
    st.header("📑 Export PowerPoint (16:9)")

    data = c.execute("SELECT * FROM reports").fetchall()

    if st.button("สร้าง PowerPoint"):

        # 🔥 16:9 SETUP
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        # ---------------- SLIDE 1 ----------------
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = "Executive Summary"

        total = len(data)
        avg = sum([d[4] for d in data]) / total if total else 0

        plt.figure()
        plt.pie([avg, 100-avg], labels=["Done", "Remaining"])
        plt.savefig("summary.png")

        slide.shapes.add_picture("summary.png", Inches(1), Inches(1.5), Inches(6))

        # ---------------- TASK SLIDES ----------------
        for d in data:

            slide = prs.slides.add_slide(prs.slide_layouts[5])
            slide.shapes.title.text = d[2]

            txt = f"""
หน่วย: {d[1]}
สถานะ: {d[5]}
ความคืบหน้า: {d[4]}%
รายละเอียด: {d[3]}
ปัญหา: {d[6]}
"""

            box = slide.shapes.add_textbox(
                Inches(0.8), Inches(1.2),
                Inches(6), Inches(2)
            )
            box.text = txt

            # ---------------- IMAGES ----------------
            if d[7]:
                imgs = d[7].split(",")
                y = 3.0

                for img in imgs:
                    if os.path.exists(img):
                        try:
                            slide.shapes.add_picture(img, Inches(7), Inches(y), Inches(5))
                            y += 1.5
                        except:
                            pass

        prs.save("report_final.pptx")
        st.success("สร้าง PowerPoint สำเร็จ → report_final.pptx")
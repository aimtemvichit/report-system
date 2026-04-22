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

# ================= AUTO REFRESH (SAFE METHOD) =================
st.experimental_set_query_params(t=str(datetime.datetime.now()))

# ================= ADMIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "admin_login" not in st.session_state:
    st.session_state["admin_login"] = False

# ================= UPLOAD =================
UPLOAD_DIR = "uploads"
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

STATUS_OPTIONS = [
    "ค้าง 🔴",
    "กำลังดำเนินการ 🟡",
    "เสร็จสิ้น 🟢"
]

# ================= USER =================
def user_app():

    st.title("📌 ระบบรายงานหน่วย")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.ร.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    report_date = st.date_input("วันที่รายงาน")

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")

    progress = st.number_input("ความคืบหน้า (%)", 0, 100)

    status = st.selectbox("สถานะ", STATUS_OPTIONS)

    problem = st.text_area("ปัญหา / ข้อขัดข้อง")

    files = st.file_uploader("แนบรูป", accept_multiple_files=True)

    image_paths = []

    if files:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f.name)
            with open(path, "wb") as out:
                out.write(f.getbuffer())
            image_paths.append(path)

    if st.button("ส่งรายงาน"):

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
        st.success("ส่งสำเร็จ")

    st.stop()

# ================= LOGIN =================
def login_page():

    st.title("🔐 กกร. Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):

        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["admin_login"] = True
            st.rerun()
        else:
            st.error("Login ไม่ถูกต้อง")

# ================= DATA =================
def get_data():

    data = c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    return data

# ================= EXPORT PPT =================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    total = len(data)

    status_count = {
        "ค้าง 🔴": 0,
        "กำลังดำเนินการ 🟡": 0,
        "เสร็จสิ้น 🟢": 0
    }

    for d in data:
        if d[5] in status_count:
            status_count[d[5]] += 1

    # chart
    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    bar = "bar.png"
    plt.savefig(bar)
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    pie = "pie.png"
    plt.savefig(pie)
    plt.close()

    # slide 1
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "📊 Dashboard Summary"

    text = f"""
จำนวนทั้งหมด: {total}

🔴 {status_count['ค้าง 🔴']}
🟡 {status_count['กำลังดำเนินการ 🟡']}
🟢 {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(5), Inches(5)).text = text

    if os.path.exists(bar):
        slide.shapes.add_picture(bar, Inches(6), Inches(1), width=Inches(3.5))

    if os.path.exists(pie):
        slide.shapes.add_picture(pie, Inches(6), Inches(4), width=Inches(3.5))

    # details
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

        slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(6), Inches(4)).text = text

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)

    st.download_button(
        "📥 Export PPT",
        output,
        file_name="report.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# ================= ADMIN =================
def admin_app():

    st.title("📊 กกร. Command Center (Live)")

    # 🔥 LOGOUT
    with st.sidebar:
        st.title("Admin")
        if st.button("🚪 Logout"):
            st.session_state["admin_login"] = False
            st.rerun()

    data = get_data()

    st.metric("จำนวนรายงาน", len(data))

    st.subheader("📄 รายงานล่าสุด")

    for d in data[:20]:

        st.write("---")
        st.write("หน่วย:", d[1])
        st.write("วันที่:", d[8])
        st.write("งาน:", d[2])
        st.write("สถานะ:", d[5])

        if d[7]:
            imgs = d[7].split(",")
            cols = st.columns(3)

            for i, img in enumerate(imgs):
                if os.path.exists(img):
                    cols[i % 3].image(img, use_container_width=True)

    if st.button("📤 Export PPT"):

        export_ppt(data)

# ================= ROUTER =================
def main():

    if "admin_login" not in st.session_state:
        st.session_state["admin_login"] = False

    if st.session_state["admin_login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

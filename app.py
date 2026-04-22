import streamlit as st
import sqlite3
import datetime
import os
import io
import time
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="Command Center", layout="wide")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "admin_login" not in st.session_state:
    st.session_state["admin_login"] = False

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
    report_date TEXT,
    time TEXT
)
""")
conn.commit()

# ================= CONSTANT =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

STATUS_LIST = ["ค้าง 🔴", "กำลังดำเนินการ 🟡", "เสร็จสิ้น 🟢"]

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

    status = st.selectbox("สถานะ", STATUS_LIST)

    problem = st.text_area("ปัญหา / ข้อขัดข้อง")

    files = st.file_uploader("แนบรูป", accept_multiple_files=True)

    image_paths = []

    if files:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{f.name}")
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
            unit, task, detail, progress,
            status, problem,
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

# ================= GET DATA =================
def get_data():
    return c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

# ================= EXPORT PPT =================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    status_count = {k:0 for k in STATUS_LIST}

    for d in data:
        if d[5] in status_count:
            status_count[d[5]] += 1

    # chart
    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    plt.savefig("bar.png")
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    plt.savefig("pie.png")
    plt.close()

    # summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "📊 Summary"

    txt = f"""
จำนวนทั้งหมด: {len(data)}
ค้าง: {status_count['ค้าง 🔴']}
กำลังดำเนินการ: {status_count['กำลังดำเนินการ 🟡']}
เสร็จสิ้น: {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(6), Inches(4)).text = txt

    slide.shapes.add_picture("bar.png", Inches(6), Inches(1), width=Inches(3.5))
    slide.shapes.add_picture("pie.png", Inches(6), Inches(4), width=Inches(3.5))

    # detail slides
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

        slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(3)).text = text

        # images
        if d[7]:
            imgs = d[7].split(",")
            x, y = 6, 1

            for img in imgs:
                if os.path.exists(img):
                    slide.shapes.add_picture(img, Inches(x), Inches(y), width=Inches(3))
                    x += 3
                    if x > 10:
                        x = 6
                        y += 2

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

    st.title("📊 Command Center Dashboard")

    with st.sidebar:
        st.title("Admin Panel")

        if st.button("🚪 Logout"):
            st.session_state["admin_login"] = False
            st.rerun()

        st.markdown("## 📅 Filter")

        from_date = st.date_input("จากวันที่")
        to_date = st.date_input("ถึงวันที่")

    raw = get_data()
    data = []

    for d in raw:
        try:
            d_date = datetime.datetime.strptime(d[8], "%Y-%m-%d").date()
            if from_date <= d_date <= to_date:
                data.append(d)
        except:
            pass

    # ================= KPI =================
    st.subheader("📊 Overview")

    total = len(data)
    status_count = {k:0 for k in STATUS_LIST}
    unit_count = {}

    for d in data:
        status_count[d[5]] += 1
        unit_count[d[1]] = unit_count.get(d[1], 0) + 1

    st.metric("ทั้งหมด", total)

    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 ค้าง", status_count["ค้าง 🔴"])
    col2.metric("🟡 ดำเนินการ", status_count["กำลังดำเนินการ 🟡"])
    col3.metric("🟢 เสร็จสิ้น", status_count["เสร็จสิ้น 🟢"])

    # ================= CHART =================
    st.subheader("📊 Status Chart")

    fig1, ax1 = plt.subplots()
    ax1.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots()
    ax2.bar(status_count.keys(), status_count.values())
    st.pyplot(fig2)

    # ================= UNIT =================
    st.subheader("🏢 งานตามหน่วย")

    for u, ccc in sorted(unit_count.items(), key=lambda x: x[1], reverse=True):
        st.write(f"{u} : {ccc}")

    # ================= DETAIL =================
    st.subheader("📄 รายการ")

    for d in data[:30]:
        st.write("---")
        st.write(f"หน่วย: {d[1]}")
        st.write(f"งาน: {d[2]}")
        st.write(f"สถานะ: {d[5]}")

        if d[7]:
            imgs = d[7].split(",")
            cols = st.columns(3)

            for i, img in enumerate(imgs):
                if os.path.exists(img):
                    cols[i % 3].image(img, use_container_width=True)

    # ================= EXPORT =================
    if st.button("📤 Export PPT"):
        export_ppt(data)

# ================= ROUTER =================
def main():

    if st.session_state["admin_login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

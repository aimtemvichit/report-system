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
if "login" not in st.session_state:
    st.session_state["login"] = False

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()

# auto refresh (safe)
if st.session_state["login"]:
    if time.time() - st.session_state["last_refresh"] > 5:
        st.session_state["last_refresh"] = time.time()
        st.rerun()

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

# ================= CONSTANT =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

STATUS = ["ค้าง 🔴", "กำลังดำเนินการ 🟡", "เสร็จสิ้น 🟢"]

# ================= USER =================
def user():

    st.title("📌 ระบบรายงานหน่วย")

    unit = st.selectbox("หน่วย", ["พล.1 รอ.", "พล.ร.2 รอ.", "พล.ม.2 รอ."])

    report_date = st.date_input("วันที่รายงาน")

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")

    progress = st.number_input("ความคืบหน้า (%)", 0, 100)

    status = st.selectbox("สถานะ", STATUS)

    problem = st.text_area("ปัญหา")

    files = st.file_uploader("แนบรูป", accept_multiple_files=True)

    images = []

    if files:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{f.name}")
            with open(path, "wb") as w:
                w.write(f.getbuffer())
            images.append(path)

    if st.button("ส่งรายงาน"):

        c.execute("""
            INSERT INTO reports VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            unit, task, detail, progress,
            status, problem,
            ",".join(images),
            str(report_date),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งสำเร็จ")

    st.stop()

# ================= LOGIN =================
def login():

    st.title("🔐 LOGIN")

    u = st.text_input("User")
    p = st.text_input("Pass", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("ผิด")

# ================= DATA =================
def get_data():
    return c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

# ================= EXPORT =================
def export(data):

    prs = Presentation()

    status_count = {s:0 for s in STATUS}

    for d in data:
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

    # summary
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "SUMMARY"

    slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(6), 3).text = f"""
ทั้งหมด: {len(data)}
ค้าง: {status_count['ค้าง 🔴']}
กำลังดำเนินการ: {status_count['กำลังดำเนินการ 🟡']}
เสร็จสิ้น: {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_picture("bar.png", Inches(6), Inches(1), width=Inches(3))
    slide.shapes.add_picture("pie.png", Inches(6), Inches(4), width=Inches(3))

    # details
    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"{d[1]} | {d[2]}"

        text = f"""
หน่วย: {d[1]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {d[5]}
ปัญหา: {d[6]}
"""

        slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), 3).text = text

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

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)

    st.download_button(
        "Export PPT",
        buf,
        file_name="report.pptx"
    )

# ================= ADMIN =================
def admin():

    st.title("📊 Command Center")

    with st.sidebar:

        if st.button("Logout"):
            st.session_state["login"] = False
            st.rerun()

        st.subheader("Filter")

        from_date = st.date_input("From")
        to_date = st.date_input("To")

    raw = get_data()
    data = []

    for d in raw:
        try:
            dt = datetime.datetime.strptime(d[8], "%Y-%m-%d").date()
            if from_date <= dt <= to_date:
                data.append(d)
        except:
            pass

    st.metric("ทั้งหมด", len(data))

    status_count = {s:0 for s in STATUS}

    for d in data:
        status_count[d[5]] += 1

    col1,col2,col3 = st.columns(3)

    col1.metric("ค้าง", status_count["ค้าง 🔴"])
    col2.metric("ทำอยู่", status_count["กำลังดำเนินการ 🟡"])
    col3.metric("เสร็จ", status_count["เสร็จสิ้น 🟢"])

    st.subheader("รายการ")

    for d in data[:30]:
        st.write(f"{d[1]} | {d[2]} | {d[5]}")

    if st.button("Export PPT"):
        export(data)

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin()
    else:
        login()
        user()

main()

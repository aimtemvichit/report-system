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
st.set_page_config(page_title="WAR ROOM COMMAND CENTER", layout="wide")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state["login"] = False

if "refresh" not in st.session_state:
    st.session_state["refresh"] = time.time()

# auto refresh
if st.session_state["login"]:
    if time.time() - st.session_state["refresh"] > 5:
        st.session_state["refresh"] = time.time()
        st.rerun()

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

# ================= CONFIG =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

STATUS = ["ค้าง 🔴", "กำลังดำเนินการ 🟡", "เสร็จสิ้น 🟢"]

UNITS = ["ทั้งหมด", "พล.1 รอ.", "พล.ร.2 รอ.", "พล.ม.2 รอ.", "กรม ทย.รอ.อย."]

# ================= DELETE =================
def delete_report(report_id):
    c.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()

# ================= DATA =================
def get_data():
    return c.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

# ================= USER =================
def user_app():

    st.title("📌 UNIT REPORT SYSTEM")

    unit = st.selectbox("หน่วย", UNITS[1:])
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
def login_page():

    st.title("🔐 WAR ROOM LOGIN")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("Login ไม่ถูกต้อง")

# ================= EXPORT PPT =================
def export_ppt(data):

    prs = Presentation()

    status_count = {"ค้าง 🔴":0,"กำลังดำเนินการ 🟡":0,"เสร็จสิ้น 🟢":0}

    for d in data:
        status_count[d[5]] += 1

    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    plt.savefig("bar.png")
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    plt.savefig("pie.png")
    plt.close()

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "WAR ROOM SUMMARY"

    slide.shapes.add_textbox(
        Inches(0.5), Inches(1), Inches(6), 3
    ).text = f"""
TOTAL: {len(data)}
🔴 {status_count['ค้าง 🔴']}
🟡 {status_count['กำลังดำเนินการ 🟡']}
🟢 {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_picture("bar.png", Inches(6), Inches(1), width=Inches(3))
    slide.shapes.add_picture("pie.png", Inches(6), Inches(4), width=Inches(3))

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

        slide.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(6), 3
        ).text = text

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

    st.download_button("📥 Export PPT", buf, file_name="war_room.pptx")

# ================= ADMIN =================
def admin_app():

    st.title("🚨 WAR ROOM COMMAND CENTER")

    with st.sidebar:

        if st.button("Logout"):
            st.session_state["login"] = False
            st.rerun()

        unit_filter = st.selectbox("หน่วย", UNITS)

        from_date = st.date_input("From")
        to_date = st.date_input("To")

    # ================= FILTER DATA (FIXED) =================
    raw = get_data()

    data = []

    for d in raw:

        try:
            dt = datetime.datetime.strptime(d[8], "%Y-%m-%d").date()

            if from_date <= dt <= to_date:

                if unit_filter == "ทั้งหมด":
                    data.append(d)
                elif d[1] == unit_filter:
                    data.append(d)

        except:
            pass

    # ================= ALERT =================
    if any(d[5] == "ค้าง 🔴" for d in data):
        st.error("🚨 มีงานค้างในระบบ")

    # ================= KPI =================
    status_count = {"ค้าง 🔴":0,"กำลังดำเนินการ 🟡":0,"เสร็จสิ้น 🟢":0}

    for d in data:
        status_count[d[5]] += 1

    c1,c2,c3 = st.columns(3)

    c1.metric("🔴 ค้าง", status_count["ค้าง 🔴"])
    c2.metric("🟡 ดำเนินการ", status_count["กำลังดำเนินการ 🟡"])
    c3.metric("🟢 เสร็จ", status_count["เสร็จสิ้น 🟢"])

    # ================= LIVE REPORTS =================
    st.subheader("📄 LIVE REPORTS (FILTERED BY UNIT)")

    for d in data:

        col1, col2 = st.columns([3,1])

        with col1:

            if d[5] == "ค้าง 🔴":
                st.error(f"{d[1]} | {d[2]}")
            elif d[5] == "กำลังดำเนินการ 🟡":
                st.warning(f"{d[1]} | {d[2]}")
            else:
                st.success(f"{d[1]} | {d[2]}")

            st.write(f"📅 {d[8]}")
            st.write(f"📊 {d[4]}%")
            st.write(f"🧾 {d[3]}")
            st.write(f"⚠️ {d[6]}")

            if d[7]:
                imgs = d[7].split(",")
                cols = st.columns(min(len(imgs),3))

                for i,img in enumerate(imgs):
                    if os.path.exists(img):
                        cols[i%3].image(img, use_container_width=True)

        with col2:

            st.metric("Progress", f"{d[4]}%")

            if st.button("🗑 ลบ", key=f"del_{d[0]}"):
                delete_report(d[0])
                st.rerun()

    # ================= EXPORT =================
    st.markdown("---")

    if st.button("📤 EXPORT PPT"):
        export_ppt(data)

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

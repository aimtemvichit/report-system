import streamlit as st
import sqlite3
import os
import datetime
import time
import pandas as pd
import io
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

# ================= CONFIG =================
st.set_page_config(page_title="COMMAND CENTER", layout="wide")

UPLOAD_DIR = "uploads"
DB_DIR = "database"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# ================= LOGIN =================
ADMIN_USER = "admin06"
ADMIN_PASS = "St006904#"

if "login" not in st.session_state:
    st.session_state["login"] = False

# ================= UNITS =================
UNITS = [
    "พล.1 รอ.",
    "พล.ร.2 รอ.",
    "พล.ม.2 รอ.",
    "กรม ทย.รอ.อย."
]

# ================= STATUS =================
STATUS = [
    "ยังไม่ดำเนินการ 🔴",
    "กำลังดำเนินการ 🟡",
    "เสร็จสิ้น 🟢"
]

# ================= NORMALIZE (กันพัง 100%) =================
def norm(s):
    if not s:
        return "ยังไม่ดำเนินการ 🔴"
    s = str(s)
    if "เสร็จ" in s:
        return "เสร็จสิ้น 🟢"
    if "ดำเนิน" in s:
        return "กำลังดำเนินการ 🟡"
    return "ยังไม่ดำเนินการ 🔴"

# ================= DB =================
def safe_unit(u):
    return u.replace(" ", "_").replace(".", "")

def db_path(unit):
    folder = os.path.join(DB_DIR, safe_unit(unit))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "reports.db")

def connect(unit):
    conn = sqlite3.connect(db_path(unit), check_same_thread=False)
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
    return conn, c

# ================= USER =================
def user_app():

    st.title("📌 พื้นที่สำหรับหน่วยรายงาน")

    unit = st.selectbox("เลือกหน่วย", UNITS)
    conn, c = connect(unit)

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")
    progress = st.number_input("ความคืบหน้า (%)", 0, 100)
    status = st.selectbox("สถานะ", STATUS)
    problem = st.text_area("ปัญหา")

    files = st.file_uploader("📸 แนบรูป", accept_multiple_files=True)

    images = []

    if files:
        for f in files:
            name = f"{time.time()}_{f.name}"
            path = os.path.join(UPLOAD_DIR, name)
            with open(path, "wb") as w:
                w.write(f.getbuffer())
            images.append(path)

    if st.button("📤 ส่งรายงาน"):

        c.execute("""
        INSERT INTO reports VALUES (NULL,?,?,?,?,?,?,?,?,?)
        """, (
            unit, task, detail, progress,
            norm(status), problem,
            ",".join(images),
            str(datetime.date.today()),
            str(datetime.datetime.now())
        ))

        conn.commit()
        st.success("ส่งรายงานสำเร็จ")

    st.stop()

# ================= LOAD ALL =================
def load_all():

    data = []

    for u in UNITS:
        conn, c = connect(u)
        rows = c.execute("SELECT * FROM reports").fetchall()

        fixed = []
        for r in rows:
            r = list(r)
            r[5] = norm(r[5])
            fixed.append(r)

        data.extend(fixed)

    return data

# ================= DELETE =================
def delete(unit, rid):
    conn, c = connect(unit)
    c.execute("DELETE FROM reports WHERE id=?", (rid,))
    conn.commit()

# ================= EXPORT PPTX 16:9 =================
def export_ppt(data):

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    status_count = {
        "ยังไม่ดำเนินการ 🔴": 0,
        "กำลังดำเนินการ 🟡": 0,
        "เสร็จสิ้น 🟢": 0
    }

    for d in data:
        status_count[norm(d[5])] += 1

    plt.figure()
    plt.bar(status_count.keys(), status_count.values())
    plt.title("STATUS")
    plt.tight_layout()
    plt.savefig("bar.png")
    plt.close()

    plt.figure()
    plt.pie(status_count.values(), labels=status_count.keys(), autopct="%1.1f%%")
    plt.title("STATUS")
    plt.savefig("pie.png")
    plt.close()

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "COMMAND CENTER SUMMARY"

    slide.shapes.add_textbox(
        Inches(0.5), Inches(1), Inches(6), Inches(3)
    ).text = f"""
TOTAL: {len(data)}
🔴 ยังไม่ดำเนินการ: {status_count['ยังไม่ดำเนินการ 🔴']}
🟡 กำลังดำเนินการ: {status_count['กำลังดำเนินการ 🟡']}
🟢 เสร็จสิ้น: {status_count['เสร็จสิ้น 🟢']}
"""

    slide.shapes.add_picture("bar.png", Inches(6), Inches(1), width=Inches(3))
    slide.shapes.add_picture("pie.png", Inches(6), Inches(4), width=Inches(3))

    for d in data:

        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"{d[1]} | {d[2]}"

        text = f"""
หน่วย: {d[1]}
งาน: {d[2]}
รายละเอียด: {d[3]}
ความคืบหน้า: {d[4]}%
สถานะ: {norm(d[5])}
ปัญหา: {d[6]}
วันที่: {d[8]}
"""

        slide.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(6), Inches(4)
        ).text = text

        if d[7]:
            imgs = d[7].split(",")
            x, y = 6, 1

            for img in imgs:
                if os.path.exists(img):
                    slide.shapes.add_picture(img, Inches(x), Inches(y), width=Inches(3))
                    x += 3
                    if x > 9:
                        x = 6
                        y += 2

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

# ================= ADMIN =================
def admin_app():

    st.title("🚨 กกร.ฉก.ทม.รอ.904 COMMAND CENTER")

    with st.sidebar:
        st.markdown("## CONTROL")

        if st.button("🚪 Logout"):
            st.session_state["login"] = False
            st.rerun()

        unit_filter = st.selectbox("หน่วย", ["ทั้งหมด"] + UNITS)
        from_date = st.date_input("From", datetime.date.today())
        to_date = st.date_input("To", datetime.date.today())

    data = load_all()

    filtered = []

    for d in data:
        try:
            dd = datetime.datetime.strptime(d[8], "%Y-%m-%d").date()
        except:
            continue

        if unit_filter != "ทั้งหมด" and d[1] != unit_filter:
            continue

        if not (from_date <= dd <= to_date):
            continue

        filtered.append(d)

    # KPI
    st.subheader("📊 KPI")

    total = len(filtered)

    c1, c2, c3 = st.columns(3)

    c1.metric("📦 ทั้งหมด", total)
    c2.metric("🟡 กำลังดำเนินการ", len([x for x in filtered if norm(x[5]) == "กำลังดำเนินการ 🟡"]))
    c3.metric("🔴 ยังไม่ดำเนินการ", len([x for x in filtered if norm(x[5]) == "ยังไม่ดำเนินการ 🔴"]))

    st.markdown("---")

    # REPORT
    st.subheader("📄 REPORT")

    for d in filtered:

        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"**{d[1]} | {d[2]} | {norm(d[5])}**")
            st.write(d[3])
            st.write("📅", d[8])

            if d[7]:
                for img in d[7].split(","):
                    if os.path.exists(img):
                        st.image(img, width=250)

        with col2:
            if st.button("🗑 ลบ", key=f"del_{d[0]}"):
                delete(d[1], d[0])
                st.rerun()

    # EXPORT
    st.markdown("---")

    if st.button("📤 EXPORT PPTX 16:9"):

        ppt = export_ppt(filtered)

        st.download_button(
            "📥 ดาวน์โหลด PPTX",
            ppt,
            file_name="COMMAND_CENTER.pptx"
        )

    # DB VIEW
    st.markdown("---")
    st.subheader("🧠 DATABASE VIEW")

    df = pd.DataFrame(filtered, columns=[
        "ID","หน่วย","งาน","รายละเอียด","%","สถานะ",
        "ปัญหา","รูป","วันที่","เวลา"
    ])

    st.dataframe(df, use_container_width=True)

# ================= LOGIN =================
def login_page():

    st.title("🔐 ADMIN LOGIN")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("Login ไม่ถูกต้อง")

# ================= ROUTER =================
def main():

    if st.session_state["login"]:
        admin_app()
    else:
        login_page()
        user_app()

main()

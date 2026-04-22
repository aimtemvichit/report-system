import streamlit as st
import sqlite3
import datetime

# ================= MUST FIRST =================
st.set_page_config(page_title="Report System", layout="wide")

# ================= ROUTE =================
mode = st.query_params.get("mode", "user")

if isinstance(mode, list):
    mode = mode[0]

# 🔥 บังคับค่าให้ชัด
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

# =====================================================
# 🔴 FORCE REMOVE SIDEBAR (สำคัญมาก)
# =====================================================
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 🔵 USER MODE (STRICT FORM ONLY)
# =====================================================
def user_app():

    st.title("📌 ระบบส่งรายงาน (หน่วย)")

    st.warning("🔒 หน่วย: ใช้กรอกข้อมูลเท่านั้น")

    unit = st.selectbox("หน่วย", [
        "พล.1 รอ.",
        "พล.2 รอ.",
        "พล.ม.2 รอ.",
        "กรม ทย.รอ.อย."
    ])

    task = st.text_input("งาน")
    detail = st.text_area("รายละเอียด")
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
        st.success("ส่งสำเร็จ")

    st.stop()  # 🔴 หยุด 100%

# =====================================================
# 🔴 ADMIN MODE (FULL CONTROL)
# =====================================================
def admin_app():

    st.title("📊 Dashboard กกร.")

    data = c.execute("SELECT * FROM reports").fetchall()

    st.metric("จำนวนงานทั้งหมด", len(data))

    st.subheader("รายการทั้งหมด")

    for d in data:
        st.write("---")
        st.write("หน่วย:", d[1])
        st.write("งาน:", d[2])
        st.write("ความคืบหน้า:", d[4], "%")
        st.write("สถานะ:", d[5])

# =====================================================
# 🔥 ROUTER (สำคัญที่สุด)
# =====================================================
if is_admin:
    admin_app()
else:
    user_app()

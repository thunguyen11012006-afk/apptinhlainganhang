import os
import pandas as pd
import requests
import streamlit as st

# ============================================================
# CẤU HÌNH ỨNG DỤNG
# ============================================================
st.set_page_config(
    page_title="FINBANK — Smart Banking Assistant",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

# ============================================================
# GIAO DIỆN CSS
# ============================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    section[data-testid="stSidebar"] {
        background-color: #1a2234 !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p {
        color: #ffffff !important;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px 17px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HÀM HỖ TRỢ
# ============================================================
def vnd(value):
    return f"{value:,.0f} VNĐ".replace(",", ".")

def calculate_loan(principal, annual_rate_percent, months, method):
    monthly_rate = annual_rate_percent / 100 / 12
    balance = float(principal)
    rows = []

    if method == "Trả góp đều (gốc + lãi gần bằng nhau)":
        if monthly_rate == 0:
            payment = principal / months
        else:
            payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))

        for month in range(1, months + 1):
            interest = balance * monthly_rate
            principal_paid = payment - interest
            if month == months or principal_paid > balance:
                principal_paid = balance
                payment_this_month = principal_paid + interest
            else:
                payment_this_month = principal_paid + interest
            balance = max(0.0, balance - principal_paid)
            rows.append({
                "Tháng": month,
                "Dư nợ đầu kỳ (VNĐ)": round(balance + principal_paid),
                "Tiền gốc (VNĐ)": round(principal_paid),
                "Tiền lãi (VNĐ)": round(interest),
                "Tổng phải trả (VNĐ)": round(payment_this_month),
                "Dư nợ cuối kỳ (VNĐ)": round(balance),
            })
    else:
        principal_each_month = principal / months
        for month in range(1, months + 1):
            balance_start = balance
            interest = balance_start * monthly_rate
            principal_paid = min(principal_each_month, balance_start)
            payment_this_month = principal_paid + interest
            balance = max(0.0, balance_start - principal_paid)
            rows.append({
                "Tháng": month,
                "Dư nợ đầu kỳ (VNĐ)": round(balance_start),
                "Tiền gốc (VNĐ)": round(principal_paid),
                "Tiền lãi (VNĐ)": round(interest),
                "Tổng phải trả (VNĐ)": round(payment_this_month),
                "Dư nợ cuối kỳ (VNĐ)": round(balance),
            })

    schedule = pd.DataFrame(rows)
    total_interest = float(schedule["Tiền lãi (VNĐ)"].sum())
    total_principal = float(schedule["Tiền gốc (VNĐ)"].sum())
    total_payment = total_principal + total_interest
    return schedule, total_interest, total_payment

def ask_openrouter(api_key, model, messages):
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "FINBANK",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 900,
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"Lỗi kết nối ({response.status_code}): {detail}")
    data = response.json()
    return data["choices"][0]["message"]["content"]

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("### 🏦 FINBANK")
st.sidebar.markdown("<p style='font-size: 0.85rem; color: #94a3b8;'>Smart Banking Assistant</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Điều hướng",
    ["🏠 Tổng quan", "📊 Máy tính PRO", "⚖️ So sánh ngân hàng", "💬 Chatbot AI", "📈 Báo cáo & biểu đồ", "📖 Hướng dẫn"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🤖 Trợ lý AI")

api_key = ""
try:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    pass

if not api_key:
    api_key = os.getenv("OPENROUTER_API_KEY", "")

if api_key:
    st.sidebar.success("Đã kết nối API AI")
else:
    st.sidebar.warning("Chưa cấu hình API Key")

# ============================================================
# NỘI DUNG CHÍNH TỪNG TAB
# ============================================================
if menu == "🏠 Tổng quan":
    st.markdown('<div class="main-title">🎯 Nền Tảng Tài Chính FINBANK</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Giải pháp quản lý, tính toán lịch trả nợ và tư vấn tài chính thông minh dựa trên trí tuệ nhân tạo.</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💡 **Máy tính Khoản vay**\n\nTính toán chi tiết gốc và lãi từng tháng theo nhiều phương thức khác nhau chuẩn xác 100%.")
    with col2:
        st.success("⚖️ **So sánh Ngân hàng**\n\nTổng hợp và đối chiếu lãi suất, ưu đãi vay mua nhà, mua xe từ các ngân hàng hàng đầu.")
    with col3:
        st.warning("🤖 **Trợ lý AI 24/7**\n\nTư vấn chiến lược trả nợ trước hạn, tối ưu hóa dòng tiền và giải đáp mọi thắc mắc tài chính.")

    st.markdown("---")
    st.markdown("### 🚀 Điểm nổi bật của hệ thống")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("- **Giao diện trực quan:** Tối ưu hiển thị cho máy chiếu và màn hình lớn.\n- **Bảo mật tuyệt đối:** Quản lý khóa API an toàn qua Streamlit Secrets.")
    with c2:
        st.markdown("- **Báo cáo minh họa:** Biểu đồ trực quan giúp dễ dàng nắm bắt cơ cấu dòng tiền.\n- **Đa nền tảng:** Hoạt động trơn tru trên mọi trình duyệt web hiện đại.")

elif menu == "📊 Máy tính PRO":
    st.markdown('<div class="main-title">📊 Máy tính Khoản vay PRO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Nhập thông số khoản vay để lập bảng chiết tính chi tiết hằng tháng.</div>', unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        principal = st.number_input("Số tiền vay (VNĐ)", min_value=1_000_000, value=500_000_000, step=10_000_000)
        annual_rate = st.number_input("Lãi suất năm (%/năm)", min_value=0.0, value=9.5, step=0.1)
    with col_input2:
        months = st.number_input("Thời hạn vay (tháng)", min_value=1, value=60, step=12)
        method = st.selectbox(
            "Phương pháp trả nợ",
            [
                "Trả góp đều (gốc + lãi gần bằng nhau)",
                "Gốc đều hằng tháng (gốc cố định, lãi giảm dần)"
            ]
        )
    
    if st.button("🚀 Thực hiện tính toán ngay", type="primary"):
        schedule, total_interest, total_payment = calculate_loan(principal, annual_rate, months, method)
        
        st.markdown("### 📌 Kết quả tổng quan")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng gốc phải trả", vnd(principal))
        m2.metric("Tổng tiền lãi", vnd(total_interest))
        m3.metric("Tổng gốc + lãi", vnd(total_payment))
        
        st.markdown("### 📑 Chi tiết lịch trả nợ hằng tháng")
        st.dataframe(schedule, use_container_width=True)

elif menu == "⚖️ So sánh ngân hàng":
    st.markdown('<div class="main-title">⚖️ So Sánh Lãi Suất & Gói Vay Ngân Hàng</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cập nhật bảng lãi suất vay mua nhà, mua xe và tiêu dùng từ các ngân hàng lớn.</div>', unsafe_allow_html=True)
    
    data_banks = {
        "Ngân hàng": ["Vietcombank (VCB)", "Techcombank (TCB)", "VPBank", "BIDV", "MBBank", "TPBank"],
        "Lãi suất ưu đãi năm đầu (%/năm)": [7.5, 7.8, 8.0, 7.6, 7.7, 7.9],
        "Lãi suất sau ưu đãi (%/năm)": [10.5, 11.0, 11.2, 10.6, 10.8, 11.1],
        "Thời hạn vay tối đa": ["30 năm", "35 năm", "25 năm", "30 năm", "30 năm", "25 năm"],
        "Tỷ lệ cho vay tối đa (% TSĐB)": ["70%", "80%", "75%", "70%", "80%", "75%"],
        "Phí trả nợ trước hạn": ["1% - 2%", "Miễn phí từ năm thứ 4", "1.5%", "1% - 2%", "Miễn phí từ năm thứ 3", "1%"]
    }
    df_banks = pd.DataFrame(data_banks)
    st.dataframe(df_banks, use_container_width=True)
    
    st.info("💡 **Nhận xét chuyên gia:** Các ngân hàng TMCP tư nhân như Techcombank và MBBank có tỷ lệ cho vay hạn mức cao (đến 80%) và chính sách miễn phí trả nợ trước hạn linh hoạt hơn so với nhóm ngân hàng quốc doanh.")

elif menu == "💬 Chatbot AI":
    st.markdown('<div class="main-title">💬 Trợ lý Tài chính AI 24/7</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Hỏi đáp trực tiếp cùng chuyên gia AI về phương án vay vốn, tối ưu lãi suất và quản trị tài chính.</div>', unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "Bạn là chuyên gia tư vấn tài chính ngân hàng cao cấp của hệ thống FINBANK."}
        ]

    for msg in st.session_state["messages"]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Nhập câu hỏi của bạn tại đây...")
    if user_input:
        if not api_key:
            st.error("Chưa cấu hình API Key trong Streamlit Secrets!")
        else:
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("AI đang phân tích câu trả lời..."):
                    try:
                        reply = ask_openrouter(api_key, DEFAULT_MODEL, st.session_state["messages"])
                        st.markdown(reply)
                        st.session_state["messages"].append({"role": "assistant", "content": reply})
                    except Exception as e:
                        st.error(f"Không thể kết nối AI: {e}")

elif menu == "📈 Báo cáo & biểu đồ":
    st.markdown('<div class="main-title">📈 Báo Cáo & Phân Tích Biểu Đồ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Trực quan hóa cấu trúc dòng tiền gốc và lãi qua từng giai đoạn vay.</div>', unsafe_allow_html=True)
    
    # Dữ liệu mô phỏng cho biểu đồ
    chart_data = pd.DataFrame({
        "Tháng": [f"Tháng {i}" for i in range(1, 13)],
        "Tiền gốc trả": [4000000, 4100000, 4200000, 4300000, 4400000, 4500000, 4600000, 4700000, 4800000, 4900000, 5000000, 5100000],
        "Tiền lãi trả": [4500000, 4400000, 4300000, 4200000, 4100000, 4000000, 3900000, 3800000, 3700000, 3600000, 3500000, 3400000]
    }).set_index("Tháng")
    
    st.markdown("### 📊 Biểu đồ cơ cấu trả gốc và lãi (12 tháng đầu tiên)")
    st.bar_chart(chart_data)
    
    st.markdown("### 📌 Thống kê dòng tiền tài chính")
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        st.metric("Tỷ trọng tiền gốc trung bình", "48.5%")
    with col_rep2:
        st.metric("Tỷ trọng tiền lãi trung bình", "51.5%")

else:
    st.markdown('<div class="main-title">📖 Hướng Dẫn Sử Dụng Nền Tảng FINBANK</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tài liệu hướng dẫn nhanh các tính năng dành cho người dùng và chuyên viên tư vấn.</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📌 Các bước thao tác chính trên hệ thống:
    
    1. **Sử dụng Máy tính PRO:**
       - Điền chính xác số tiền cần vay, lãi suất theo năm và kỳ hạn tính bằng tháng.
       - Chọn phương pháp trả góp phù hợp (Trả góp đều hoặc Gốc đều lãi giảm dần).
       - Bấm **"Thực hiện tính toán ngay"** để xuất bảng chiết tính chi tiết từng dòng tiền.
    
    2. **Tra cứu So sánh Ngân hàng:**
       - Truy cập tab **So sánh ngân hàng** để đối chiếu biên độ lãi suất ưu đãi giữa các ngân hàng thương mại lớn.
    
    3. **Tư vấn cùng Chatbot AI:**
       - Đặt câu hỏi trực tiếp để nhận tư vấn chuyên sâu về tài chính cá nhân và tối ưu hóa chi phí vay vốn.
    
    4. **Xem Báo cáo biểu đồ:**
       - Theo dõi trực quan xu hướng giảm dần của tiền lãi và cơ cấu trả nợ qua từng kỳ hạn.
    """)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>FINBANK • 2026 • Nền tảng công nghệ tài chính thông minh</p>", unsafe_allow_html=True)

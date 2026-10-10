import base64
import os
from io import BytesIO

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CẤU HÌNH ỨNG DỤNG
# ============================================================

st.set_page_config(
    page_title="Tính Khoản Vay Ngân Hàng",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "TÍNH KHOẢN VAY NGÂN HÀNG"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

# ============================================================
# HÀM HỖ TRỢ
# ============================================================

def vnd(value):
    """Định dạng số tiền theo kiểu Việt Nam."""
    return f"{value:,.0f} VNĐ".replace(",", ".")


def load_background(path="background.jpg"):
    """Đọc ảnh nền cục bộ và phủ một lớp tối để làm nổi bật chữ trắng."""
    if os.path.exists(path):
        with open(path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode()
        return f"""
        <style>
        .stApp {{
            background-image: linear-gradient(
                rgba(5, 15, 35, 0.88),
                rgba(5, 15, 35, 0.92)
            ),
            url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Ép toàn bộ chữ thành màu trắng sáng để hiển thị cực kỳ rõ trên nền ảnh tối */
        h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown, div[data-testid="stMarkdownContainer"] {{
            color: #ffffff !important;
        }}
        </style>
        """
    return """
    <style>
    .stApp {
        background: linear-gradient(135deg, #071936 0%, #103d68 55%, #eaf4ff 150%);
    }
    </style>
    """


def calculate_loan(principal, annual_rate_percent, months, method):
    """
    Tính lịch trả nợ theo dư nợ giảm dần.
    - Trả góp đều: tiền thanh toán hằng tháng gần như bằng nhau.
    - Gốc đều: tiền gốc cố định, tiền lãi giảm dần.
    """
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
    """Gửi câu hỏi đến OpenRouter và trả về nội dung chatbot."""
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Tinh Khoan Vay Ngan Hang",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 900,
    }
    response = requests.post(
        OPENROUTER_URL, headers=headers, json=payload, timeout=60
    )
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"OpenRouter báo lỗi ({response.status_code}): {detail}")
    data = response.json()
    return data["choices"][0]["message"]["content"]


# ============================================================
# CSS / GIAO DIỆN
# ============================================================

st.markdown(load_background(), unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1250px;}
    .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 20px;
        background: linear-gradient(120deg, rgba(7,31,66,.96), rgba(18,93,145,.91));
        border: 1px solid rgba(255,255,255,.20);
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,.18);
        margin-bottom: 1.2rem;
    }
    .hero h1 {font-size: clamp(1.7rem, 4vw, 2.7rem); margin: 0 0 .45rem 0; color: white;}
    .hero p {font-size: 1.02rem; margin: 0; color: #e6f3ff;}
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,.93);
        border: 1px solid #d8e7f4;
        padding: 15px 17px;
        border-radius: 14px;
    }
    div[data-testid="stMetric"] label {color: #244b70 !important;}
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# GIAO DIỆN CHÍNH (STREAMLIT UI)
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <h1>{APP_TITLE}</h1>
        <p>Công cụ tính toán lịch trả nợ ngân hàng chi tiết và hỗ trợ tư vấn tài chính thông minh.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar nhập liệu
st.sidebar.header("⚙️ Thông số khoản vay")
principal = st.sidebar.number_input("Số tiền vay (VNĐ)", min_value=1_000_000, value=500_000_000, step=10_000_000)
annual_rate = st.sidebar.number_input("Lãi suất năm (%/năm)", min_value=0.0, value=9.5, step=0.1)
months = st.sidebar.number_input("Thời hạn vay (tháng)", min_value=1, value=360, step=12)
method = st.sidebar.selectbox(
    "Phương pháp trả nợ",
    [
        "Trả góp đều (gốc + lãi gần bằng nhau)",
        "Gốc đều hằng tháng (gốc cố định, lãi giảm dần)"
    ]
)

# Lấy API Key từ Streamlit Secrets hoặc biến môi trường
api_key = ""
try:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    pass

if not api_key:
    api_key = os.getenv("OPENROUTER_API_KEY", "")

# Nút tính toán
if st.sidebar.button("Tính toán lịch trả nợ", type="primary"):
    schedule, total_interest, total_payment = calculate_loan(principal, annual_rate, months, method)
    
    st.success("Đã tính toán thành công!")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng gốc phải trả", vnd(principal))
    col2.metric("Tổng tiền lãi", vnd(total_interest))
    col3.metric("Tổng gốc + lãi", vnd(total_payment))
    
    st.subheader("📊 Bảng lịch trình trả nợ chi tiết")
    st.dataframe(schedule, use_container_width=True)

# Phần giao diện Chatbot tư vấn AI
st.markdown("---")
st.subheader("💬 Hỏi đáp cùng Trợ lý tài chính AI")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": "Bạn là một chuyên gia tư vấn tài chính và ngân hàng tận tâm, hỗ trợ giải đáp các vấn đề liên quan đến khoản vay, lãi suất và kế hoạch tài chính cho người dùng."}
    ]

# Hiển thị lịch sử chat
for msg in st.session_state["messages"]:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Nhập câu hỏi từ người dùng
user_input = st.chat_input("Nhập câu hỏi của bạn về khoản vay hoặc tài chính...")
if user_input:
    if not api_key:
        st.error("Chưa cấu hình OpenRouter API Key trong Streamlit Secrets! Vui lòng kiểm tra lại cài đặt.")
    else:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý câu trả lời..."):
                try:
                    bot_reply = ask_openrouter(api_key, DEFAULT_MODEL, st.session_state["messages"])
                    st.markdown(bot_reply)
                    st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")

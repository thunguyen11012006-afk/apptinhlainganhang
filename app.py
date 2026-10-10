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
    page_title="FinLoan AI PRO",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "FinLoan AI PRO"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

# ============================================================
# GIAO DIỆN CSS (SIDEBAR TỐI MÀU & NỀN SÁNG HIỆN ĐẠI)
# ============================================================

st.markdown(
    """
    <style>
    /* Toàn bộ nền chính sáng sủa */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Tùy chỉnh Sidebar tối màu chuẩn FinTech */
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

    /* Định dạng thẻ tiêu đề chính */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }
    
    /* Khung chỉ số metric */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 15px 17px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #6b7280 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HÀM HỖ TRỢ XỬ LÝ
# ============================================================

def vnd(value):
    """Định dạng số tiền theo kiểu Việt Nam."""
    return f"{value:,.0f} VNĐ".replace(",", ".")


def calculate_loan(principal, annual_rate_percent, months, method):
    """Tính lịch trả nợ theo dư nợ giảm dần."""
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
    """Gửi câu hỏi đến OpenRouter API."""
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "FinLoan AI PRO",
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
        raise RuntimeError(f"Lỗi xác thực hoặc kết nối ({response.status_code}): {detail}")
    data = response.json()
    return data["choices"][0]["message"]["content"]


# ============================================================
# THANH ĐIỀU HƯỚNG SIDEBAR
# ============================================================

st.sidebar.markdown("### 🏦 FinLoan AI PRO")
st.sidebar.markdown("<p style='font-size: 0.85rem; color: #9ca3af;'>Smart Banking Assistant</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Điều hướng",
    ["🏠 Tổng quan", "📊 Máy tính PRO", "⚖️ So sánh ngân hàng", "💬 Chatbot AI", "📈 Báo cáo & biểu đồ", "📖 Hướng dẫn"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🤖 AI Assistant")

# Lấy API Key từ Streamlit Secrets hoặc biến môi trường
api_key = ""
try:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    pass

if not api_key:
    api_key = os.getenv("OPENROUTER_API_KEY", "")

if api_key:
    st.sidebar.success("Đã có API key")
else:
    st.sidebar.warning("Chưa cấu hình API key")

# ============================================================
# NỘI DUNG CHÍNH THEO TỪNG TAB
# ============================================================

if "🏠 Tổng quan" in menu:
    st.markdown('<div class="main-title">🎯 FinLoan AI PRO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Nền tảng công nghệ tài chính thông minh hỗ trợ phân tích khoản vay và tư vấn ngân hàng tự động.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("💡 **Tính năng nổi bật:**\n- Tính toán lịch trả nợ chi tiết theo phương pháp dư nợ giảm dần.\n- So sánh và mô phỏng các gói vay linh hoạt.\n- Trợ lý ảo AI giải đáp mọi thắc mắc về tài chính 24/7.")
    with col2:
        st.success("🚀 **Hướng dẫn nhanh:**\n1. Chọn mục **Máy tính PRO** để tính toán tiền gốc và lãi.\n2. Trò chuyện trực tiếp với chuyên gia tại **Chatbot AI**.")

elif "📊 Máy tính PRO" in menu:
    st.markdown('<div class="main-title">📊 Máy tính Khoản vay PRO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Nhập thông số để lập bảng chiết tính lịch trả nợ chi tiết hàng tháng.</div>', unsafe_allow_html=True)
    
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

elif "💬 Chatbot AI" in menu:
    st.markdown('<div class="main-title">💬 Hỏi đáp cùng Trợ lý tài chính AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Bạn có thể hỏi về khoản vay, cách tối ưu lãi suất hoặc bất kỳ câu hỏi tài chính phù hợp nào.</div>', unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "Bạn là chuyên gia tư vấn tài chính ngân hàng cao cấp của hệ thống FinLoan AI PRO."}
        ]

    for msg in st.session_state["messages"]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Nhập câu hỏi của bạn...")
    if user_input:
        if not api_key:
            st.error("Chưa cấu hình API Key trong Streamlit Secrets! Vui lòng kiểm tra lại.")
        else:
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("AI đang phân tích..."):
                    try:
                        reply = ask_openrouter(api_key, DEFAULT_MODEL, st.session_state["messages"])
                        st.markdown(reply)
                        st.session_state["messages"].append({"role": "assistant", "content": reply})
                    except Exception as e:
                        st.error(f"Không gọi được AI: {e}")

else:
    st.markdown(f'<div class="main-title">{menu}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Chức năng đang được cập nhật để phục vụ buổi thuyết trình tốt nhất.</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 0.85rem;'>FinLoan AI PRO • 2026 • Công cụ tham khảo tài chính</p>", unsafe_allow_html=True)

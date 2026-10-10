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
    page_title="FINBANK — Smart Banking Assistant",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "FINBANK"
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
        raise RuntimeError(f"Lỗi xác thực hoặc kết nối ({response.status_code}): {detail}")
    data = response.json()
    return data["choices"][0]["message"]["content"]


# ============================================================
# THANH ĐIỀU HƯỚNG SIDEBAR
# ============================================================

st.sidebar.markdown("### 🏦 FINBANK")
st.sidebar.markdown("<p style='font-size: 0.85rem; color: #9ca3af;'>Smart Banking Assistant</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.

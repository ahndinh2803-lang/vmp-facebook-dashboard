import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from sklearn.linear_model import LinearRegression
import plotly.express as px
import datetime
import io

# ==========================================
# CẤU HÌNH GIAO DIỆN LIGHT MODE
# ==========================================
st.set_page_config(page_title="VMP Facebook Ads Dashboard", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .custom-card {
        background-color: #ffffff; border-radius: 12px; padding: 20px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .status-success { background-color: #10b981; height: 8px; border-radius: 10px; }
    .status-fail { background-color: #ef4444; height: 8px; border-radius: 10px; }
    .progress-bg { background-color: #f1f5f9; border-radius: 10px; height: 8px; width: 100%; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# KẾT NỐI DATA FACEBOOK ADS
# ==========================================
def get_ss_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_fb_data():
    gc = get_ss_client()
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())
    
    # Làm sạch dữ liệu
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])
    
    numeric_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)', 'Clicks (All)']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    return df

df_raw = load_fb_data()

# ==========================================
# BỘ LỌC SIDEBAR
# ==========================================
with st.sidebar:
    st.title("📈 FB ADS REPORT")
    start_date = st.date_input("Từ ngày", df_raw['Created Time'].min())
    end_date = st.date_input("Đến ngày", df_raw['Created Time'].max())
    
df = df_raw[(df_raw['Created Time'] >= pd.to_datetime(start_date)) & 
            (df_raw['Created Time'] <= pd.to_datetime(end_date))]

# ==========================================
# HIỂN THỊ DASHBOARD
# ==========================================
st.title("📊 Hiệu suất Facebook Ads Overview")

# Metrics
m1, m2, m3 = st.columns(3)
total_reach = df['Reach'].sum()
target_reach = 188000 # Giả định mục tiêu

with m1:
    ratio = min(total_reach/target_reach, 1.0)
    color = "status-success" if total_reach >= target_reach else "status-fail"
    st.markdown(f"""
        <div class="custom-card">
            <div style="color: #64748b; font-size: 0.8rem;">TỔNG REACH</div>
            <div style="font-size: 2rem; font-weight: bold;">{total_reach:,.0f}</div>
            <div class="progress-bg"><div class="{color}" style="width: {ratio*100}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)

# Biểu đồ
st.markdown("### Biểu đồ xu hướng Reach")
fig = px.line(df.groupby(df['Created Time'].dt.date)['Reach'].sum().reset_index(), 
              x='Created Time', y='Reach', template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Dữ liệu chi tiết Content")
st.dataframe(df[['Created Time', 'FORMAT', 'Reach', 'Tổng tương tác', 'Clicks (Link)']], use_container_width=True)

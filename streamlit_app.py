import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
import plotly.express as px
import plotly.graph_objects as go
import datetime
import math
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN (LIGHT MODE)
# ==========================================
st.set_page_config(page_title="VMP Facebook Analytics", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    .custom-card {
        background-color: #ffffff; border-radius: 16px; padding: 24px;
        border: 1px solid #e2e8f0; margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .progress-container { background-color: #f1f5f9; border-radius: 10px; height: 8px; width: 100%; margin-top: 10px; overflow: hidden; }
    .progress-bar-fill { height: 100%; border-radius: 10px; }
    .status-success { background-color: #10b981; }
    .status-fail { background-color: #ef4444; }
    .ai-box { background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 12px; padding: 20px; color: #0c4a6e; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. KẾT NỐI & XỬ LÝ DỮ LIỆU (A -> AA)
# ==========================================
def get_ss_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_fb_data():
    gc = get_ss_client()
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())
    
    # Làm sạch Created Time
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])
    
    # Ép kiểu số toàn bộ cột A -> AA
    numeric_cols = [
        'IMPRESSION', 'Reach', 'Tổng tương tác', 'Likes', 'Comments', 'Shares', 
        'Clicks (All)', 'Clicks (Link)', 'Clicks (Other)', 'Clicks (Photo View)', 
        'Clicks (Video Play)', 'Reach (Fan)', 'Reach (Paid)'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    # Tuần trong tháng
    df['Week'] = pd.cut(df['Created Time'].dt.day, bins=[0, 7, 14, 21, 31], labels=[1, 2, 3, 4]).astype(int)
    return df

df_raw = load_fb_data()

# ==========================================
# 3. DỰ BÁO MỤC TIÊU (LOGIC MỤC 2 COLAB)
# ==========================================
@st.cache_data(ttl=600)
def calculate_fb_goals(df):
    metrics = ['Reach', 'Tổng tương tác', 'Clicks (Link)']
    goals_results = {}
    
    for met in metrics:
        hist_25 = df[df['Year'] == 2025].groupby('Month')[met].sum().reindex(range(1, 13), fill_value=0).values
        act_26 = df[df['Year'] == 2026].groupby('Month')[met].sum().reindex(range(1, 13), fill_value=0).values
        
        y = hist_25.astype(float)
        # Thuật toán dự báo
        ma_pred = np.array([np.mean(y[max(0, i-3):i]) if i > 0 else y[0] for i in range(1, 13)])
        try:
            model_es = SimpleExpSmoothing(y).fit(smoothing_level=0.3, optimized=False)
            es_pred = model_es.fittedvalues
        except: es_pred = ma_pred
        
        # Giả định tăng trưởng 15%
        target_2026 = [int(max(p * 1.15, 10)) for p in es_pred]
        
        goals_results[met] = {
            'monthly': [{'month': m, 'act25': int(y[m-1]), 'tar26': target_2026[m-1], 'act26': int(act_26[m-1])} for m in range(1, 13)]
        }
    return goals_results

goals_fb = calculate_fb_goals(df_raw)

# ==========================================
# 4. ĐIỀU HƯỚNG & BỘ LỌC
# ==========================================
with st.sidebar:
    st.title("📈 VMP FACEBOOK")
    nav = st.radio("Menu", ["📊 Tổng quan", "🎯 Mục tiêu & AI", "📝 Dữ liệu Content"])
    st.divider()
    start_date = st.date_input("Từ ngày", df_raw['Created Time'].min())
    end_date = st.date_input("Đến ngày", df_raw['Created Time'].max())

df = df_raw[(df_raw['Created Time'] >= pd.to_datetime(start_date)) & (df_raw['Created Time'] <= pd.to_datetime(end_date))]

# ==========================================
# 5. HIỂN THỊ CHI TIẾT
# ==========================================
if nav == "📊 Tổng quan":
    st.title("📊 Tổng quan hiệu suất Fanpage")
    
    # Metrics hàng đầu
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Reach", f"{df['Reach'].sum():,.0f}")
    c2.metric("Impression", f"{df['IMPRESSION'].sum():,.0f}")
    c3.metric("Tương tác", f"{df['Tổng tương tác'].sum():,.0f}")
    c4.metric("Click Link", f"{df['Clicks (Link)'].sum():,.0f}")
    
    # Biểu đồ xu hướng
    st.markdown("### Xu hướng Reach 2025 - 2026")
    df_chart = df_raw.groupby(['Year', 'Month'])['Reach'].sum().reset_index()
    fig = px.line(df_chart, x='Month', y='Reach', color='Year', markers=True, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

elif nav == "🎯 Mục tiêu & AI":
    st.title("🎯 Theo dõi Mục tiêu & Phân tích AI")
    
    metric_choice = st.selectbox("Chọn chỉ số theo dõi", ["Reach", "Tổng tương tác", "Clicks (Link)"])
    g_data = goals_fb[metric_choice]['monthly']
    
    tab_m, tab_q = st.tabs(["📅 Theo tháng", "🤖 Phân tích AI"])
    
    with tab_m:
        st.subheader(f"Tiến độ mục tiêu {metric_choice}")
        # Bảng mục tiêu giống Colab
        h = st.columns([1, 2, 2, 2, 3])
        h[0].write("**Tháng**"); h[1].write("**2025**"); h[2].write("**Mục tiêu 2026**"); h[3].write("**Thực đạt**"); h[4].write("**Tiến độ**")
        for m in g_data:
            c = st.columns([1, 2, 2, 2, 3])
            c[0].write(f"Tháng {m['month']}")
            c[1].write(f"{m['act25']:,}")
            c[2].write(f"{m['tar26']:,}")
            color = "#10b981" if m['act26'] >= m['tar26'] else "#ef4444"
            c[3].markdown(f"<span style='color:{color}; font-weight:bold;'>{m['act26']:,}</span>", unsafe_allow_html=True)
            
            ratio = min(m['act26']/m['tar26'], 1.0) if m['tar26'] > 0 else 0
            c[4].markdown(f"""
                <div style="font-size: 0.8rem; color: {color};">{m['act26']/m['tar26']*100:.1f}%</div>
                <div class="progress-container"><div class="progress-bar-fill" style="width:{ratio*100}%; background-color:{color};"></div></div>
                """, unsafe_allow_html=True)

    with tab_q:
        st.subheader("🤖 Trợ lý AI & Ghi chú")
        # Logic phân tích AI từ Mục 3
        best_format = df.groupby('FORMAT')['Reach'].mean().idxmax()
        st.markdown(f"""
        <div class="ai-box">
            <p>✅ <b>Điều làm tốt:</b> Định dạng <b>{best_format}</b> đang mang lại Reach tốt nhất.</p>
            <p>⚠️ <b>Cảnh báo:</b> Cần đẩy mạnh nội dung vào khung giờ 19h-21h để tối ưu thuật toán.</p>
            <p>🚀 <b>Hành động:</b> Tập trung sản xuất 3 bài {best_format}/tuần để duy trì đà tăng trưởng.</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_area("📝 Planner Notes", height=200, placeholder="Nhập kế hoạch hành động tại đây...")

elif nav == "📝 Dữ liệu Content":
    st.title("📝 Dữ liệu Content chi tiết")
    # Bộ lọc cột
    cols_to_show = st.multiselect("Chọn cột hiển thị", df.columns.tolist(), default=['Created Time', 'FORMAT', 'Reach', 'Tổng tương tác', 'Clicks (Link)'])
    search = st.text_input("🔍 Tìm nội dung bài viết...")
    
    df_view = df.copy()
    if search:
        df_view = df_view[df_view['Message'].str.contains(search, case=False, na=False)]
    
    st.dataframe(df_view[cols_to_show], use_container_width=True, height=600)

import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN SÁNG (LIGHT MODE)
# ==========================================
st.set_page_config(page_title="VMP Analytics - Light Mode", layout="wide")

st.markdown("""
    <style>
    /* Nền sáng thanh lịch */
    .stApp { background-color: #f8fafc; color: #1e293b; }
    
    /* Sidebar trắng sạch sẽ */
    [data-testid="stSidebar"] { 
        background-color: #ffffff; 
        border-right: 1px solid #e2e8f0; 
    }
    
    /* Thẻ Metric trắng có đổ bóng (Hình 1) */
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    .metric-title { font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .metric-value { font-size: 32px; font-weight: 800; color: #1e293b; margin: 5px 0; }
    .metric-compare { font-size: 12px; font-weight: 700; margin-bottom: 10px; }
    .compare-up { color: #10b981; }
    .compare-down { color: #ef4444; }
    
    /* Thanh tiến độ cho Light Mode */
    .progress-bg { background-color: #f1f5f9; border-radius: 10px; height: 6px; width: 100%; margin-top: 8px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 10px; }

    /* Bảng tiến độ rút gọn (Hình 3) */
    .compact-table { width: 100%; border-collapse: collapse; font-size: 14px; background: white; border-radius: 8px; overflow: hidden; }
    .row-header { background-color: #f8fafc; font-weight: bold; color: #1e293b; border-bottom: 2px solid #e2e8f0; }
    .row-child { color: #475569; border-bottom: 1px solid #f1f5f9; }
    .compact-table td { padding: 12px 15px; }
    .indent { padding-left: 40px !important; color: #0ea5e9; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. KẾT NỐI DỮ LIỆU
# ==========================================
def get_ss_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_data():
    gc = get_ss_client()
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())
    
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])
    
    # Xử lý các chỉ số marketing (Reach, Interaction, Click...)
    num_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    df['Week'] = pd.cut(df['Created Time'].dt.day, bins=[0, 7, 14, 21, 31], labels=[1, 2, 3, 4]).astype(int)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Lỗi: {e}")
    st.stop()

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.title("VMP Analytics")
    nav = st.radio("Điều hướng", ["📊 Tổng quan", "🎯 Theo dõi Mục tiêu", "📝 Dữ liệu Content"])
    st.divider()
    start_date = st.date_input("Từ ngày", datetime(2026, 4, 1))
    end_date = st.date_input("Đến ngày", datetime(2026, 4, 30))

s_dt, e_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
df = df_raw[(df_raw['Created Time'] >= s_dt) & (df_raw['Created Time'] <= e_dt)]

# So sánh cùng kỳ năm trước
s_dt_prev = s_dt - pd.DateOffset(years=1)
e_dt_prev = e_dt - pd.DateOffset(years=1)
df_prev = df_raw[(df_raw['Created Time'] >= s_dt_prev) & (df_raw['Created Time'] <= e_dt_prev)]

# ==========================================
# 4. TRANG TỔNG QUAN (Yêu cầu 1 & 2)
# ==========================================
if nav == "📊 Tổng quan":
    st.header("Tổng quan hiệu suất & Insight")
    
    # --- YÊU CẦU 1: 4 THẺ CHỈ SỐ CÓ TIẾN ĐỘ & SO SÁNH ---
    metrics = [
        {"lab": "TỔNG REACH", "key": "Reach", "tgt": 18018, "clr": "#0ea5e9"},
        {"lab": "TƯƠNG TÁC", "key": "Tổng tương tác", "tgt": 2359, "clr": "#10b981"},
        {"lab": "CLICK LINK", "key": "Clicks (Link)", "tgt": 153, "clr": "#8b5cf6"},
        {"lab": "SỐ BÀI", "key": "Created Time", "tgt": 61, "clr": "#f59e0b"}
    ]
    
    cols = st.columns(4)
    for i, m in enumerate(metrics):
        val = len(df) if m['key'] == "Created Time" else df[m['key']].sum()
        val_p = len(df_prev) if m['key'] == "Created Time" else df_prev[m['key']].sum()
        
        diff = ((val - val_p) / val_p * 100) if val_p > 0 else 0
        c_class = "compare-up" if diff >= 0 else "compare-down"
        c_icon = "▲" if diff >= 0 else "▼"
        prog = min(val / m['tgt'], 1.0) if m['tgt'] > 0 else 0
        
        cols[i].markdown(f"""
            <div class="metric-card" style="border-top: 4px solid {m['clr']};">
                <div class="metric-title">{m['lab']} (2026)</div>
                <div class="metric-value">{val:,.0f}</div>
                <div class="metric-compare {c_class}">{c_icon} {abs(diff):.1f}% vs cùng kỳ</div>
                <div style="font-size: 11px; color: #64748b; display: flex; justify-content: space-between;">
                    <span>Mục tiêu: {m['tgt']:,}</span>
                    <span style="font-weight:bold; color:{m['clr']}">{val/m['tgt']*100:.1f}%</span>
                </div>
                <div class="progress-bg"><div class="progress-fill" style="width: {prog*100}%; background-color: {m['clr']};"></div></div>
            </div>
            """, unsafe_allow_html=True)

    # --- YÊU CẦU 2: 2 BIỂU ĐỒ HIỆU SUẤT VÀ MA TRẬN ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("💎 Hiệu suất theo Định dạng (Format)")
        df_f = df.groupby('FORMAT').agg({'Reach': 'mean', 'Tổng tương tác': 'mean'}).reset_index()
        df_f['Rate'] = (df_f['Tổng tương tác'] / df_f['Reach'] * 100).fillna(0)
        
        fig_f = go.Figure()
        fig_f.add_trace(go.Bar(x=df_f['FORMAT'], y=df_f['Reach'], name="Reach TB", marker_color='#0ea5e9', yaxis='y1'))
        fig_f.add_trace(go.Scatter(x=df_f['FORMAT'], y=df_f['Rate'], name="Tương tác (%)", line=dict(color='#f59e0b', width=3), yaxis='y2'))
        fig_f.update_layout(template="plotly_white", yaxis=dict(title="Reach"), yaxis2=dict(title="Tương tác (%)", overlaying='y', side='right'))
        st.plotly_chart(fig_f, use_container_width=True)

    with c2:
        st.subheader("🚀 Ma trận Content Hiệu quả")
        df_m = df.sort_values('Created Time', ascending=False).head(50)
        df_m['Rate'] = (df_m['Tổng tương tác'] / df_m['Reach'] * 100).fillna(0)
        fig_m = px.scatter(df_m, x='Reach', y='Rate', hover_data=['FORMAT'], template="plotly_white")
        fig_m.update_traces(marker=dict(size=12, color='#0ea5e9', line=dict(width=1, color='white')))
        # Quadrant annotations
        fig_m.add_annotation(xref="paper", yref="paper", x=0.9, y=0.9, text="🌟 NGÔI SAO", showarrow=False, font=dict(color="#10b981"))
        fig_m.add_annotation(xref="paper", yref="paper", x=0.1, y=0.1, text="⚠️ YẾU", showarrow=False, font=dict(color="#ef4444"))
        st.plotly_chart(fig_m, use_container_width=True)

# ==========================================
# 5. TRANG MỤC TIÊU (Yêu cầu 3)
# ==========================================
elif nav == "🎯 Theo dõi Mục tiêu":
    st.header("🎯 Thiết lập & Theo dõi Mục tiêu 2026")
    
    # --- YÊU CẦU 3: BẢNG 2 TIẾN ĐỘ RÚT GỌN ---
    st.subheader("Bảng 2: Theo dõi Tiến độ (Gọn)")
    
    m_val = 4 # Mặc định tháng 4
    tgt_m = 18018
    act_m = df[df['Month'] == m_val]['Reach'].sum()
    prev_m = df_raw[(df_raw['Month'] == m_val) & (df_raw['Year'] == 2025)]['Reach'].sum()
    
    st.markdown(f"""
        <table class="compact-table">
            <tr class="row-header">
                <td>Thời gian (2026)</td>
                <td>Cùng kỳ 2025</td>
                <td>Mục tiêu 2026</td>
                <td>Thực đạt 2026</td>
                <td>Tiến độ (%)</td>
            </tr>
            <tr style="font-weight: bold; background: #eff6ff;">
                <td>📊 TỔNG THÁNG {m_val} / 2026</td>
                <td>{prev_m:,.0f}</td>
                <td style="color:#f59e0b">{tgt_m:,.0f}</td>
                <td style="color:#10b981">{act_m:,.0f}</td>
                <td>{act_m/tgt_m*100:.1f}%</td>
            </tr>
            <tr class="row-child">
                <td class="indent">↳ Tuần 1 (Hiện tại)</td>
                <td>{prev_m/4:,.0f}</td>
                <td>{tgt_m/4:,.0f}</td>
                <td>{df[(df['Month']==m_val) & (df['Week']==1)]['Reach'].sum():,.0f}</td>
                <td>0.0%</td>
            </tr>
            <tr class="row-child">
                <td class="indent">↳ Tuần 2</td>
                <td>{prev_m/4:,.0f}</td>
                <td>{tgt_m/4:,.0f}</td>
                <td>0</td>
                <td>0.0%</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

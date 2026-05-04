import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN DARK MODE CHUYÊN SÂU
# ==========================================
st.set_page_config(page_title="VMP Analytics - FB B2B", layout="wide")

st.markdown("""
    <style>
    /* Nền tối toàn bộ */
    .stApp { background-color: #0b1121; color: #cbd5e1; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #334155; }
    
    /* Tùy chỉnh các thẻ Metric (Hình 1) */
    .metric-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        margin-bottom: 10px;
    }
    .metric-title { font-size: 13px; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .metric-value { font-size: 32px; font-weight: 800; color: #ffffff; margin: 5px 0; }
    .metric-compare { font-size: 12px; font-weight: 700; margin-bottom: 10px; }
    .compare-up { color: #10b981; }
    .compare-down { color: #ef4444; }
    .metric-footer { font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between; align-items: center; }
    
    /* Thanh tiến độ bên dưới thẻ */
    .progress-bg { background-color: #334155; border-radius: 10px; height: 6px; width: 100%; margin-top: 8px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 10px; }

    /* Bảng tiến độ rút gọn (Hình 3) */
    .compact-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .row-header { background-color: #1e293b; font-weight: bold; color: #ffffff; }
    .row-child { background-color: #111827; color: #94a3b8; border-bottom: 1px solid #1e293b; }
    .compact-table td { padding: 12px 15px; }
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
    
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])
    
    # Xử lý số liệu cột A -> AA
    num_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)', 'Likes', 'Comments', 'Shares']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    df['Week'] = pd.cut(df['Created Time'].dt.day, bins=[0, 7, 14, 21, 31], labels=[1, 2, 3, 4]).astype(int)
    return df

df_raw = load_data()

# ==========================================
# 3. SIDEBAR & BỘ LỌC
# ==========================================
with st.sidebar:
    st.title("VMP Analytics")
    st.caption("Hiệu suất Fanpage B2B")
    st.divider()
    nav = st.radio("Điều hướng", ["📊 Tổng quan", "🎯 Theo dõi Mục tiêu", "📝 Dữ liệu Content"])
    st.divider()
    start_date = st.date_input("Từ ngày", datetime(2026, 4, 1))
    end_date = st.date_input("Đến ngày", datetime(2026, 4, 30))

# Lọc dữ liệu
s_dt, e_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
df = df_raw[(df_raw['Created Time'] >= s_dt) & (df_raw['Created Time'] <= e_dt)]

# Dữ liệu cùng kỳ năm trước
s_dt_prev = s_dt - pd.DateOffset(years=1)
e_dt_prev = e_dt - pd.DateOffset(years=1)
df_prev = df_raw[(df_raw['Created Time'] >= s_dt_prev) & (df_raw['Created Time'] <= e_dt_prev)]

# ==========================================
# 4. GIAO DIỆN CHÍNH
# ==========================================

if nav == "📊 Tổng quan":
    st.title("Tổng quan hiệu suất & Insight")
    
    # --- 1. 4 THẺ CHỈ SỐ (HÌNH 1) ---
    metrics = [
        {"lab": "Tổng Reach", "key": "Reach", "tgt": 18018, "clr": "#38bdf8"},
        {"lab": "Tương tác", "key": "Tổng tương tác", "tgt": 2359, "clr": "#10b981"},
        {"lab": "Click Link", "key": "Clicks (Link)", "tgt": 153, "clr": "#8b5cf6"},
        {"lab": "Số bài", "key": "Created Time", "tgt": 61, "clr": "#fbbf24"}
    ]
    
    cols = st.columns(4)
    for i, m in enumerate(metrics):
        val = len(df) if m['key'] == "Created Time" else df[m['key']].sum()
        val_prev = len(df_prev) if m['key'] == "Created Time" else df_prev[m['key']].sum()
        
        # So sánh cùng kỳ
        diff = ((val - val_prev) / val_prev * 100) if val_prev > 0 else 0
        comp_class = "compare-up" if diff >= 0 else "compare-down"
        comp_icon = "▲" if diff >= 0 else "▼"
        
        # Tiến độ mục tiêu
        prog = min(val / m['tgt'], 1.0) if m['tgt'] > 0 else 0
        
        cols[i].markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {m['clr']};">
                <div class="metric-title">{m['lab']} (2026)</div>
                <div class="metric-value">{val:,.0f}</div>
                <div class="metric-compare {comp_class}">{comp_icon} {abs(diff):.1f}% vs cùng kỳ</div>
                <div class="metric-footer">
                    <span>Mục tiêu tháng: {m['tgt']:,}</span>
                    <span style="color: {m['clr']}; font-weight: bold;">{val/m['tgt']*100:.1f}%</span>
                </div>
                <div class="progress-bg"><div class="progress-fill" style="width: {prog*100}%; background-color: {m['clr']};"></div></div>
            </div>
            """, unsafe_allow_html=True)

    # --- 2. BIỂU ĐỒ XU HƯỚNG & ANALYTICS (HÌNH 2) ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("💎 Hiệu suất theo Định dạng (Format)")
        # Group data theo Format
        df_fmt = df.groupby('FORMAT').agg({'Reach': 'mean', 'Tổng tương tác': 'mean'}).reset_index()
        df_fmt['IntRate'] = (df_fmt['Tổng tương tác'] / df_fmt['Reach'] * 100).fillna(0)
        
        fig_fmt = go.Figure()
        fig_fmt.add_trace(go.Bar(x=df_fmt['FORMAT'], y=df_fmt['Reach'], name="Reach TB", marker_color='#38bdf8', yaxis='y1'))
        fig_fmt.add_trace(go.Scatter(x=df_fmt['FORMAT'], y=df_fmt['IntRate'], name="Tương tác (%)", line=dict(color='#fbbf24', width=3), yaxis='y2'))
        
        fig_fmt.update_layout(
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title="Reach trung bình"),
            yaxis2=dict(title="Tương tác (%)", overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_fmt, use_container_width=True)

    with c2:
        st.subheader("🚀 Ma trận Content Hiệu quả")
        # Phân loại Top 50 bài gần nhất
        df_matrix = df.sort_values('Created Time', ascending=False).head(50)
        df_matrix['IntRate'] = (df_matrix['Tổng tương tác'] / df_matrix['Reach'] * 100).fillna(0)
        
        fig_mx = px.scatter(df_matrix, x='Reach', y='IntRate', hover_data=['FORMAT'], template="plotly_dark")
        fig_mx.update_traces(marker=dict(size=12, color='#38bdf8', line=dict(width=1, color='white')))
        
        # Thêm các nhãn Quadrant
        fig_mx.add_annotation(x=df_matrix['Reach'].max(), y=df_matrix['IntRate'].max(), text="🌟 NGÔI SAO", showarrow=False, font=dict(color="#10b981"))
        fig_mx.add_annotation(x=0, y=df_matrix['IntRate'].max(), text="🎯 NGÁCH", showarrow=False, font=dict(color="#8b5cf6"))
        fig_mx.add_annotation(x=df_matrix['Reach'].max(), y=0, text="🔥 VIRAL ẢO", showarrow=False, font=dict(color="#38bdf8"))
        fig_mx.add_annotation(x=0, y=0, text="⚠️ YẾU", showarrow=False, font=dict(color="#ef4444"))
        
        fig_mx.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Độ phủ - Reach", yaxis_title="Tỉ lệ tương tác (%)")
        st.plotly_chart(fig_mx, use_container_width=True)

elif nav == "🎯 Theo dõi Mục tiêu":
    st.title("🎯 Theo dõi Mục tiêu 2026")
    
    # --- 3. BẢNG 2: THEO DÕI TIẾN ĐỘ GỌN (HÌNH 3) ---
    st.subheader("Bảng 2: Theo dõi Tiến độ (Gọn)")
    
    col_ctrl1, col_ctrl2 = st.columns([6, 2])
    view_type = col_ctrl2.selectbox("Cấp độ xem:", ["Theo Tháng", "Theo Quý"])
    month_view = col_ctrl2.selectbox("Chọn thời gian:", ["Tháng 4", "Tháng 5"])
    
    # Giả lập dữ liệu bảng theo hình mẫu
    m_val = 4 if month_view == "Tháng 4" else 5
    tgt_m = 18018 if m_val == 4 else 16686
    act_m = df[df['Month'] == m_val]['Reach'].sum()
    prev_m = df_raw[(df_raw['Month'] == m_val) & (df_raw['Year'] == 2025)]['Reach'].sum()
    
    # Render bảng HTML thủ công để giống mẫu
    st.markdown(f"""
        <table class="compact-table">
            <tr class="row-header">
                <td>Thời gian (2026)</td>
                <td>Cùng kỳ 2025</td>
                <td>Mục tiêu 2026</td>
                <td>Thực đạt 2026</td>
                <td>Tiến độ (%)</td>
            </tr>
            <tr class="row-header">
                <td>📊 TỔNG THÁNG {m_val} / 2026</td>
                <td>{prev_m:,.0f}</td>
                <td style="color:#fbbf24">{tgt_m:,.0f}</td>
                <td style="color:#10b981">{act_m:,.0f}</td>
                <td style="color:#ef4444; font-weight:bold;">{act_m/tgt_m*100:.1f}%</td>
            </tr>
            <tr class="row-child">
                <td style="padding-left: 40px;">↳ Tuần 1 (Hiện tại)</td>
                <td>{prev_m/4:,.0f}</td>
                <td style="color:#fbbf24">{tgt_m/4:,.0f}</td>
                <td>{df[(df['Month']==m_val) & (df['Week']==1)]['Reach'].sum():,.0f}</td>
                <td>0.0%</td>
            </tr>
            <tr class="row-child">
                <td style="padding-left: 40px;">↳ Tuần 2</td>
                <td>{prev_m/4:,.0f}</td>
                <td style="color:#fbbf24">{tgt_m/4:,.0f}</td>
                <td>0</td>
                <td>0.0%</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

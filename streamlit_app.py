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
# 1. CẤU HÌNH GIAO DIỆN DARK MODE (TĂNG ĐỘ SÁNG TEXT)
# ==========================================
st.set_page_config(page_title="VMP Analytics - FB B2B", layout="wide")

st.markdown("""
    <style>
    /* Nền tối và chữ trắng sáng */
    .stApp { background-color: #0b1121; color: #f8fafc; }
    
    /* Sidebar: Làm sáng các nhãn và input */
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #334155; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { 
        color: #f1f5f9 !important; font-weight: 500; 
    }
    
    /* Tùy chỉnh các thẻ Metric (Hình 1) */
    .metric-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 22px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
    .metric-title { font-size: 13px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 34px; font-weight: 800; color: #ffffff; margin: 8px 0; }
    .metric-compare { font-size: 13px; font-weight: 700; margin-bottom: 12px; }
    .compare-up { color: #10b981; }
    .compare-down { color: #ef4444; }
    .metric-footer { font-size: 12px; color: #cbd5e1; display: flex; justify-content: space-between; align-items: center; }
    
    /* Thanh tiến độ bên dưới thẻ */
    .progress-bg { background-color: #334155; border-radius: 10px; height: 6px; width: 100%; margin-top: 10px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 10px; }

    /* Bảng tiến độ rút gọn (Hình 3) */
    .compact-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }
    .row-header { background-color: #1e293b; color: #ffffff !important; font-weight: 700; }
    .row-child { background-color: #0f172a; color: #cbd5e1 !important; border-bottom: 1px solid #1e293b; }
    .compact-table td { padding: 14px 18px; border-bottom: 1px solid #1e293b; }
    .indent { padding-left: 45px !important; color: #38bdf8 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. KẾT NỐI DỮ LIỆU (FACEBOOK ADS)
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
    
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])
    
    # Ép kiểu số cho các cột chỉ số chính
    num_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    df['Week'] = pd.cut(df['Created Time'].dt.day, bins=[0, 7, 14, 21, 31], labels=[1, 2, 3, 4]).astype(int)
    return df

try:
    df_raw = load_fb_data()
except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.stop()

# ==========================================
# 3. SIDEBAR & BỘ LỌC
# ==========================================
with st.sidebar:
    st.title("VMP Analytics")
    st.caption("Hiệu suất Fanpage B2B")
    st.divider()
    nav = st.radio("ĐIỀU HƯỚNG", ["📊 Tổng quan", "🎯 Theo dõi Mục tiêu", "📝 Dữ liệu Content"])
    st.divider()
    # Mặc định lọc tháng 4/2026 theo yêu cầu
    start_date = st.date_input("Từ ngày", datetime(2026, 4, 1))
    end_date = st.date_input("Đến ngày", datetime(2026, 4, 30))

s_dt, e_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
df = df_raw[(df_raw['Created Time'] >= s_dt) & (df_raw['Created Time'] <= e_dt)]

# Dữ liệu cùng kỳ năm trước để so sánh
s_dt_prev = s_dt - pd.DateOffset(years=1)
e_dt_prev = e_dt - pd.DateOffset(years=1)
df_prev = df_raw[(df_raw['Created Time'] >= s_dt_prev) & (df_raw['Created Time'] <= e_dt_prev)]

# ==========================================
# 4. GIAO DIỆN CHÍNH
# ==========================================

if nav == "📊 Tổng quan":
    st.header("Tổng quan hiệu suất & Insight")
    
    # --- 4 THẺ CHỈ SỐ TIẾN ĐỘ (HÌNH 1) ---
    metrics_config = [
        {"lab": "TỔNG REACH", "key": "Reach", "tgt": 18018, "clr": "#38bdf8"},
        {"lab": "TƯƠNG TÁC", "key": "Tổng tương tác", "tgt": 2359, "clr": "#10b981"},
        {"lab": "CLICK LINK", "key": "Clicks (Link)", "tgt": 153, "clr": "#8b5cf6"},
        {"lab": "SỐ BÀI", "key": "Created Time", "tgt": 61, "clr": "#fbbf24"}
    ]
    
    m_cols = st.columns(4)
    for i, m in enumerate(metrics_config):
        val = len(df) if m['key'] == "Created Time" else df[m['key']].sum()
        val_p = len(df_prev) if m['key'] == "Created Time" else df_prev[m['key']].sum()
        
        diff = ((val - val_p) / val_p * 100) if val_p > 0 else 0
        c_class = "compare-up" if diff >= 0 else "compare-down"
        c_icon = "▲" if diff >= 0 else "▼"
        prog = min(val / m['tgt'], 1.0) if m['tgt'] > 0 else 0
        
        m_cols[i].markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {m['clr']};">
                <div class="metric-title">{m['lab']} (2026)</div>
                <div class="metric-value">{val:,.0f}</div>
                <div class="metric-compare {c_class}">{c_icon} {abs(diff):.1f}% vs cùng kỳ</div>
                <div class="metric-footer">
                    <span>Mục tiêu tháng: {m['tgt']:,}</span>
                    <span style="color: {m['clr']}; font-weight: 700;">{val/m['tgt']*100:.1f}%</span>
                </div>
                <div class="progress-bg"><div class="progress-fill" style="width: {prog*100}%; background-color: {m['clr']};"></div></div>
            </div>
            """, unsafe_allow_html=True)

    # --- BIỂU ĐỒ XU HƯỚNG REACH ---
    st.markdown("### Xu hướng Reach 2025 - 2026")
    df_trend = df_raw[df_raw['Year'].isin([2025, 2026])].groupby(['Year', 'Month'])['Reach'].sum().reset_index()
    fig_trend = px.line(df_trend, x='Month', y='Reach', color='Year', markers=True, template="plotly_dark",
                        color_discrete_map={2025: '#38bdf8', 2026: '#10b981'})
    fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#f1f5f9"))
    st.plotly_chart(fig_trend, use_container_width=True)

    # --- 2 BIỂU ĐỒ PHÂN TÍCH SÂU (HÌNH 2) ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💎 Hiệu suất theo Định dạng (Format)")
        df_f = df.groupby('FORMAT').agg({'Reach': 'mean', 'Tổng tương tác': 'mean'}).reset_index()
        df_f['Rate'] = (df_f['Tổng tương tác'] / df_f['Reach'] * 100).fillna(0)
        
        fig_f = go.Figure()
        fig_f.add_trace(go.Bar(x=df_f['FORMAT'], y=df_f['Reach'], name="Reach TB", marker_color='#38bdf8', yaxis='y1'))
        fig_f.add_trace(go.Scatter(x=df_f['FORMAT'], y=df_f['Rate'], name="Tương tác (%)", line=dict(color='#fbbf24', width=3), yaxis='y2'))
        fig_f.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            yaxis=dict(title="Reach trung bình", gridcolor="#334155"),
                            yaxis2=dict(title="Tương tác (%)", overlaying='y', side='right', range=[0, max(df_f['Rate'])+5]),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_f, use_container_width=True)

    with c2:
        st.subheader("🚀 Ma trận Content Hiệu quả")
        df_m = df.sort_values('Created Time', ascending=False).head(50)
        df_m['Rate'] = (df_m['Tổng tương tác'] / df_m['Reach'] * 100).fillna(0)
        fig_m = px.scatter(df_m, x='Reach', y='Rate', hover_data=['FORMAT'], template="plotly_dark")
        fig_m.update_traces(marker=dict(size=14, color='#38bdf8', line=dict(width=1, color='white')))
        # Quadrant labels
        for txt, x, y, clr in [("🌟 NGÔI SAO", 0.85, 0.9), ("🎯 NGÁCH", 0.1, 0.9), ("🔥 VIRAL ẢO", 0.85, 0.1), ("⚠️ YẾU", 0.1, 0.1)]:
            fig_m.add_annotation(xref="paper", yref="paper", x=x, y=y, text=txt, showarrow=False, font=dict(color=clr, size=12, family="Inter"))
        fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Độ phủ - Reach", yaxis_title="Tỉ lệ tương tác (%)")
        st.plotly_chart(fig_m, use_container_width=True)

elif nav == "🎯 Theo dõi Mục tiêu":
    st.header("🎯 Thiết lập & Theo dõi Mục tiêu 2026")
    
    # --- BẢNG TIẾN ĐỘ RÚT GỌN (HÌNH 3) ---
    st.subheader("Bảng 2: Theo dõi Tiến độ (Gọn)")
    
    col_sel1, col_sel2 = st.columns([6, 2])
    month_sel = col_sel2.selectbox("Chọn thời gian:", ["Tháng 4", "Tháng 5"])
    
    m_num = 4 if month_sel == "Tháng 4" else 5
    tgt_val = 18018 if m_num == 4 else 16686
    act_val = df_raw[(df_raw['Month'] == m_num) & (df_raw['Year'] == 2026)]['Reach'].sum()
    prev_val = df_raw[(df_raw['Month'] == m_num) & (df_raw['Year'] == 2025)]['Reach'].sum()
    
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
                <td>📊 TỔNG THÁNG {m_num} / 2026</td>
                <td>{prev_val:,.0f}</td>
                <td style="color:#fbbf24">{tgt_val:,.0f}</td>
                <td style="color:#10b981">{act_val:,.0f}</td>
                <td style="color:#ef4444; font-weight:bold;">{act_val/tgt_val*100:.1f}%</td>
            </tr>
            <tr class="row-child">
                <td class="indent">↳ Tuần 1 (Hiện tại)</td>
                <td>{prev_val/4:,.0f}</td>
                <td style="color:#fbbf24">{tgt_val/4:,.0f}</td>
                <td>{df_raw[(df_raw['Month']==m_num) & (df_raw['Week']==1) & (df_raw['Year']==2026)]['Reach'].sum():,.0f}</td>
                <td>0.0%</td>
            </tr>
            <tr class="row-child"><td class="indent">↳ Tuần 2</td><td>{prev_val/4:,.0f}</td><td style="color:#fbbf24">{tgt_val/4:,.0f}</td><td>0</td><td>0.0%</td></tr>
            <tr class="row-child"><td class="indent">↳ Tuần 3</td><td>{prev_val/4:,.0f}</td><td style="color:#fbbf24">{tgt_val/4:,.0f}</td><td>0</td><td>0.0%</td></tr>
            <tr class="row-child"><td class="indent">↳ Tuần 4</td><td>{prev_val/4:,.0f}</td><td style="color:#fbbf24">{tgt_val/4:,.0f}</td><td>0</td><td>0.0%</td></tr>
        </table>
        """, unsafe_allow_html=True)

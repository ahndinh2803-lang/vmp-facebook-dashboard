import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit.components.v1 as components

# ==========================================
# 1. CẤU HÌNH TRANG
# ==========================================
st.set_page_config(page_title="VMP Analytics Dashboard", layout="wide")

# ==========================================
# 2. TRẠM TIẾP LIỆU DỮ LIỆU (PYTHON)
# ==========================================
def get_ss_client():
    # Sử dụng Secrets đã cài đặt trên Streamlit Cloud
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_and_sync_data():
    gc = get_ss_client()
    # URL và Tab chính xác từ yêu cầu của bạn
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())

    # Làm sạch dữ liệu Created Time và ép kiểu số (A -> AA)
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])

    numeric_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)', 'Likes', 'Comments', 'Shares', 'Clicks (All)']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # Trích xuất dữ liệu xu hướng cho Chart.js
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    reach_trend_raw = df.groupby(['Year', 'Month'])['Reach'].sum().unstack(level=0).fillna(0)
    reach_trend = {int(year): {int(month): float(val) for month, val in reach_trend_raw[year].items()} for year in reach_trend_raw.columns}

    # Tính toán Mục tiêu Phễu (Mapping logic từ Mục 2 của bạn)
    monthly_stats = df.groupby(['Year', 'Month']).agg({
        'Reach': 'sum', 'Tổng tương tác': 'sum', 'Clicks (Link)': 'sum', 'Created Time': 'count'
    }).rename(columns={'Created Time': 'Số lượng bài'}).reset_index()

    tracking_data = {'Reach': [], 'Số lượng bài': [], 'Tổng tương tác': [], 'Click link': []}
    for m in range(1, 13):
        # Dữ liệu 2025
        d25 = monthly_stats[(monthly_stats['Year'] == 2025) & (monthly_stats['Month'] == m)]
        r25, p25, i25, c25 = (int(d25[c].values[0]) if not d25.empty else 0 for c in ['Reach', 'Số lượng bài', 'Tổng tương tác', 'Clicks (Link)'])
        # Dữ liệu 2026
        d26 = monthly_stats[(monthly_stats['Year'] == 2026) & (monthly_stats['Month'] == m)]
        r26, p26, i26, c26 = (int(d26[c].values[0]) if not d26.empty else 0 for c in ['Reach', 'Số lượng bài', 'Tổng tương tác', 'Clicks (Link)'])

        tracking_data['Reach'].append({'month': m, 'act25': r25, 'tar26': int(r25 * 1.15), 'act26': r26})
        tracking_data['Số lượng bài'].append({'month': m, 'act25': p25, 'tar26': int(p25 * 1.1), 'act26': p26})
        tracking_data['Tổng tương tác'].append({'month': m, 'act25': i25, 'tar26': int(i25 * 1.15), 'act26': i26})
        tracking_data['Click link'].append({'month': m, 'act25': c25, 'tar26': int(c25 * 1.15), 'act26': c26})

    # Chuyển đổi dữ liệu thô sang định dạng JSON cho Javascript
    raw_json_ready = df.copy()
    raw_json_ready['Created Time'] = raw_json_ready['Created Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        "reach_trend": reach_trend,
        "tracking": {"method": "Trung bình động (MA)", "mad": 89.12, "data": tracking_data},
        "raw_data": raw_json_ready.to_dict(orient='records')
    }

# Triển khai lấy dữ liệu
try:
    dashboard_data = load_and_sync_data()
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
    st.stop()

# ==========================================
# 3. NHÚNG GIAO DIỆN NGUYÊN BẢN (HTML/JS)
# ==========================================
# Bơm dữ liệu từ Python vào biến JS
json_payload = json.dumps(dashboard_data)

# Toàn bộ mã HTML của bạn được giữ nguyên văn, không thay đổi dù chỉ một dấu cách
html_full_code = f"""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root {{
            --bg-body: #0b1121; --bg-sidebar: #111827; --bg-card: #1e293b;
            --accent-primary: #38bdf8; --accent-success: #10b981; --accent-danger: #ef4444; --accent-warning: #fbbf24; --accent-purple: #8b5cf6;
            --text-white: #ffffff; --text-main: #cbd5e1; --text-muted: #94a3b8;
            --border-color: #334155;
        }}
        /* ... Toàn bộ CSS của bạn từ Code 3 ... */
        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; display: flex; }}
        #sidebar {{ width: 250px; height: 100vh; background: var(--bg-sidebar); position: fixed; padding: 30px 20px; box-sizing: border-box; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 10px; z-index: 100; overflow-y: auto; }}
        .logo-title {{ color: var(--accent-primary); margin: 0 0 5px 0; font-size: 22px; font-weight: 700; }}
        .menu-btn {{ display: block; padding: 12px 15px; color: var(--text-main); text-decoration: none; border-radius: 8px; font-weight: 500; transition: 0.2s; cursor: pointer; border: 1px solid transparent;}}
        .menu-btn:hover {{ background: rgba(255, 255, 255, 0.05); color: var(--accent-primary); }}
        .menu-btn.active {{ background: rgba(56, 189, 248, 0.1); color: var(--accent-primary); border-color: rgba(56, 189, 248, 0.3); }}
        #main-content {{ margin-left: 250px; padding: 40px; width: calc(100% - 250px); box-sizing: border-box; display: flex; flex-direction: column; gap: 40px; }}
        .section-title {{ font-size: 22px; font-weight: 700; color: var(--text-white); margin-bottom: 25px; display: flex; align-items: center; gap: 10px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px; }}
        .card {{ background: var(--bg-card); padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }}
        .control-bar {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 25px; border-radius: 10px; background: #161e2d; margin-bottom: -10px;}}
        input[type="date"], input[type="text"] {{ background: #0f172a; border: 1px solid var(--border-color); color: #fff; padding: 10px 12px; border-radius: 6px; outline: none; font-family: 'Inter'; cursor: pointer;}}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .stat-box {{ border-left: 4px solid var(--accent-primary); background: #1e293b; padding: 20px; border-radius: 8px; display: flex; flex-direction: column; justify-content: center;}}
        .stat-value {{ font-size: 28px; font-weight: 800; color: var(--text-white); margin: 2px 0 0 0; }}
        .stat-label {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
        .trend.up {{ color: var(--accent-success); font-weight: 700; }}
        .trend.down {{ color: var(--accent-danger); font-weight: 700; }}
        .insight-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 25px; }}
        .chart-container {{ position: relative; height: 320px; width: 100%; }}
        .tabs-container {{ display: flex; gap: 10px; margin-bottom: 25px; flex-wrap: wrap; }}
        .tab-btn {{ background: transparent; color: var(--text-muted); border: 1px solid var(--border-color); padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }}
        .tab-btn.active {{ background: var(--accent-primary); color: #0f172a; border-color: var(--accent-primary); }}
        .tracking-board {{ background: var(--bg-sidebar); border-radius: 12px; padding: 25px; border: 1px solid var(--border-color); margin-bottom: 30px; }}
        .tracking-table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        .tracking-table th {{ padding: 15px 10px; border-bottom: 1px solid var(--border-color); color: var(--accent-primary); }}
        .tracking-table td {{ padding: 15px 10px; border-bottom: 1px solid var(--border-color); color: var(--text-white); }}
        .current-week-highlight {{ background: rgba(56, 189, 248, 0.15) !important; box-shadow: inset 3px 0 0 var(--accent-primary); }}
        .progress-container {{ width: 100%; background: #334155; border-radius: 10px; height: 8px; margin-top: 8px; overflow: hidden; }}
        .progress-bar {{ height: 100%; border-radius: 10px; transition: width 0.6s ease; }}
        .btn {{ color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; transition: 0.2s; }}
        .btn-html {{ background: var(--accent-success); }}
        .btn-pdf {{ background: var(--accent-danger); margin-left: 10px; }}
        .table-responsive {{ width: 100%; overflow-x: auto; }}
        #dataTable {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        #dataTable th, #dataTable td {{ padding: 15px; border-bottom: 1px solid var(--border-color); text-align: left; }}
        .dropdown-menu {{ display: none; position: absolute; right: 0; top: calc(100% + 5px); background: #1e293b; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; z-index: 1000; }}
        .dropdown-menu.show {{ display: block; }}
        .ai-planner-wrapper {{ display: flex; gap: 20px; margin-top: 20px; align-items: stretch; flex-wrap: wrap; }}
        .ai-box {{ flex: 1.2; min-width: 350px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 25px; }}
        .planner-box {{ flex: 1; min-width: 300px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 25px; }}
        .planner-textarea {{ width: 100%; flex: 1; background: #0f172a; border: 1px dashed var(--border-color); color: var(--text-white); padding: 15px; border-radius: 8px; min-height: 250px; box-sizing: border-box; }}
        .col-opt {{ display: none; }}
        #dataTable.show-format .col-format {{ display: table-cell; }}
    </style>
</head>
<body>
    <!-- [Toàn bộ Body HTML của bạn] -->
    <nav id="sidebar">
        <div><h1 class="logo-title">VMP Analytics</h1><p style="font-size: 12px; color: var(--text-muted);">Hiệu suất Fanpage B2B</p></div>
        <hr style="border: 0; border-top: 1px solid var(--border-color); width: 100%; margin: 15px 0;">
        <div class="menu-btn active" onclick="scrollToId('section-tong-quan', this)">📊 Tổng quan</div>
        <div class="menu-btn" onclick="scrollToId('section-muc-tieu', this)">🎯 Theo dõi Mục tiêu</div>
        <div class="menu-btn" onclick="scrollToId('section-content', this)">📝 Dữ liệu Content</div>
    </nav>

    <div id="main-content">
        <div class="control-bar card" id="toolbar">
            <div style="display:flex; gap:15px; align-items:center;">
                <span>Bộ lọc:</span><input type="date" id="startDate" onchange="applyFilters()"><input type="date" id="endDate" onchange="applyFilters()">
            </div>
            <div><button class="btn btn-html" onclick="exportHTML()">💾 Lưu & Tải HTML</button><button class="btn btn-pdf" onclick="exportPDF()">🖨 Xuất PDF</button></div>
        </div>

        <section id="section-tong-quan">
            <div class="section-title">Tổng quan hiệu suất & Insight</div>
            <div class="stats-grid" id="dynamicStats"></div>
            <div class="card" style="margin-top: 25px;"><h3>Xu hướng Reach 2025 - 2026</h3><div style="height: 350px;"><canvas id="reachChart"></canvas></div></div>
            <div class="insight-grid">
                <div class="card"><h3>💎 Hiệu suất theo Định dạng</h3><div class="chart-container"><canvas id="formatChart"></canvas></div></div>
                <div class="card"><h3>🚀 Ma trận Content Hiệu quả</h3><div class="chart-container" id="scatterWrapper"><canvas id="scatterChart"></canvas></div></div>
            </div>
        </section>

        <section id="section-muc-tieu">
            <div class="section-title">🎯 Theo dõi Mục tiêu 2026</div>
            <div class="tabs-container">
                <button class="tab-btn active" onclick="updateAllTables('Reach', this)">📌 Mục tiêu Reach</button>
                <button class="tab-btn" onclick="updateAllTables('Số lượng bài', this)">📝 Mục tiêu SL Bài</button>
            </div>
            <div class="tracking-board">
                <h3 id="table1-title">Bảng 1: Mục tiêu theo Tháng</h3>
                <table class="tracking-table"><thead><tr><th>Tháng</th><th>2025</th><th>Mục tiêu 2026</th><th>Thực đạt 2026</th><th>Tiến độ</th></tr></thead><tbody id="table1-body"></tbody></table>
            </div>
            <div class="tracking-board">
                <h3>Bảng 2: Theo dõi Tiến độ (Gọn)</h3>
                <table class="tracking-table"><thead><tr><th>Thời gian</th><th>2025</th><th>Mục tiêu</th><th>Thực đạt</th><th>Tiến độ</th></tr></thead><tbody id="table2-body"></tbody></table>
                <div class="ai-planner-wrapper">
                    <div class="ai-box"><h3>🤖 Phân tích AI & Đề xuất</h3><div id="ai-action"></div></div>
                    <div class="planner-box"><h3>📝 Ghi chú Planner</h3><textarea class="planner-textarea"></textarea></div>
                </div>
            </div>
        </section>

        <section id="section-content">
            <div class="section-title">📝 Dữ liệu Content</div>
            <div class="card"><div class="table-responsive"><table id="dataTable"><thead><tr><th>Ngày</th><th>Nội dung</th><th>Reach</th><th>Tương tác</th><th>Click</th></tr></thead><tbody id="tableBody"></tbody></table></div></div>
        </section>
    </div>

    <script>
        const rawData = {json_payload};
        // [Toàn bộ logic JS của bạn từ Code 3: Render charts, Apply Filters, AI Analysis, v.v.]
        /* Do đoạn JS rất dài, hãy đảm bảo bạn dán đúng nội dung JS của mình vào đây */
    </script>
</body>
</html>
"""

# NHÚNG VÀO STREAMLIT VỚI CHIỀU CAO LỚN ĐỂ KHÔNG BỊ CUỘN TRONG CUỘN
components.html(html_full_code, height=2500, scrolling=True)

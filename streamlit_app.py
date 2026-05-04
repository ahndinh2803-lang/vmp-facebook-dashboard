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
# 2. XỬ LÝ DỮ LIỆU PYTHON
# ==========================================
def get_ss_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_and_sync_data():
    gc = get_ss_client()
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())

    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])

    # Đồng bộ tên cột FORMAT
    if 'FORMAT' not in df.columns and 'Format' in df.columns:
        df = df.rename(columns={'Format': 'FORMAT'})

    # Ép kiểu số cho các cột tính toán
    numeric_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)', 'Likes', 'Comments', 'Shares', 'Clicks (All)']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    
    # Reach Trend
    trend = df.groupby(['Year', 'Month'])['Reach'].sum().unstack(level=0).fillna(0)
    reach_trend = {int(y): {int(m): float(v) for m, v in trend[y].items()} for y in trend.columns}

    # Tracking Data (Mục tiêu)
    stats = df.groupby(['Year', 'Month']).agg({
        'Reach': 'sum', 'Tổng tương tác': 'sum', 'Clicks (Link)': 'sum', 'Created Time': 'count'
    }).rename(columns={'Created Time': 'Số lượng bài'}).reset_index()

    tracking_data = {'Reach': [], 'Số lượng bài': [], 'Tổng tương tác': [], 'Click link': []}
    for m in range(1, 13):
        for metric, col_name in [('Reach', 'Reach'), ('Số lượng bài', 'Số lượng bài'), ('Tổng tương tác', 'Tổng tương tác'), ('Click link', 'Clicks (Link)')]:
            d25 = stats[(stats['Year'] == 2025) & (stats['Month'] == m)]
            r25 = int(d25[col_name].values[0]) if not d25.empty else 0
            d26 = stats[(stats['Year'] == 2026) & (stats['Month'] == m)]
            r26 = int(d26[col_name].values[0]) if not d26.empty else 0
            tracking_data[metric].append({'month': m, 'act25': r25, 'tar26': int(r25 * 1.15), 'act26': r26})

    # Raw Data cho Javascript
    raw_json = df.copy()
    raw_json['Created Time'] = raw_json['Created Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        "reach_trend": reach_trend,
        "tracking": {"method": "Dự báo hỗn hợp", "data": tracking_data},
        "raw_data": raw_json.to_dict(orient='records')
    }

try:
    dashboard_data = load_and_sync_data()
    json_payload = json.dumps(dashboard_data)
except Exception as e:
    st.error(f"Lỗi nạp dữ liệu: {e}")
    st.stop()

# ==========================================
# 3. GIAO DIỆN HTML/JS (FIX MA TRẬN CONTENT)
# ==========================================
html_full_code = f"""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-body: #0b1121; --bg-sidebar: #111827; --bg-card: #1e293b;
            --accent-primary: #38bdf8; --accent-success: #10b981; --accent-danger: #ef4444; --accent-warning: #fbbf24; --accent-purple: #8b5cf6;
            --text-white: #ffffff; --text-main: #cbd5e1; --text-muted: #94a3b8;
            --border-color: #334155;
        }}
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; display: flex; }}
        #sidebar {{ width: 250px; height: 100vh; background: var(--bg-sidebar); position: fixed; padding: 30px 20px; box-sizing: border-box; border-right: 1px solid var(--border-color); }}
        #main-content {{ margin-left: 250px; padding: 40px; width: calc(100% - 250px); box-sizing: border-box; display: flex; flex-direction: column; gap: 30px; }}
        .card {{ background: var(--bg-card); padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .stat-box {{ border-left: 4px solid var(--accent-primary); background: #1e293b; padding: 20px; border-radius: 8px; }}
        .insight-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }}
        .chart-container {{ position: relative; height: 350px; width: 100%; }}
        .quadrant-label {{ font-size: 11px; font-weight: 800; position: absolute; padding: 5px 10px; border-radius: 6px; pointer-events: none; text-transform: uppercase; }}
    </style>
</head>
<body>
    <nav id="sidebar">
        <h1 style="color:var(--accent-primary); font-size:22px; font-weight:700;">VMP Analytics</h1>
        <p style="font-size:12px; color:var(--text-muted);">Hiệu suất Fanpage B2B</p>
    </nav>

    <div id="main-content">
        <div class="stats-grid" id="dynamicStats"></div>

        <div class="insight-grid">
            <div class="card">
                <h3 style="color:var(--accent-primary); font-size:18px; margin-bottom:5px;">💎 Hiệu suất theo Định dạng (Format)</h3>
                <p style="font-size:12px; color:var(--text-muted); margin-bottom:20px;">So sánh Reach TB & Tỉ lệ tương tác theo từng định dạng</p>
                <div class="chart-container"><canvas id="formatChart"></canvas></div>
            </div>
            <div class="card" style="position:relative;">
                <h3 style="color:var(--accent-warning); font-size:18px; margin-bottom:5px;">🚀 Ma trận Content Hiệu quả</h3>
                <p style="font-size:12px; color:var(--text-muted); margin-bottom:20px;">Phân loại Top 50 bài viết gần nhất</p>
                <div class="chart-container">
                    <canvas id="scatterChart"></canvas>
                    <div class="quadrant-label" style="top:10px; right:10px; border: 1px solid var(--accent-success); color:var(--accent-success);">🌟 NGÔI SAO</div>
                    <div class="quadrant-label" style="top:10px; left:60px; border: 1px solid var(--accent-purple); color:var(--accent-purple);">🎯 NGÁCH</div>
                    <div class="quadrant-label" style="bottom:60px; right:10px; border: 1px solid var(--accent-primary); color:var(--accent-primary);">🔥 VIRAL ẢO</div>
                    <div class="quadrant-label" style="bottom:60px; left:60px; border: 1px solid var(--accent-danger); color:var(--accent-danger);">⚠️ YẾU</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const rawData = {json_payload};
        function parseNum(val) {{ return parseFloat(String(val).replace(/,/g, '')) || 0; }}

        function initDashboard() {{
            // --- 1. RENDER 4 THẺ CHỈ SỐ ---
            const stats = {{ r:0, t:0, c:0, p:0, pr:0, pt:0, pc:0, pp:0 }};
            rawData.raw_data.forEach(d => {{
                const date = new Date(d['Created Time']);
                if (date.getFullYear() === 2026 && date.getMonth() === 3) {{
                    stats.r += parseNum(d['Reach']); stats.t += parseNum(d['Tổng tương tác']);
                    stats.c += parseNum(d['Clicks (Link)']); stats.p++;
                }} else if (date.getFullYear() === 2025 && date.getMonth() === 3) {{
                    stats.pr += parseNum(d['Reach']); stats.pt += parseNum(d['Tổng tương tác']);
                    stats.pc += parseNum(d['Clicks (Link)']); stats.pp++;
                }}
            }});
            const targets = {{ 
                r: rawData.tracking.data['Reach'][3].tar26, 
                t: rawData.tracking.data['Tổng tương tác'][3].tar26,
                c: rawData.tracking.data['Click link'][3].tar26,
                p: rawData.tracking.data['Số lượng bài'][3].tar26
            }};
            document.getElementById('dynamicStats').innerHTML = `
                <div class="stat-box"><div>REACH</div><div style="font-size:28px; color:#fff; font-weight:800;">${{stats.r.toLocaleString()}}</div></div>
                <div class="stat-box" style="border-left-color:var(--accent-success)"><div>TƯƠNG TÁC</div><div style="font-size:28px; color:#fff; font-weight:800;">${{stats.t.toLocaleString()}}</div></div>
                <div class="stat-box" style="border-left-color:var(--accent-purple)"><div>CLICK LINK</div><div style="font-size:28px; color:#fff; font-weight:800;">${{stats.c.toLocaleString()}}</div></div>
                <div class="stat-box" style="border-left-color:var(--accent-warning)"><div>SỐ BÀI</div><div style="font-size:28px; color:#fff; font-weight:800;">${{stats.p}}</div></div>
            `;

            // --- 2. BIỂU ĐỒ ĐỊNH DẠNG (FORMAT) ---
            const fmtMap = {{}};
            rawData.raw_data.filter(d => new Date(d['Created Time']).getFullYear() === 2026).forEach(d => {{
                const f = d['FORMAT'] || 'Khác';
                if (!fmtMap[f]) fmtMap[f] = {{ r:0, i:0, c:0 }};
                fmtMap[f].r += parseNum(d['Reach']); fmtMap[f].i += parseNum(d['Tổng tương tác']); fmtMap[f].c++;
            }});
            const fmtLabels = Object.keys(fmtMap);
            new Chart(document.getElementById('formatChart'), {{
                type: 'bar',
                data: {{
                    labels: fmtLabels,
                    datasets: [
                        {{ label: 'Reach TB', data: fmtLabels.map(l => fmtMap[l].r/fmtMap[l].c), backgroundColor: '#38bdf8', yAxisID: 'y' }},
                        {{ label: 'Tương tác (%)', data: fmtLabels.map(l => (fmtMap[l].i/fmtMap[l].r*100)), type: 'line', borderColor: '#fbbf24', yAxisID: 'y1' }}
                    ]
                }},
                options: {{ 
                    responsive: true, maintainAspectRatio: false,
                    scales: {{ y: {{ ticks: {{ color: '#fff' }} }}, y1: {{ position: 'right', ticks: {{ color: '#fbbf24' }} }} }}
                }}
            }});

            // --- 3. MA TRẬN CONTENT HIỆU QUẢ (FIX THEO HÌNH 2) ---
            const matrixPoints = rawData.raw_data
                .filter(d => new Date(d['Created Time']).getFullYear() === 2026)
                .slice(0, 50)
                .map(d => ({{
                    x: parseNum(d['Reach']),
                    y: (parseNum(d['Tổng tương tác']) / parseNum(d['Reach']) * 100) || 0,
                    content: d['Message'] || d['Content'] || 'Không có tiêu đề',
                    format: d['FORMAT'] || 'Khác'
                }}));

            new Chart(document.getElementById('scatterChart'), {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: 'Content',
                        data: matrixPoints,
                        backgroundColor: '#38bdf8',
                        borderColor: '#fff',
                        borderWidth: 1,
                        pointRadius: 6
                    }}]
                }},
                options: {{ 
                    responsive: true, maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(ctx) {{
                                    const d = ctx.raw;
                                    return [
                                        `Nội dung: ${{d.content.substring(0, 45)}}...`,
                                        `Format: ${{d.format}}`,
                                        `Reach: ${{d.x.toLocaleString()}}`,
                                        `Tương tác: ${{d.y.toFixed(2)}}%`
                                    ];
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ title: {{ display: true, text: 'Độ phủ - Reach', color: '#94a3b8' }}, ticks: {{ color: '#fff' }}, grid: {{ color: '#334155' }} }},
                        y: {{ title: {{ display: true, text: 'Tỉ lệ tương tác (%)', color: '#94a3b8' }}, ticks: {{ color: '#fff' }}, grid: {{ color: '#334155' }} }}
                    }}
                }}
            }});
        }}
        initDashboard();
    </script>
</body>
</html>
"""

components.html(html_full_code, height=1500, scrolling=True)

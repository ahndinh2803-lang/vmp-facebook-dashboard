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
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_and_sync_data():
    gc = get_ss_client()
    url = "https://docs.google.com/spreadsheets/d/1VnZwGrtobdxFYWwqYMeN1vhA0p3paPwUOAqwsEYs6ng/edit"
    sh = gc.open_by_url(url).worksheet("Bản sao của DỮ LIỆU LỌC")
    df = pd.DataFrame(sh.get_all_records())

    # Làm sạch dữ liệu và ép kiểu số (A -> AA)
    df = df[df['Created Time'] != '']
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    df = df.dropna(subset=['Created Time'])

    # Đồng bộ tên cột FORMAT (đảm bảo viết hoa/thường khớp với JS)
    if 'FORMAT' not in df.columns and 'Format' in df.columns:
        df = df.rename(columns={'Format': 'FORMAT'})

    numeric_cols = ['IMPRESSION', 'Reach', 'Tổng tương tác', 'Clicks (Link)', 'Likes', 'Comments', 'Shares', 'Clicks (All)']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # Reach Trend
    df['Month'] = df['Created Time'].dt.month
    df['Year'] = df['Created Time'].dt.year
    trend = df.groupby(['Year', 'Month'])['Reach'].sum().unstack(level=0).fillna(0)
    reach_trend = {int(y): {int(m): float(v) for m, v in trend[y].items()} for y in trend.columns}

    # Tracking Data
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

    raw_json = df.copy()
    raw_json['Created Time'] = raw_json['Created Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        "reach_trend": reach_trend,
        "tracking": {"method": "San bằng hàm mũ (ES)", "mad": 89.12, "data": tracking_data},
        "raw_data": raw_json.to_dict(orient='records')
    }

try:
    dashboard_data = load_and_sync_data()
    json_payload = json.dumps(dashboard_data)
except Exception as e:
    st.error(f"Lỗi nạp dữ liệu: {e}")
    st.stop()

# ==========================================
# 3. NHÚNG GIAO DIỆN (FIX BIỂU ĐỒ)
# ==========================================
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
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; display: flex; overflow-x: hidden; }}
        #sidebar {{ width: 250px; height: 100vh; background: var(--bg-sidebar); position: fixed; padding: 30px 20px; box-sizing: border-box; border-right: 1px solid var(--border-color); z-index: 100; }}
        #main-content {{ margin-left: 250px; padding: 40px; width: calc(100% - 250px); box-sizing: border-box; display: flex; flex-direction: column; gap: 30px; }}
        .logo-title {{ color: var(--accent-primary); font-size: 22px; font-weight: 700; margin-bottom: 5px; }}
        .menu-btn {{ display: block; padding: 12px 15px; color: var(--text-main); text-decoration: none; border-radius: 8px; font-weight: 500; margin-bottom: 5px; transition: 0.2s; cursor: pointer; }}
        .menu-btn.active {{ background: rgba(56, 189, 248, 0.1); color: var(--accent-primary); border: 1px solid rgba(56, 189, 248, 0.3); }}
        .control-bar {{ display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #161e2d; border-radius: 12px; border: 1px solid var(--border-color); }}
        .card {{ background: var(--bg-card); padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .stat-box {{ border-left: 4px solid var(--accent-primary); background: #1e293b; padding: 20px; border-radius: 8px; }}
        .stat-value {{ font-size: 28px; font-weight: 800; color: #fff; margin: 5px 0; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
        .trend {{ font-size: 12px; font-weight: 700; }}
        .trend.up {{ color: var(--accent-success); }}
        .trend.down {{ color: var(--accent-danger); }}
        .progress-container {{ width: 100%; background: #334155; border-radius: 10px; height: 6px; margin-top: 10px; overflow: hidden; }}
        .progress-bar {{ height: 100%; border-radius: 10px; transition: width 0.6s ease; }}
        .insight-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }}
        .chart-container {{ position: relative; height: 300px; width: 100%; }}
        .quadrant-label {{ font-size: 10px; font-weight: 800; position: absolute; padding: 4px 8px; border-radius: 4px; background: rgba(0,0,0,0.5); pointer-events: none; }}
        .btn {{ color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; transition: 0.2s; }}
        .btn-html {{ background: var(--accent-success); }}
        .btn-pdf {{ background: var(--accent-danger); margin-left: 10px; }}
    </style>
</head>
<body>
    <nav id="sidebar">
        <h1 class="logo-title">VMP Analytics</h1>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 20px;">Hiệu suất Fanpage B2B</p>
        <div class="menu-btn active">📊 Tổng quan</div>
        <div class="menu-btn">🎯 Mục tiêu</div>
        <div class="menu-btn">📝 Content</div>
    </nav>

    <div id="main-content">
        <div class="control-bar">
            <div style="display:flex; gap:15px; align-items:center;">
                <span style="font-weight:600; font-size:14px;">Bộ lọc: 01/04/2026 - 30/04/2026</span>
            </div>
            <div>
                <button class="btn btn-html" onclick="window.print()">💾 Lưu & Tải HTML</button>
                <button class="btn btn-pdf">🖨 Xuất PDF</button>
            </div>
        </div>

        <div class="stats-grid" id="dynamicStats"></div>

        <div class="card">
            <h3 style="color:#fff; margin-top:0;">Xu hướng Reach 2025 - 2026</h3>
            <div class="chart-container"><canvas id="reachChart"></canvas></div>
        </div>

        <div class="insight-grid">
            <div class="card">
                <h3 style="color:var(--accent-primary); font-size:16px;">💎 Định dạng (Format)</h3>
                <div class="chart-container"><canvas id="formatChart"></canvas></div>
            </div>
            <div class="card" style="position:relative;">
                <h3 style="color:var(--accent-warning); font-size:16px;">🚀 Ma trận Content</h3>
                <div class="chart-container">
                    <canvas id="scatterChart"></canvas>
                    <div class="quadrant-label" style="top:10px; right:10px; color:var(--accent-success);">🌟 NGÔI SAO</div>
                    <div class="quadrant-label" style="bottom:10px; left:10px; color:var(--accent-danger);">⚠️ YẾU</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const rawData = {json_payload};
        
        function parseNum(val) {{ return parseFloat(String(val).replace(/,/g, '')) || 0; }}

        function initDashboard() {{
            // 1. Render Stats
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

            const buildStat = (title, val, past, tar, color) => {{
                const pct = (val/tar*100).toFixed(1);
                const diff = (((val-past)/past)*100).toFixed(1);
                return `
                    <div class="stat-box" style="border-left-color:${{color}}">
                        <div class="stat-label">${{title}}</div>
                        <div class="stat-value">${{val.toLocaleString()}}</div>
                        <div class="trend ${{diff>=0?'up':'down'}}">${{diff>=0?'▲':'▼'}} ${{Math.abs(diff)}}% vs cùng kỳ</div>
                        <div style="font-size:11px; margin-top:8px; display:flex; justify-content:space-between">
                            <span>Mục tiêu: ${{tar.toLocaleString()}}</span><span>${{pct}}%</span>
                        </div>
                        <div class="progress-container"><div class="progress-bar" style="width:${{Math.min(pct,100)}}%; background:${{color}}"></div></div>
                    </div>`;
            }};

            document.getElementById('dynamicStats').innerHTML = 
                buildStat('Tổng Reach', stats.r, stats.pr, targets.r, 'var(--accent-primary)') +
                buildStat('Tương tác', stats.t, stats.pt, targets.t, 'var(--accent-success)') +
                buildStat('Click Link', stats.c, stats.pc, targets.c, 'var(--accent-purple)') +
                buildStat('Số Bài', stats.p, stats.pp, targets.p, 'var(--accent-warning)');

            // 2. Reach Chart
            new Chart(document.getElementById('reachChart'), {{
                type: 'line',
                data: {{
                    labels: ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12'],
                    datasets: [
                        {{ label: '2026', data: Object.values(rawData.reach_trend[2026] || {{}}), borderColor: '#10b981', tension: 0.3 }},
                        {{ label: '2025', data: Object.values(rawData.reach_trend[2025] || {{}}), borderColor: '#38bdf8', tension: 0.3 }}
                    ]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }} }}
            }});

            // 3. Format Chart (FIX)
            const fmtMap = {{}};
            rawData.raw_data.filter(d => new Date(d['Created Time']).getFullYear() === 2026).forEach(d => {{
                const f = d['FORMAT'] || 'Khác';
                if (!fmtMap[f]) fmtMap[f] = {{ r: 0, i: 0, c: 0 }};
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
                    scales: {{ 
                        y: {{ ticks: {{ color: '#fff' }} }},
                        y1: {{ position: 'right', ticks: {{ color: '#fbbf24' }} }}
                    }}
                }}
            }});

            // 4. Matrix Chart (FIX)
            const matrixPoints = rawData.raw_data.filter(d => new Date(d['Created Time']).getFullYear() === 2026).slice(0,50).map(d => ({{
                x: parseNum(d['Reach']), y: (parseNum(d['Tổng tương tác'])/parseNum(d['Reach'])*100) || 0
            }}));
            new Chart(document.getElementById('scatterChart'), {{
                type: 'scatter',
                data: {{ datasets: [{{ label: 'Content', data: matrixPoints, backgroundColor: '#38bdf8' }}] }},
                options: {{ 
                    responsive: true, maintainAspectRatio: false,
                    scales: {{ x: {{ ticks: {{ color: '#fff' }} }}, y: {{ ticks: {{ color: '#fff' }} }} }}
                }}
            }});
        }}
        
        initDashboard();
    </script>
</body>
</html>
"""

components.html(html_full_code, height=1500, scrolling=True)

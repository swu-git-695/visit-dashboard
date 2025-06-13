import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import matplotlib.pyplot as plt

# ===== Page config =====
st.set_page_config(page_title="Visit ต่อวัน", layout="wide")

# ===== CSS Styling =====
st.markdown("""
<style>
/* ใส่ CSS ของคุณที่นี่ได้เลย */
</style>
""", unsafe_allow_html=True)

# ===== DB fetch function =====
def get_data(query):
    try:
        with psycopg2.connect(
            host='172.18.69.20',
            user='iptscanview',
            password='iptscanview',
            dbname='cpahdb',
            port=5432
        ) as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")
        return pd.DataFrame()

# ===== Main =====
st.title("📅 รายงานจำนวน Visit ต่อวัน")

# 1. Filter เลือกช่วงวันที่เองได้ (Date Picker)
col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    start_date = st.date_input("เลือกวันที่เริ่มต้น", value=pd.to_datetime("2025-06-01"))
with col_filter2:
    end_date = st.date_input("เลือกวันที่สิ้นสุด", value=pd.to_datetime("2025-06-12"))

if start_date > end_date:
    st.error("วันที่เริ่มต้นต้องไม่เกินวันที่สิ้นสุด")
    st.stop()

# 7. จำกัดข้อมูลแสดง (Limit & Pagination) — สมมติ limit 60 วัน
max_days = 60
if (end_date - start_date).days > max_days:
    st.warning(f"เลือกช่วงวันที่เกิน {max_days} วัน ระบบจะตัดข้อมูลให้เหลือแค่ {max_days} วันล่าสุด")
    start_date = end_date - pd.Timedelta(days=max_days)

# ดึงข้อมูลจาก DB
query = f"""
SELECT vstdate, COUNT(vn) as total 
FROM ovst
WHERE vstdate BETWEEN '{start_date}' AND '{end_date}'
GROUP BY vstdate
ORDER BY vstdate ASC;
"""
df = get_data(query)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในช่วงวันที่ที่ระบุ")
    st.stop()

df['vstdate'] = pd.to_datetime(df['vstdate']).dt.date

# เติมวันในช่วงที่ไม่มีข้อมูล visit เป็น 0
all_dates = pd.date_range(start_date, end_date)
df_full = pd.DataFrame({'vstdate': all_dates})
df_full['vstdate'] = df_full['vstdate'].dt.date
df = pd.merge(df_full, df, on='vstdate', how='left').fillna({'total': 0})
df['total'] = df['total'].astype(int)

# 4. เพิ่ม Moving Average Trend
window_size = st.slider("เลือกช่วง Moving Average (วัน)", min_value=1, max_value=14, value=3)
df['moving_avg'] = df['total'].rolling(window=window_size, min_periods=1).mean()

# *** เพิ่มเลือกประเภทกราฟระหว่าง Bar กับ Line ***
chart_type = st.radio("เลือกประเภทแผนภูมิ", ['Bar Chart', 'Line Chart'], horizontal=True)

# Layout Responsive (cols)
col1, col2 = st.columns([2, 1])

with col1:
    if chart_type == 'Bar Chart':
        st.subheader("📊 แผนภูมิแท่ง (Bar Chart)")

        fig = px.bar(
            df,
            x='vstdate',
            y='total',
            labels={'vstdate': 'วันที่', 'total': 'จำนวน Visit'},
            text='total',
            color='total',
            color_continuous_scale=px.colors.sequential.Teal,
            title='จำนวน Visit ต่อวัน'
        )
    else:
        st.subheader("📈 แผนภูมิเส้น (Line Chart)")

        fig = px.line(
            df,
            x='vstdate',
            y='total',
            markers=True,
            labels={'vstdate': 'วันที่', 'total': 'จำนวน Visit'},
            title='จำนวน Visit ต่อวัน'
        )

    # เพิ่มเส้น Moving Average
    fig.add_scatter(
        x=df['vstdate'],
        y=df['moving_avg'],
        mode='lines',
        line=dict(color='orange', width=3, dash='dash'),
        name=f'Moving Average ({window_size} วัน)'
    )

    fig.update_traces(
        marker=dict(line=dict(width=1.8, color='#145c4d')),
        textfont_color='#145c4d',
        hovertemplate='<b>วันที่:</b> %{x}<br><b>Visit:</b> %{y}<extra></extra>'
    )

    fig.update_layout(
        xaxis_tickformat='%d %b %Y',
        xaxis_title='วันที่',
        yaxis_title='จำนวน Visit',
        coloraxis_showscale=False,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Segoe UI", size=14, color="#20514f"),
        hovermode="x unified",
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧁 แผนภูมิวงกลม (Pie Chart)")

    df_sorted = df.sort_values('total', ascending=True)

    def func(pct, allvals):
        absolute = int(round(pct / 100. * sum(allvals)))
        return f"{absolute:,}"

    fig_pie, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        df_sorted['total'],
        labels=df_sorted['vstdate'].astype(str),
        autopct=lambda pct: func(pct, df_sorted['total']),
        startangle=140,
        colors=plt.cm.Set3.colors,
        textprops={'fontsize': 11, 'weight': 'bold', 'color': '#20514f'}
    )
    ax.axis('equal')
    ax.set_title("สัดส่วน Visit ต่อวัน", fontsize=18, fontweight='bold', color='#20514f')
    st.pyplot(fig_pie)

with col2:
    st.subheader("📋 ตารางจำนวน Visit ต่อวัน")

    def highlight_max(s):
        is_max = s == s.max()
        return ['background-color: #78b5a7; font-weight: 700; color: white;' if v else '' for v in is_max]

    styled_df = df.style.format({'total': '{:,}'}).apply(highlight_max, subset=['total']).set_properties(**{
        'text-align': 'center',
        'font-size': '15px',
        'font-family': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
        'padding': '12px',
        'color': '#20514f'
    }).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#4c8a76'),
                                     ('color', '#d9f0ec'),
                                     ('font-weight', '700'),
                                     ('text-align', 'center'),
                                     ('padding', '14px')]},
        {'selector': 'td', 'props': [('border', '1px solid #a2d2cc')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#9bd4c8')]},
    ])

    st.dataframe(styled_df, use_container_width=True)

    # 3. Export/Download CSV
    csv = df.to_csv(index=False)
    st.download_button("📥 ดาวน์โหลด CSV", data=csv, file_name='visit_report.csv', mime='text/csv')

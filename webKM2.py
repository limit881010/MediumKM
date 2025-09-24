import streamlit as st
import pandas as pd

# 讀取Excel檔案
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        # 確保欄位存在
        required_columns = ['Date', 'Author', 'Title', 'Subtitle', 'URL', 'Category (20-class)']
        if not all(col in df.columns for col in required_columns):
            st.error("Excel檔案缺少必要欄位：Date, Author, Title, Subtitle, URL, Category (20-class)")
            return None
        # 轉換Date為datetime格式，以便排序
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"讀取檔案失敗：{e}")
        return None

# 顯示分頁文章的函數
def display_paginated_articles(df):
    if df.empty:
        st.info("無文章。")
        return

    # 初始化 session state 中的頁碼
    if 'page' not in st.session_state:
        st.session_state.page = 0

    # 計算總頁數
    items_per_page = 5
    total_pages = (len(df) + items_per_page - 1) // items_per_page

    # 顯示當前頁的文章
    start = st.session_state.page * items_per_page
    end = start + items_per_page
    page_df = df.iloc[start:end]

    # 使用 CSS 來減少留白
    st.markdown("""
    <style>
    .stMarkdown div {
        margin-top: -10px;
        margin-bottom: -10px;
    }
    </style>
    """, unsafe_allow_html=True)

    for index, row in page_df.iterrows():
        # 使用 columns 來對齊標題和連結
        col1, col2 = st.columns([4, 1])  # 調整比例使連結對齊右邊
        with col1:
            st.markdown(f"♦ **{row['Title']}**", unsafe_allow_html=True)
        with col2:
            st.markdown(f"[🔗閱覽連結](https://freedium.cfd/{row['URL']})", unsafe_allow_html=True)
        
        # 合併 subtitle, author 和 date 到一行以縮短版面
        subtitle = row['Subtitle'] if pd.notna(row['Subtitle']) else ''
        date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'
        st.markdown(f"{subtitle} — {row['Author']}, {date_str}", unsafe_allow_html=True)
        st.markdown("---")
    
    # 分頁控制按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("上一頁") and st.session_state.page > 0:
            st.session_state.page -= 1
            st.rerun()
    with col3:
        if st.button("下一頁") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1
            st.rerun()
    st.write(f"頁碼: {st.session_state.page + 1} / {total_pages}")

# 主程式
st.title("Medium Digest-Web")

# 上傳或指定Excel檔案（這裡假設檔案在同目錄，您可以改成上傳功能）
file_path = 'Medium digest (classified).xlsx'  # 替換成您的Excel檔案路徑
df = load_data(file_path)

if df is not None:
    # 定義 AI 和 非 AI 類別
    ai_categories = [
        "Retrieval-Augmented Generation (RAG)",
        "Agentic AI & AI Agents",
        "Large Language Models (LLM)",
        "Multimodal AI (Vision/Audio/Video + Language)",
        "Computer Vision (CV)",
        "Speech & Audio AI",
        "Natural Language Processing (non-LLM)",
        "Fine-tuning & Embeddings",
        "Prompt Engineering & In-Context Learning",
        "AI Evaluation & Metrics",
        "Deep Learning (non-LLM)",
        "Machine Learning (Classical)",
        "AI Infrastructure, MLOps & Frameworks",
        "AI Applications (Business/Dev/Productivity)",
        "AI Policy, Governance & Safety"
    ]

    non_ai_display_categories = [
        "Software Engineering & Programming",
        "Data Science & Statistics",
        "Technology/Science",
        "Finance/Economics/Business",
        "Society/Culture/Other"
    ]

    # 在側邊欄顯示摺疊列表
    st.sidebar.header("文章分類")
    selected_labels = []

    with st.sidebar.expander("AI（15 類）"):
        select_all_ai = st.checkbox("全選 AI")
        if select_all_ai:
            selected_labels.extend([label for label in ai_categories if label in df['Category (20-class)'].unique()])
        else:
            for label in ai_categories:
                if label in df['Category (20-class)'].unique():
                    label_count = len(df[df['Category (20-class)'] == label])
                    if st.checkbox(f"{label} ({label_count} 篇文章)", value=False):
                        selected_labels.append(label)

    with st.sidebar.expander("非 AI（5 類）"):
        select_all_non_ai = st.checkbox("全選 非AI")
        if select_all_non_ai:
            selected_labels.extend([f"Non-AI {label}" for label in non_ai_display_categories if f"Non-AI {label}" in df['Category (20-class)'].unique()])
        else:
            for display_label in non_ai_display_categories:
                label = f"Non-AI {display_label}"
                if label in df['Category (20-class)'].unique():
                    label_count = len(df[df['Category (20-class)'] == label])
                    if st.checkbox(f"{display_label} ({label_count} 篇文章)", value=False):
                        selected_labels.append(label)

    # 顯示搜尋框在標題下方
    search_term = st.text_input("在Title或Subtitle中搜尋")

    # 重置頁碼當搜尋或選擇改變時（可選，但有助於使用者體驗）
    if 'last_search' not in st.session_state or st.session_state.last_search != search_term:
        st.session_state.page = 0
        st.session_state.last_search = search_term
    if 'last_selected' not in st.session_state or st.session_state.last_selected != selected_labels:
        st.session_state.page = 0
        st.session_state.last_selected = selected_labels[:]

    # 先根據選擇的label過濾資料
    if selected_labels:
        filtered_df = df[df['Category (20-class)'].isin(selected_labels)]
    else:
        filtered_df = df
    filtered_df = filtered_df.sort_values('Date', ascending=False)

    if search_term:
        # 處理搜尋：忽略大小寫，處理NaN，在過濾後的df上搜尋
        mask_title = filtered_df['Title'].astype(str).str.contains(search_term, case=False, na=False)
        mask_subtitle = filtered_df['Subtitle'].astype(str).str.contains(search_term, case=False, na=False)
        search_df = filtered_df[mask_title | mask_subtitle]
        st.subheader(f"搜尋結果 (共 {len(search_df)} 筆)")
        if not search_df.empty:
            display_paginated_articles(search_df)
        else:
            st.info("無符合搜尋結果。")
    else:
        display_paginated_articles(filtered_df)
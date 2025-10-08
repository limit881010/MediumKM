import streamlit as st
import pandas as pd
import os
import hashlib

READ_DB = "read_status.csv"  # 側車檔，用來保存已讀狀態（URL為唯一鍵）

# ========== 讀寫已讀狀態 ==========
def ensure_read_db():
    """若 read_status.csv 不存在就建立空檔"""
    if not os.path.exists(READ_DB):
        pd.DataFrame({"ItemKey": [], "Read": []}).to_csv(READ_DB, index=False)

def _dedup_by_itemkey(df: pd.DataFrame) -> pd.DataFrame:
    if "ItemKey" in df.columns:
        # 保留最後一次寫入的狀態
        df = df.drop_duplicates(subset=["ItemKey"], keep="last")
    return df

def load_read_db() -> pd.DataFrame:
    ensure_read_db()
    try:
        db = pd.read_csv(READ_DB, dtype={"ItemKey": str})
        if "Read" not in db.columns:
            db["Read"] = False
        db = _dedup_by_itemkey(db)
        return db
    except Exception:
        # 壞檔時自動重建
        empty = pd.DataFrame({"ItemKey": [], "Read": []})
        empty.to_csv(READ_DB, index=False)
        return empty

def save_read_db(db: pd.DataFrame):
    db = _dedup_by_itemkey(db)
    db.to_csv(READ_DB, index=False)

def mark_read(item_key: str, read_state: bool):
    db = load_read_db()
    if item_key in db["ItemKey"].values:
        db.loc[db["ItemKey"] == item_key, "Read"] = read_state
    else:
        db = pd.concat([db, pd.DataFrame({"ItemKey": [item_key], "Read": [read_state]})], ignore_index=True)
    save_read_db(db)

def stable_key(prefix: str, s: str) -> str:
    """把任意字串 s 轉為穩定、安全的 widget key"""
    h = hashlib.md5(s.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"{prefix}_{h}"

# ========== 載入主資料 ==========
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        required_columns = ['Date', 'Author', 'Title', 'Subtitle', 'URL', 'Category (20-class)']
        if not all(col in df.columns for col in required_columns):
            st.error("Excel檔案缺少必要欄位：Date, Author, Title, Subtitle, URL, Category (20-class)")
            return None

        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # 用 URL 當唯一鍵（建議）
        df["ItemKey"] = df["URL"].astype(str)

        # 若想改用 Author+Title 當 key，改用下列這行：
        # df["ItemKey"] = (df["Author"].astype(str) + " || " + df["Title"].astype(str)).str.strip()

        # 合併已讀狀態
        read_db = load_read_db()
        df = df.merge(read_db, how="left", on="ItemKey")
        df["Read"] = df["Read"].fillna(False).astype(bool)
        return df
    except Exception as e:
        st.error(f"讀取檔案失敗：{e}")
        return None

# ========== 分頁顯示 ==========
def display_paginated_articles(df):
    if df.empty:
        st.info("無文章。")
        return

    if 'page' not in st.session_state:
        st.session_state.page = 0

    items_per_page = 8
    total_pages = (len(df) + items_per_page - 1) // items_per_page
    # 若篩選變更造成頁碼超界，保險收回最後一頁
    st.session_state.page = min(st.session_state.page, max(total_pages - 1, 0))

    start = st.session_state.page * items_per_page
    end = start + items_per_page
    page_df = df.iloc[start:end]

    # CSS：淡化已讀
    st.markdown("""
    <style>
    .stMarkdown div { margin-top: -10px; margin-bottom: -10px; }
    .read-dim { opacity: 0.45; }
    </style>
    """, unsafe_allow_html=True)

    for _, row in page_df.iterrows():
        wrapper_class = "read-dim" if row.get("Read", False) else ""
        title_html = f"<font size=5>♦ <b>{row['Title']}</b></font>"
        subtitle_html = f"{row['Subtitle']}" if pd.notna(row['Subtitle']) else ""
        date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'
        link_html = (
            f"{row['Author']},  {date_str}, "
            f"<a href='{row['URL']}' target='_blank' style='margin-right:15px'>🔗全文連結</a>"
            f"<a href='https://freedium.cfd/{row['URL']}' target='_blank'>🔗破解連結</a>"
            )
        st.markdown(f"<div class='{wrapper_class}'>{title_html}</div>", unsafe_allow_html=True)
        if subtitle_html:
            st.markdown(f"<div class='{wrapper_class}'>{subtitle_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='{wrapper_class}'>{link_html}</div>", unsafe_allow_html=True)

        # 互動按鈕：標記為已報告 / 取消已報告（使用穩定雜湊 key）
        col_a, col_b = st.columns([3, 3])
        btn_key_read = stable_key("btn_read", str(row['ItemKey']))
        if not row.get("Read", False):
            if col_a.button("標示為已報告", key=btn_key_read):
                mark_read(row['ItemKey'], True)
                st.rerun()
        else:
            if col_a.button("取消已報告", key=btn_key_read):
                mark_read(row['ItemKey'], False)
                st.rerun()

        st.markdown("---")

    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        if st.button("上一頁") and st.session_state.page > 0:
            st.session_state.page -= 1
            st.rerun()
    with col3:
        if st.button("下一頁") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1
            st.rerun()
    st.write(f"頁碼: {st.session_state.page + 1} / {total_pages}")

# ========== 主程式 ==========
st.title("Medium Digest-Web")

file_path = 'Medium digest (classified).xlsx'
df = load_data(file_path)


if df is not None:
    # ===== 類別清單 =====
    ai_categories = [
        "Agentic AI & AI Agents",
        "Retrieval-Augmented Generation (RAG)",
        "Multimodal AI (Vision/Audio/Video + Language)",
        "Prompt Engineering & In-Context Learning",
        "Fine-tuning & Embeddings",
        "Large Language Models (LLM)",
        "Natural Language Processing (non-LLM)",
        "Computer Vision (CV)",
        "Speech & Audio AI",
        "Deep Learning (non-LLM)",
        "Machine Learning (Classical)",
        "AI Algorithm",
        "AI Evaluation & Metrics",
        "AI Infrastructure, MLOps & Frameworks",
        "AI Applications (Business/Dev/Productivity)",
        "AI Policy, Governance & Safety"
    ]

    non_ai_display_categories = [
        "Data Science & Statistics",
        "Software Engineering & Programming",
        "Technology/Science",
        "Finance/Economics/Business",
        "Society/Culture/Other"
    ]

    # ===== 狀態（已報告 / 未報告） =====
    st.sidebar.subheader("狀態")
    total_read = int(df["Read"].sum())
    total_unread = int((~df["Read"]).sum())
    status_options = [
        f"全部（{len(df)}）",
        f"僅未報告（{total_unread}）",
        f"僅已報告（{total_read}）"
    ]
    status_choice = st.sidebar.radio(
        "依狀態篩選",
        status_options,
        index=0,
        key="status_filter"
    )
    st.sidebar.markdown("---")
    # ===== 側邊欄：分類 =====
    st.sidebar.header("文章分類")
    selected_labels = []

    unique_cats = set(df['Category (20-class)'].unique())

    st.sidebar.subheader("AI（15 類）")
    ai_select_all = st.sidebar.checkbox("全選 AI", key="ai__all")
    prev_ai_all = st.session_state.get("ai__all_prev", False)
    if ai_select_all != prev_ai_all:
        for label in ai_categories:
            if label in unique_cats:
                st.session_state[f"ai_{label}"] = ai_select_all
        st.session_state["ai__all_prev"] = ai_select_all

    for label in ai_categories:
        if label in unique_cats:
            cnt = (df['Category (20-class)'] == label).sum()
            if st.sidebar.checkbox(
                f"{label}（{cnt} 篇文章）",
                key=f"ai_{label}",
                value=st.session_state.get(f"ai_{label}", False)
            ):
                selected_labels.append(label)

    st.sidebar.markdown("---")

    st.sidebar.subheader("非 AI（5 類）")
    non_ai_select_all = st.sidebar.checkbox("全選 非AI", key="nonai__all")
    prev_nonai_all = st.session_state.get("nonai__all_prev", False)
    if non_ai_select_all != prev_nonai_all:
        for display_label in non_ai_display_categories:
            label = f"Non-AI {display_label}"
            if label in unique_cats:
                st.session_state[f"nonai_{display_label}"] = non_ai_select_all
        st.session_state["nonai__all_prev"] = non_ai_select_all

    for display_label in non_ai_display_categories:
        label = f"Non-AI {display_label}"
        if label in unique_cats:
            cnt = (df['Category (20-class)'] == label).sum()
            if st.sidebar.checkbox(
                f"{display_label}（{cnt} 篇文章）",
                key=f"nonai_{display_label}",
                value=st.session_state.get(f"nonai_{display_label}", False)
            ):
                selected_labels.append(label)

    st.sidebar.markdown("---")

    # ===== 主區塊 =====
    search_term = st.text_input("在Title或Subtitle中搜尋", key="search_main")

    # 去重並排序，避免順序引起頁碼重置錯亂
    selected_labels = sorted(set(selected_labels))

    # 初始化 page
    if "page" not in st.session_state:
        st.session_state.page = 0

    # 搜尋或選擇改變時重置頁碼
    if st.session_state.get("last_search") != search_term:
        st.session_state.page = 0
        st.session_state.last_search = search_term

    if st.session_state.get("last_selected") != tuple(selected_labels):
        st.session_state.page = 0
        st.session_state.last_selected = tuple(selected_labels)

    if st.session_state.get("last_status") != status_choice:
        st.session_state.page = 0
        st.session_state.last_status = status_choice

    # 先依類別過濾
    if selected_labels:
        filtered_df = df[df['Category (20-class)'].isin(selected_labels)]
    else:
        filtered_df = df

    # 套用「狀態」篩選
    if "僅未報告" in status_choice:
        filtered_df = filtered_df[~filtered_df["Read"]]
    elif "僅已報告" in status_choice:
        filtered_df = filtered_df[filtered_df["Read"]]

    # 時間排序
    filtered_df = filtered_df.sort_values('Date', ascending=False)

    # 搜尋（忽略大小寫，處理 NaN）
    if search_term:
        mask = (
            filtered_df['Title'].astype(str).str.contains(search_term, case=False, na=False) |
            filtered_df['Subtitle'].astype(str).str.contains(search_term, case=False, na=False)
        )
        search_df = filtered_df[mask]
        st.subheader(f"搜尋結果（共 {len(search_df)} 筆）")
        if not search_df.empty:
            display_paginated_articles(search_df)
        else:
            st.info("無符合搜尋結果。")
    else:
        display_paginated_articles(filtered_df)

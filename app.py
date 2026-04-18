"""
Octopus Energy 電気料金サンプル明細書 — Streamlit Web アプリ
─────────────────────────────────────────────────────────────
起動方法:
  pip install streamlit reportlab pypdf
  streamlit run app.py

デプロイ方法:
  Streamlit Community Cloud (無料) に GitHub 経由でデプロイできます。
  詳細は README を参照してください。
─────────────────────────────────────────────────────────────
"""

import io
import os
import streamlit as st
from datetime import date

# ── アプリ設定 ─────────────────────────────────────────────────
APP_TITLE    = "Octopus Energy 電気料金サンプル明細書 生成ツール"
# パスワードはStreamlit Secretsから取得（ローカル実行時はデフォルト値を使用）
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "octopus2025")

# ── 生成エンジンを読み込む ──────────────────────────────────────
# generate_bill.py と同じフォルダに配置してください
import sys
sys.path.insert(0, os.path.dirname(__file__))
from generate_bill import (
    get_seasonal_kwh,
    calculate_bill,
    generate_pdf,
    get_discount_rate,
    _fy,
    RATE,
)


# ── ページ設定 ─────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚡",
    layout="centered",
)


# ── パスワード認証 ──────────────────────────────────────────────
def auth_gate():
    st.title("⚡ " + APP_TITLE)
    st.markdown("---")
    pwd = st.text_input("🔑 パスワードを入力してください", type="password")
    if st.button("ログイン", use_container_width=True):
        if pwd == APP_PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    auth_gate()
    st.stop()


# ── メイン画面 ─────────────────────────────────────────────────
st.title("⚡ " + APP_TITLE)
st.caption("チーム内専用ツール")
st.markdown("---")

# ── 入力フォーム ───────────────────────────────────────────────
with st.form("bill_form"):
    st.subheader("① 顧客情報の入力")

    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("氏名（フルネーム）", placeholder="例：山田 太郎", value="")
    with col2:
        postal = st.text_input("郵便番号", placeholder="例：150-0001", value="")

    address = st.text_input(
        "住所（都道府県〜部屋番号まで）",
        placeholder="例：東京都渋谷区神宮前1-2-3 サンプルマンション301",
        value="",
    )

    st.markdown("---")
    st.subheader("② 請求月の選択")

    today = date.today()
    col3, col4 = st.columns(2)
    with col3:
        year = st.selectbox(
            "年",
            options=list(range(today.year - 1, today.year + 2)),
            index=1,
        )
    with col4:
        month = st.selectbox(
            "月",
            options=list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: f"{m}月",
        )

    st.markdown("---")
    st.subheader("③ 使用量の設定")

    auto_kwh = st.checkbox(
        "季節に合わせて自動計算する（推奨）",
        value=True,
        help="チェックをはずすと手動でkWhを入力できます",
    )
    manual_kwh = None
    if not auto_kwh:
        manual_kwh = st.slider(
            "使用量（kWh）",
            min_value=50, max_value=600, value=200, step=5,
            help="0〜120kWh: 段階1 / 121〜300kWh: 段階2 / 301kWh〜: 段階3",
        )

    st.markdown("---")
    st.subheader("④ 発行日の指定")
    issue_date_input = st.date_input(
        "発行日",
        value=date(today.year, today.month, 25),
        help="PDFの右上に表示される発行日です",
    )

    submitted = st.form_submit_button("📄　明細書を生成する", use_container_width=True)


# ── PDF 生成 & ダウンロード ────────────────────────────────────
if submitted:
    # バリデーション
    errors = []
    if not name.strip():
        errors.append("氏名を入力してください。")
    if not postal.strip():
        errors.append("郵便番号を入力してください。")
    if not address.strip():
        errors.append("住所を入力してください。")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    with st.spinner("明細書を生成中…"):
        import random
        from datetime import timedelta

        # 使用期間の計算（前月23日〜当月22日）
        prev_month = month - 1 if month > 1 else 12
        prev_year  = year if month > 1 else year - 1
        period_start = date(prev_year, prev_month, 23)
        period_end   = date(year, month, 22)
        days = (period_end - period_start).days + 1

        # 発行日・前回支払日
        issue_date     = issue_date_input
        prev_paid_date = date(prev_year, prev_month, 4)

        # kWh の決定
        kwh = manual_kwh if manual_kwh else get_seasonal_kwh(month)

        # 料金計算
        discount_rate = get_discount_rate(year, month)
        bill = calculate_bill(kwh, days, discount_rate=discount_rate)

        # 前回ご請求金額（前月推定）
        prev_kwh    = get_seasonal_kwh(prev_month)
        prev_bill   = calculate_bill(prev_kwh, 30)
        prev_amount = prev_bill["final_total"]

        # 契約番号・請求書番号（ランダム）
        import string
        hex_c    = "0123456789ABCDEF"
        contract = "A-" + "".join(random.choices(hex_c, k=8))
        invoice  = "S"  + str(random.randint(10000000, 99999999))

        # 供給地点特定番号（ダミー）
        sp = "-".join([
            f"{random.randint(0,99):02d}",
            f"{random.randint(0,9999):04d}",
            f"{random.randint(0,9999):04d}",
            f"{random.randint(0,9999):04d}",
            f"{random.randint(0,9999):04d}",
            f"{random.randint(0,9999):04d}",
        ])

        data = dict(
            name=name.strip(), postal=postal.strip(), address=address.strip(),
            contract=contract, invoice=invoice,
            issue_date=issue_date,
            period_start=period_start, period_end=period_end,
            prev_amount=prev_amount, prev_paid_date=prev_paid_date,
            supply_point=sp, bill=bill,
        )

        # 一時ファイルに生成
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        generate_pdf(tmp_path, data)

        # ── メタデータ・編集履歴を完全削除 ──────────────────────
        import pikepdf
        clean_path = tmp_path + "_clean.pdf"
        with pikepdf.open(tmp_path) as pdf:
            # XMP メタデータ（編集履歴・作成ソフト情報など）を全消去
            # set_pikepdf_as_editor=False で pikepdf 自身の署名も抑止
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta.clear()
            # ドキュメント情報辞書（Author/Creator/Producer 等）を削除
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]
            # XMP ストリーム自体も削除
            if "/Metadata" in pdf.Root:
                del pdf.Root["/Metadata"]
            pdf.save(clean_path)
        os.unlink(tmp_path)

        with open(clean_path, "rb") as f:
            pdf_bytes = f.read()
        os.unlink(clean_path)

    # ── 結果表示 ────────────────────────────────────────────
    st.success("✅ 生成完了！")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("使用量", f"{kwh} kWh")
    col_b.metric("電気料金（税込）", f"{bill['total_inc']:,}円")
    col_c.metric("請求金額（割引後）", f"{bill['final_total']:,}円")

    with st.expander("料金明細を確認する"):
        st.markdown(f"""
| 項目 | 金額 |
|---|---|
| 基本料金 | {bill['basic']:,.2f}円 |
| 電力量料金①（〜120kWh） | {bill['tier1']:,.2f}円 |
| 電力量料金②（121〜300kWh） | {bill['tier2']:,.2f}円 |
| 電力量料金③（301kWh〜） | {bill['tier3']:,.2f}円 |
| 燃料費調整額 | {bill['fuel']:,.2f}円 |
| 再エネ賦課金 | {bill['renew']:,.2f}円 |
| 消費税（10%） | {bill['tax']:,}円 |
| 政府値引き（▲{kwh}kWh × {bill['discount_rate']:.1f}円） | ▲{bill['discount']:,}円 |
| **最終請求金額** | **{bill['final_total']:,}円** |
        """)

    safe_name = name.replace(" ", "_").replace("　", "_")
    filename  = f"octopus_{year}{month:02d}_{safe_name}.pdf"

    st.download_button(
        label="⬇️　PDFをダウンロード",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )

    st.caption(f"契約番号: {contract}　|　請求書番号: {invoice}　|　発行日: {issue_date.strftime('%Y/%m/%d')}")

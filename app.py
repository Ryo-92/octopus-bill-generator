"""
Octopus Energy 電気料金サンプル明細書 — Streamlit Web アプリ
─────────────────────────────────────────────────────────────
起動方法:
  pip install streamlit reportlab pypdf pikepdf
  streamlit run app.py

デプロイ方法:
  Streamlit Community Cloud (無料) に GitHub 経由でデプロイできます。
  詳細は README を参照してください。
─────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import html as html_module
import urllib.request
import streamlit as st
from datetime import date

# ── アプリ設定 ─────────────────────────────────────────────────
APP_TITLE    = "Octopus Energy 電気料金サンプル明細書 生成ツール"
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "octopus2025")

# ── 生成エンジンを読み込む ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from generate_bill import (
    get_seasonal_kwh,
    calculate_bill,
    generate_pdf,
    get_discount_rate,
    _DISCOUNT_RATES,
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


# ── 政府補助金 単価の自動取得 ──────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_subsidy_rate_from_web(year: int, month: int) -> tuple[float | None, str | None]:
    """
    経済産業省等のページから補助金単価をスクレイピング（ベストエフォート）。
    成功した場合は (rate, source_url)、失敗した場合は (None, None) を返す。
    結果は 1 時間キャッシュする。
    """
    target_texts = [f"{year}年{month}月", f"{year}/{month:02d}"]

    urls = [
        "https://www.enecho.meti.go.jp/category/electricity_and_gas/electricity/electric_bill/",
        "https://www.enecho.meti.go.jp/",
        "https://www.meti.go.jp/",
    ]

    rate_patterns = [
        r'(\d+(?:\.\d+)?)\s*円[/／]kWh',
        r'(\d+(?:\.\d+)?)\s*円[/／]キロワット時',
        r'kWh[当あ]た[りリ]\s*(\d+(?:\.\d+)?)\s*円',
        r'1kWh[につき当あ]*?(\d+(?:\.\d+)?)\s*円',
    ]

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "Accept": "text/html",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()

            # エンコーディング自動判定
            text = None
            for enc in ("utf-8", "shift_jis", "euc-jp", "utf-8-sig"):
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if text is None:
                continue

            # HTML タグ除去・正規化
            text = re.sub(r"<[^>]+>", " ", text)
            text = html_module.unescape(text)
            text = re.sub(r"\s+", " ", text)

            for target in target_texts:
                idx = text.find(target)
                if idx < 0:
                    continue
                context = text[max(0, idx - 300): idx + 700]
                for pattern in rate_patterns:
                    m = re.search(pattern, context)
                    if m:
                        rate = float(m.group(1))
                        if 0 < rate <= 20:   # 妥当範囲チェック
                            return rate, url

        except Exception:
            continue

    return None, None


def get_subsidy_info(usage_year: int, usage_month: int) -> tuple[float, str, str]:
    """
    使用月の補助金単価を返す。
    Returns: (rate, source, status_text)
      source: "table" | "web" | "unknown"
    """
    if (usage_year, usage_month) in _DISCOUNT_RATES:
        rate = _DISCOUNT_RATES[(usage_year, usage_month)]
        if rate == 0.0:
            status = f"補助なし（{usage_year}年{usage_month}月使用分・登録済み）"
        else:
            status = f"{rate:.1f}円/kWh（{usage_year}年{usage_month}月使用分・登録済み）"
        return rate, "table", status

    # 未登録月 → Web 取得
    fetched_rate, fetched_url = _fetch_subsidy_rate_from_web(usage_year, usage_month)
    if fetched_rate is not None:
        domain = re.sub(r"https?://([^/]+).*", r"\1", fetched_url or "")
        status = f"{fetched_rate:.1f}円/kWh（{usage_year}年{usage_month}月・{domain} より取得）"
        return fetched_rate, "web", status

    status = (
        f"{usage_year}年{usage_month}月は未登録です。"
        f"[最新情報を確認](https://www.enecho.meti.go.jp/category/electricity_and_gas/electricity/electric_bill/)"
        f"して手動入力してください。"
    )
    return 0.0, "unknown", status


# ── メイン画面 ─────────────────────────────────────────────────
st.title("⚡ " + APP_TITLE)
st.caption("チーム内専用ツール")
st.markdown("---")

# ── ① 顧客情報 ────────────────────────────────────────────────
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

# ── ② 発行日の指定 ────────────────────────────────────────────
st.subheader("② 発行日の指定")

today = date.today()
issue_date_input = st.date_input(
    "発行日",
    value=date(today.year, today.month, 25),
    help="PDFの右上に表示される発行日です",
)

# ── 発行日から請求月・検針期間を自動計算 ──────────────────────
# ルール：22日以前 → 前月分、23日以降 → 当月分
issue_date = issue_date_input
if issue_date.day >= 23:
    billing_year  = issue_date.year
    billing_month = issue_date.month
else:
    if issue_date.month == 1:
        billing_year  = issue_date.year - 1
        billing_month = 12
    else:
        billing_year  = issue_date.year
        billing_month = issue_date.month - 1

# 検針期間（前月23日 〜 請求月22日）
if billing_month == 1:
    prev_year  = billing_year - 1
    prev_month = 12
else:
    prev_year  = billing_year
    prev_month = billing_month - 1

period_end   = date(billing_year, billing_month, 22)
period_start = date(prev_year, prev_month, 23)

# 計算結果を情報として表示
st.info(
    f"📅　**{issue_date.strftime('%Y年%-m月%-d日')}発行**　→　"
    f"**{billing_year}年{billing_month}月分**の請求書を生成します　"
    f"（検針期間：{prev_year}年{prev_month}月23日 〜 {billing_year}年{billing_month}月22日）"
)

st.markdown("---")

# ── ③ 政府補助金（激変緩和措置）────────────────────────────────
st.subheader("③ 政府補助金（激変緩和措置）")

# 未登録月の場合はスピナーを表示しながら取得
if (prev_year, prev_month) not in _DISCOUNT_RATES:
    with st.spinner(f"{prev_year}年{prev_month}月の補助金情報を取得中…"):
        subsidy_rate, subsidy_source, subsidy_status = get_subsidy_info(prev_year, prev_month)
else:
    subsidy_rate, subsidy_source, subsidy_status = get_subsidy_info(prev_year, prev_month)

# ステータス表示
if subsidy_source == "table":
    st.success(f"✅ {subsidy_status}")
elif subsidy_source == "web":
    st.info(f"🌐 {subsidy_status}")
else:
    st.warning(f"⚠️ {subsidy_status}")

# 単価入力（発行日変更で請求月が変わった場合にリセットされるよう key に月を含、る）
discount_rate_input = st.number_input(
    "補助単価（円/kWh）　※手動で修正できます",
    min_value=0.0,
    max_value=20.0,
    value=float(subsidy_rate),
    step=0.1,
    format="%.1f",
    key=f"disc_rate_{billing_year}_{billing_month}",
    help="政府の激変緩和措置による値引き単価（0.0 = 補助なし）",
)

# 使用量プレビュー（補助金額を即時表示）
preview_kwh = get_seasonal_kwh(billing_month)
preview_discount = round(preview_kwh * discount_rate_input)
if discount_rate_input > 0:
    st.caption(
        f"参考: 使用量 {preview_kwh} kWh（季節推定）× {discount_rate_input:.1f}円 "
        f"= 値引き **{preview_discount:,}円**"
    )

st.markdown("---")

# ── ④ 使用量の設定 ────────────────────────────────────────────
st.subheader("④ 使用量の設定")

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

# ── 生成ボタン ────────────────────────────────────────────────
generate_clicked = st.button("📄　明細書を生成する", use_container_width=True, type="primary")

if generate_clicked:
    # バリデーション
    errors = []
    if not name.strip():
        errors.append("氏名を入力してください。")
    if not postal.strip():
        errors.append("郵便番号を入力してください。")
    if not address.strip():
        errors.append("住所を入力してください。")

    for e in errors:
        st.error(e)

    if not errors:
        with st.spinner("明細書を生成中…"):
            import random, tempfile, pikepdf

            days = (period_end - period_start).days + 1
            prev_paid_date = date(prev_year, prev_month, 4)
            kwh = manual_kwh if manual_kwh else get_seasonal_kwh(billing_month)

            # 料金計算（UIで確定した単価を使用）
            bill = calculate_bill(kwh, days, discount_rate=discount_rate_input)

            # 前回ご請求金額（前月推定）
            prev_kwh    = get_seasonal_kwh(prev_month)
            prev_bill   = calculate_bill(prev_kwh, 30)
            prev_amount = prev_bill["final_total"]

            # 契約番号・請求書番号（ランダム）
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

            # PDF 生成
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
            generate_pdf(tmp_path, data)

            # メタデータ削除 & 編集保護
            clean_path = tmp_path + "_clean.pdf"
            with pikepdf.open(tmp_path) as pdf:
                with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                    meta.clear()
                if "/Info" in pdf.trailer:
                    del pdf.trailer["/Info"]
                if "/Metadata" in pdf.Root:
                    del pdf.Root["/Metadata"]
                pdf.save(
                    clean_path,
                    encryption=pikepdf.Encryption(
                        owner=APP_PASSWORD,
                        user="",
                        allow=pikepdf.Permissions(
                            extract=True,
                            print_lowres=True,
                            print_highres=True,
                            modify_annotation=False,
                            modify_form=False,
                            modify_other=False,
                            modify_assembly=False,
                       ),
                    ),
                )
            os.unlink(tmp_path)

            with open(clean_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(clean_path)

        # 結果を session_state に��存（発行日変更官もダウンロードできるよう）
        st.session_state["result"] = dict(
            pdf_bytes=pdf_bytes,
            bill=bill,
            kwh=kwh,
            billing_year=billing_year,
            billing_month=billing_month,
            name=name.strip(),
            contract=contract,
            invoice=invoice,
            issue_date=issue_date,
            discount_rate=discount_rate_input,
            subsidy_source=subsidy_source,
        )


# ── 結果誎碑 ──────────────────────────────────────────────────
result = st.session_state.get("result")
if result:
    bill = result["bill"]
    kwh  = result["kwh"]

    st.success("✅ 生成完了！")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("使用量", f"{kwh} kWh")
    col_b.metric("電気料金（税込）", f"{bill['total_inc']:,}円")
    col_c.metric("請求金額（割引後）", f"{bill['final_total']:,}円")

    with st.expander("料金明細を確認する"):
        disc_label = (
            f"政府値引き（▲{kwh}kWh × {bill['discount_rate']:.1f}円）"
            + ("　🌐Web取得" if result["subsidy_source"] == "web" else "")
        )
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
| {disc_label} | ▲{bill['discount']:,}円 |
| **最終請求金額** | **{bill['final_total']:,}円** |
        """)

    safe_name = result["name"].replace(" ", "_").replace("　", "_")
    filename  = f"octopus_{result['billing_year']}{result['billing_month']:02d}_{safe_name}.pdf"

    st.download_button(
        label="⬇️　PDFをダウンロード",
        data=result["pdf_bytes"],
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )

    st.caption(
        f"契約番号: {result['contract']}　|　"
        f"請求書番号: {result['invoice']}　|　"
        f"発行日: {result['issue_date'].strftime('%Y/%m/%d')}"
    )

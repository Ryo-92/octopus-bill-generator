"""
残高証明書（三菱UFJ銀行形式）生成ツール — Streamlit Web アプリ
座標はサンプルPDFからpdfminerで実測した値を使用
フォント: 英字・数字 → Helvetica, 日本語 → IBM Plex Sans JP
"""

import io
import os
import random
import streamlit as st
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_W, PAGE_H = A4   # 595.28 × 841.89 pt（実測 595 × 842）
_FONT_JP_PATH = os.path.join(os.path.dirname(__file__), "IBMPlexSansJP-Regular.ttf")
# Helvetica は ReportLab 内蔵フォントのため登録不要
_FONT_REGISTERED = False

APP_TITLE = "残高証明書 生成ツール"


def _setup_font():
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont("JP", _FONT_JP_PATH))
        # Helvetica は ReportLab 内蔵フォント（登録不要）
        _FONT_REGISTERED = True


def _ja_date(d: date) -> str:
    """date → 「2026 年 6 月 5 日」形式"""
    return f"{d.year} 年 {d.month} 月 {d.day} 日"


# ──────────────────────────────────────────────────────────────────────────────
# PDF 生成
# ──────────────────────────────────────────────────────────────────────────────

def generate_pdf(data: dict) -> bytes:
    _setup_font()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    _draw_certificate(c, data)
    c.save()
    buf.seek(0)
    return buf.read()


def _draw_certificate(c, data: dict):
    FJ = "JP"          # 日本語・混在テキスト
    FH = "Helvetica"   # 英字・数字（ReportLab 内蔵）

    # ── 1. ヘッダー ─────────────────────────────────────────────────────────
    # 実測: "残　高　証　明　書" x0=80, y0=803.5, fs=15
    #       "ACCOUNT BALANCE CERTIFICATE" x0=245, y0=803, fs=15
    c.setLineWidth(0.3)
    c.setFont(FJ, 15)
    c.setTextRenderMode(2)
    c.drawString(80, 803, "残　高　証　明　書")
    c.setTextRenderMode(0)
    c.setLineWidth(0.5)
    c.setFont(FH, 15)
    c.drawString(245, 803, "ACCOUNT BALANCE CERTIFICATE")

    # 右上ブロック: x1=524, y0=789 / y0=774, fs=10
    c.setFont(FJ, 10)
    c.drawRightString(524, 789, "同文のもの　１通発行の内第　１号")
    c.setFont(FH, 10)
    c.drawRightString(524, 774, "This is the 1st copy of 1 duplicate issued.")

    # 指定口座 / 1ページ: y0=759
    c.setFont(FJ, 10)
    c.drawString(75, 759, "指定口座")
    c.drawRightString(524, 759, "１ページ")

    # 区切り線（細）
    c.setLineWidth(0.5)
    c.line(75, 752, 524, 752)

    # ── 2. 発行日（右上） ────────────────────────────────────────────────────
    # 実測: x0=418, x1=520, y0=727, fs=10 → 右端 524 に右揃え
    c.setFont(FJ, 10)
    c.drawRightString(524, 727, _ja_date(data["issue_date"]))

    # ── 3. 住所・氏名（左） ──────────────────────────────────────────────────
    # 実測: x=75, 郵便番号 y0=713, 行間15pt, 氏名 y0=653（固定）
    c.setFont(FJ, 10)
    c.drawString(75, 713, data["postal_code"])

    addr_y = 698
    for ln in [data.get("address1", ""), data.get("address2", ""), data.get("address3", "")]:
        if ln and ln.strip():
            c.drawString(75, addr_y, ln.strip())
        addr_y -= 15  # 空行も送る（書式上の固定レイアウト）

    # 氏名は y=653 に固定（書式通り）
    c.drawString(75, 653, data["name"] + "　様")

    # ── 4. 太い区切り線 ──────────────────────────────────────────────────────
    # 実測: y=637, x0=75, x1=495
    c.setLineWidth(1.5)
    c.line(75, 637, 495, 637)
    c.setLineWidth(0.5)

    # ── 5. 証明文（左） ─────────────────────────────────────────────────────
    # 実測: x=85-89, y0=608/594/580（日本語 fs=10）, y0=564/549/534（英語 fs=7）
    c.setFont(FJ, 10)
    c.drawString(89, 608, f"　{_ja_date(data['cert_date'])}現在の貴方ご名義")
    c.drawString(85, 594, "下記勘定残高について相違ないことを証明")
    c.drawString(85, 580, "いたします。")

    c.setFont(FH, 7)
    c.drawString(85, 564, "THIS IS TO CERTIFY THAT THE BALANCE OF")
    c.drawString(85, 549, "YOUR ACCOUNT(S) WITH MUFG Bank SHOW(S)")
    c.drawString(85, 534, "THE AMOUNT(S) INDICATED BELOW.")

    # ── 6. 銀行名（右） ─────────────────────────────────────────────────────
    # 実測: Figure bbox (302, 585.75, 472, 600) → x=302, y_baseline≈586
    # 太字効果: テキスト描画モード2（塗り+輪郭）で太く見せる
    c.setLineWidth(0.4)
    c.setFont(FJ, 22)
    c.setTextRenderMode(2)   # fill + stroke → 疑似ボールド
    c.drawString(302, 582, "株式会社 三菱UFJ銀行")
    c.setTextRenderMode(0)   # 通常に戻す
    c.setLineWidth(0.5)

    # MUFG Bank, Ltd.  実測: Figure bbox (302, 565.84, 382, 575) → y≈566
    c.setFont(FH, 10)
    c.drawString(302, 564, "MUFG Bank, Ltd.")

    # ── 印鑑（赤い公印）─────────────────────────────────────────────────────
    # 実測 Figure bbox (478, 562, 524, 607) → 中心(501, 584.5), r≈23
    SEAL_RED = (0.72, 0.08, 0.08)   # MUFG系の深い赤
    c.setStrokeColorRGB(*SEAL_RED)
    c.setFillColorRGB(*SEAL_RED)
    c.setLineWidth(1.5)
    c.circle(501, 584, 23, stroke=1, fill=0)   # 外円
    c.setLineWidth(0.8)
    c.circle(501, 584, 20, stroke=1, fill=0)   # 内円（二重円）
    c.setFont(FJ, 6.5)
    c.drawCentredString(501, 590, "登　記　印")
    c.setLineWidth(0.6)
    c.line(484, 586, 518, 586)                  # 横線（装飾）
    c.setFont(FH, 7)
    c.drawCentredString(501, 577, "UFJ")
    # リセット
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(0.5)

    # お取引店・電話: 実測 x=280, y0=533/517
    c.setFont(FJ, 10)
    c.drawString(280, 533, f"お取引店　{data.get('branch', '')}　支店")
    c.drawString(280, 518, f"電　　話　{data.get('phone', '')}")

    # ── 7. 残高テーブル ──────────────────────────────────────────────────────
    _draw_table(c, data, FJ, FH)

    # ── 8. フッター ──────────────────────────────────────────────────────────
    # 実測: x=65, y=45/39/33/27, fs=6
    c.setFont(FJ, 6)
    notes = [
        "・この証明書の金額は訂正いたしません。",
        "・金額は、証明日現在の元帳最終残高を表わし決済未確認の証券類を含んでいることがあります。"
        "この場合はその金額を｢(内決済未確認証券類)｣に表示します。",
        "・｢当座貸越(総合)｣には、普通預金貸越型のカードローンご利用額も含まれます。",
        "・口座番号欄は、口座指定のご依頼の場合のみ表示します。",
    ]
    fy = 45
    for note in notes:
        c.drawString(65, fy, note)
        fy -= 6


def _draw_table(c, data: dict, FJ: str, FH: str):
    """
    残高テーブルを描画する
    座標はサンプルPDFから実測（pdfminer + 目視確認）
    """
    # ── 列境界（x 座標）──────────────────────────────────────────────────────
    # 実測: X1=65, X2=205, X3=290, X4=410, X5=530
    X1, X2, X3, X4, X5 = 65, 205, 290, 410, 530
    TW = X5 - X1  # = 465

    # ── 行の y 座標 ──────────────────────────────────────────────────────────
    top_y   = 502   # テーブル上端（ヘッダー上）
    hdr_bot = 472   # ヘッダー下端 / データ行上端
    bot_y   = 52    # テーブル下端
    ROW_H   = 30    # 全行の高さ（ヘッダー含む）

    # ── 外枠 ─────────────────────────────────────────────────────────────────
    c.setDash([])
    c.setLineWidth(0.5)
    c.rect(X1, bot_y, TW, top_y - bot_y)

    # ── 縦区切り線（実線、テーブル全高） ─────────────────────────────────────
    for cx in [X2, X3, X4]:
        c.line(cx, bot_y, cx, top_y)

    # ── 残高・内決済 桁グリッド（点線、データ行のみ hdr_bot → bot_y）─────────
    # 実測: 各列に5本の点線 (x オフセット 27.5, 45.5, 64.5, 82.5, 101.5)
    c.setDash([1, 2])
    for dx in [27.5, 45.5, 64.5, 82.5, 101.5]:
        c.line(X3 + dx, bot_y, X3 + dx, hdr_bot)
        c.line(X4 + dx, bot_y, X4 + dx, hdr_bot)
    c.setDash([])

    # ── 水平区切り線（ヘッダー下端から30pt毎） ───────────────────────────────
    y = hdr_bot
    while y > bot_y:
        c.line(X1, y, X5, y)
        y -= ROW_H

    # ── ヘッダーテキスト ──────────────────────────────────────────────────────
    # 実測: 上段 y0=491 (fs=7), 下段 y0=480 (fs=7/6)
    c.setFont(FJ, 7)
    c.drawString(X1 + 3, 491, "勘定")
    c.setFont(FH, 7)
    c.drawString(X1 + 3, 480, "ACCOUNT")
    c.setFont(FJ, 7)
    c.drawString(X2 + 3, 491, "口座番号")
    c.setFont(FH, 7)
    c.drawString(X2 + 3, 480, "ACCOUNT No.")
    c.setFont(FJ, 7)
    c.drawString(X3 + 3, 491, "残高")
    c.setFont(FH, 7)
    c.drawString(X3 + 3, 480, "BALANCE")
    c.setFont(FJ, 7)
    c.drawString(X4 + 3, 491, "(内決済未確認証券類)")
    c.setFont(FH, 6)
    c.drawString(X4 + 3, 480, "(BILLS OR CHECKS FOR COLLECTION)")

    # ── 普通預金行 ────────────────────────────────────────────────────────────
    # 実測: テキスト y0≈444, "普通預金" x0=75, 口座番号 x0=228, 残高 x1=410, ¥0 x1=530
    c.setLineWidth(0.3)
    c.setFont(FJ, 10)
    c.setTextRenderMode(2)
    c.drawString(X1 + 10, 444, "普　通　預　金")
    c.setTextRenderMode(0)
    c.setLineWidth(0.5)
    c.setFont(FH, 10)
    c.drawString(X2 + 23, 444, data["account_no"])
    c.drawRightString(X4, 444, f'¥{int(data["balance"])}')
    c.drawRightString(X5, 444, "¥0")

    # ── 以下余白行 ────────────────────────────────────────────────────────────
    # 実測: y0=414.5 → y≈415
    c.setFont(FJ, 10)
    c.drawCentredString((X1 + X2) / 2, 415, "以下余白")


# ══════════════════════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("🏦 " + APP_TITLE)
st.caption("三菱UFJ銀行形式の残高証明書PDFを生成します")
st.markdown("---")

# ── ランダム初期値（セッション内で固定）────────────────────────────────────────
if "rnd_acct" not in st.session_state:
    st.session_state["rnd_acct"] = str(random.randint(1000000, 9999999))
if "rnd_balance" not in st.session_state:
    st.session_state["rnd_balance"] = random.randint(1000000, 4000000)
if "rnd_cert_offset" not in st.session_state:
    st.session_state["rnd_cert_offset"] = random.randint(1, 3)

# ── ① 宛先情報（左側）────────────────────────────────────────────────────────
st.subheader("① 宛先情報（左側）")

col_p, col_n = st.columns([1, 1])
with col_p:
    postal = st.text_input("郵便番号（全角）", placeholder="例）１０１－０００１")
with col_n:
    name = st.text_input("氏名（フルネーム）", placeholder="例）田中　太郎")

addr1 = st.text_input(
    "住所①（都道府県・市区町村）",
    placeholder="例）東京都　新宿区",
)
addr2 = st.text_input(
    "住所②（番地）",
    placeholder="例）西新宿　　１－１－１",
)
addr3 = st.text_input(
    "住所③（建物名・部屋番号など）",
    placeholder="例）新宿マンション１０１",
)

st.markdown("---")

# ── ② 発行日（右上）──────────────────────────────────────────────────────────
st.subheader("② 発行日（右上）")
today = date.today()
issue_date = st.date_input("発行日", value=today)
if issue_date is None:
    issue_date = today

st.markdown("---")

# ── ③ 証明内容（中央）────────────────────────────────────────────────────────
st.subheader("③ 証明内容（中央）")
cert_date = st.date_input(
    "証明日（残高の基準日）",
    value=issue_date - timedelta(days=st.session_state["rnd_cert_offset"]),
)

col_a, col_b = st.columns([1, 1])
with col_a:
    acct_no = st.text_input("口座番号", value=st.session_state["rnd_acct"], placeholder="例）0265071")
with col_b:
    balance = st.number_input("残高（円）", min_value=0, value=st.session_state["rnd_balance"], step=1, format="%d")

st.markdown("---")

# ── ④ お取引店情報 ────────────────────────────────────────────────────────────
st.subheader("④ お取引店情報（右側）")
col_br, col_ph = st.columns([1, 1])
with col_br:
    branch = st.text_input("支店名", placeholder="例）草津")
with col_ph:
    phone = st.text_input("電話番号", placeholder="例）077(563)8811")

st.markdown("---")

# ── 生成ボタン─────────────────────────────────────────────────────────────────
if st.button("📄　残高証明書PDFを生成する", use_container_width=True, type="primary"):
    errs = []
    if not postal.strip():   errs.append("郵便番号を入力してください。")
    if not name.strip():     errs.append("氏名を入力してください。")
    if not addr1.strip():    errs.append("住所①を入力してください。")
    if not acct_no.strip():  errs.append("口座番号を入力してください。")
    for e in errs:
        st.error(e)

    if not errs:
        with st.spinner("PDFを生成中…"):
            pdf_bytes = generate_pdf(dict(
                postal_code=postal.strip(),
                address1=addr1.strip(),
                address2=addr2.strip(),
                address3=addr3.strip(),
                name=name.strip(),
                issue_date=issue_date,
                cert_date=cert_date,
                account_no=acct_no.strip(),
                balance=int(balance),
                branch=branch.strip(),
                phone=phone.strip(),
            ))

        st.success("✅ 生成完了！")

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("氏名", name.strip())
        mc2.metric("口座番号", acct_no.strip())
        mc3.metric("残高", f"¥{int(balance)}")

        safe = name.strip().replace(" ", "_").replace("　", "_")
        fname = f"zanko_{issue_date.strftime('%Y%m%d')}_{safe}.pdf"
        st.download_button(
            "⬇️　PDFをダウンロード",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )

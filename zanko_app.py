"""
残高証明書（三菱UFJ銀行形式）生成ツール — Streamlit Web アプリ
座標はサンプルPDFからpdfminerで実測した値を使用
フォント: 全テキスト → IPAexMincho（原本通り）
線幅: 全線 0.25pt（原本通り）
"""

import glob as _glob
import io
import os
import random
import streamlit as st
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_W, PAGE_H = A4   # 595.28 × 841.89 pt


def _find_font_jp() -> str:
    """IPAexMincho フォントパスを動的に探す（Streamlit Cloud: fonts-ipaexfont）"""
    for pattern in [
        '/usr/share/fonts/**/*ipaexm*.ttf',
        '/usr/share/fonts/**/*ipaexm*.otf',
        '/usr/share/fonts/**/*IPAexMincho*.ttf',
    ]:
        hits = sorted(_glob.glob(pattern, recursive=True))
        if hits:
            return hits[0]
    # フォールバック: IBMPlexSansJP（ローカル開発用）
    return os.path.join(os.path.dirname(__file__), "IBMPlexSansJP-Regular.ttf")


_FONT_JP_PATH = _find_font_jp()
_FONT_REGISTERED = False

APP_TITLE = "残高証明書 生成ツール"


def _setup_font():
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont("JP", _FONT_JP_PATH))
        _FONT_REGISTERED = True


def _ja_date(d: date) -> str:
    """date → 「2026 年  6 月  5 日」形式（1桁の月・日は先頭スペースで2桁幅）"""
    m   = f" {d.month}" if d.month < 10 else str(d.month)
    day = f" {d.day}"   if d.day   < 10 else str(d.day)
    return f"{d.year} 年 {m} 月 {day} 日"


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
    FJ = "JP"   # IPAexMincho — 原本は全テキストこのフォント

    # デフォルト線幅（原本: 全線 0.25）
    c.setLineWidth(0.25)

    # ── 1. ヘッダー ─────────────────────────────────────────────────────────
    # 原本実測: "残　高　証　明　書" x=80, y=803.5, size=15
    _t = c.beginText(80, 803)
    _t.setFont(FJ, 15)
    _t.setTextRenderMode(2)  # 塗り+輪郭 → 疑似ボールド（原本タイトル太字）
    _t.textLine("残　高　証　明　書")
    c.drawText(_t)

    # 原本実測: "ACCOUNT BALANCE CERTIFICATE" x=245, y=803, size=15
    c.setFont(FJ, 15)
    c.drawString(245, 803, "ACCOUNT BALANCE CERTIFICATE")

    # 原本実測: "同文のもの..." x=364, y=789.5, size=10
    c.setFont(FJ, 10)
    c.drawString(364, 789, "同文のもの　１通発行の内第　１号")

    # 原本実測: "This is the 1st copy..." x=329.03, y=774.5, size=10
    c.drawString(329, 774, "This is the 1st copy of 1 duplicate issued.")

    # 原本実測: "指定口座" x=75, y=759.5, size=10
    c.drawString(75, 759, "指定口座")

    # 原本実測: "1 ぺージ" x=479.12, y=759.5, size=10
    c.drawString(479, 759, "1 ページ")

    # ── 2. 発行日（右側）────────────────────────────────────────────────────
    # 原本実測: x=418.28, y=729.5, size=10
    c.drawString(418, 729, _ja_date(data["issue_date"]))

    # ── 3. 住所・氏名（左）──────────────────────────────────────────────────
    # 原本実測: 郵便番号 x=75, y=713.43, size=10, 行間 15pt
    c.drawString(75, 713, data["postal_code"])

    addr_y = 698
    for ln in [data.get("address1", ""), data.get("address2", ""), data.get("address3", "")]:
        if ln and ln.strip():
            c.drawString(75, addr_y, ln.strip())
        addr_y -= 15  # 空行でも行送り（書式固定レイアウト）

    # 原本実測: 氏名 x=75, y=653.43（アドレス行数に関わらず固定）
    c.drawString(75, 653, data["name"] + "　様")

    # ── 4. 区切り線 ──────────────────────────────────────────────────────────
    # 原本実測: (75,637)→(495,637), lw=0.25
    c.setLineWidth(0.25)
    c.line(75, 637, 495, 637)

    # ── 5. 証明文（左）──────────────────────────────────────────────────────
    # 原本実測: x=89.28, y=610.02, size=10
    c.setFont(FJ, 10)
    c.drawString(89, 610, f"　{_ja_date(data['cert_date'])}現在の貴方ご名義")

    # 原本実測: x=85, y=594.76
    c.drawString(85, 594, "下記勘定残高について相違ないことを証明")

    # 原本実測: x=85, y=580.02
    c.drawString(85, 580, "いたします。")

    # 英語証明文: x=85, y=564.42/549.42/534.42, size=7
    c.setFont(FJ, 7)
    c.drawString(85, 564, "THIS IS TO CERTIFY THAT THE BALANCE OF")
    c.drawString(85, 549, "YOUR ACCOUNT(S) WITH MUFG Bank SHOW(S)")
    c.drawString(85, 534, "THE AMOUNT(S) INDICATED BELOW.")

    # ── 6. 銀行名（右）──────────────────────────────────────────────────────
    # 原本 LTFigure bbox=(302,585.8,472,600) → 幅170pt, 高14.2pt → size≈16
    c.setLineWidth(0.35)
    _t = c.beginText(302, 586)
    _t.setFont(FJ, 17)
    _t.setTextRenderMode(2)   # 塗り+輪郭 → 疑似ボールド
    _t.textLine("株式会社 三菱UFJ銀行")
    c.drawText(_t)
    c.setLineWidth(0.25)

    # 原本 LTFigure bbox=(302,565.8,382,575) → "MUFG Bank, Ltd." x=302, y≈566
    c.setFont(FJ, 10)
    c.drawString(302, 564, "MUFG Bank, Ltd.")

    # ── 印鑑（赤い公印）─────────────────────────────────────────────────────
    # 原本 LTFigure bbox=(478,562,524,607) → 中心(501,584.5), r≈22
    SEAL_RED = (0.72, 0.08, 0.08)
    c.setStrokeColorRGB(*SEAL_RED)
    c.setFillColorRGB(*SEAL_RED)
    c.setLineWidth(1.5)
    c.circle(501, 584, 22, stroke=1, fill=0)   # 一重円
    c.setFont(FJ, 6.5)
    c.drawCentredString(501, 589, "登記印")
    c.setLineWidth(0.6)
    c.line(484, 585, 518, 585)                  # 横線
    c.setFont(FJ, 7)
    c.drawCentredString(501, 576, "UFJ")
    # カラーリセット
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(0.25)

    # お取引店・電話
    # 原本実測: "お取引店 草津　支店" x=280, y=534.5, size=10
    c.setFont(FJ, 10)
    c.drawString(280, 534, f"お取引店　{data.get('branch', '')}　支店")

    # 原本実測: '電'(280,519.5) '話 077...'(290,519.5) → 連続描画
    c.drawString(280, 519, "電")
    c.drawString(290, 519, f"話　{data.get('phone', '')}")

    # ── 7. 残高テーブル ──────────────────────────────────────────────────────
    _draw_table(c, data, FJ)

    # ── 8. フッター ──────────────────────────────────────────────────────────
    # 原本実測: x=65, y=45/39/33/27, size=6
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


def _draw_table(c, data: dict, FJ: str):
    """
    残高テーブルを描画する
    原本 pdfminer 実測値に完全準拠
    全線: lw=0.25, 実線（setDash([])）
    """
    # ── 列境界（x 座標）──────────────────────────────────────────────────────
    # 原本実測: X1=65, X2=205, X3=290, X4=410, X5=530
    X1, X2, X3, X4, X5 = 65, 205, 290, 410, 530
    TW = X5 - X1  # = 465

    # ── 行の y 座標 ──────────────────────────────────────────────────────────
    top_y   = 502   # テーブル上端
    hdr_bot = 472   # ヘッダー下端 / データ行上端
    bot_y   = 52    # テーブル下端
    ROW_H   = 30    # 全行の高さ

    c.setDash([])         # 実線（必ず最初にリセット）
    c.setLineWidth(0.25)  # 原本: 全線 lw=0.25

    # ── 外枠 ─────────────────────────────────────────────────────────────────
    c.rect(X1, bot_y, TW, top_y - bot_y)

    # ── 主要縦区切り線（テーブル全高）────────────────────────────────────────
    # 原本実測: x=205, 290, 410 それぞれ y=52〜y=502
    for cx in [X2, X3, X4]:
        c.line(cx, bot_y, cx, top_y)

    # ── 水平区切り線（hdr_bot から ROW_H 毎）────────────────────────────────
    # 原本実測: y=472, 442, 412, ..., 82 (x=65〜530)
    y = hdr_bot
    while y > bot_y:
        c.line(X1, y, X5, y)
        y -= ROW_H

    # ── 数字グリッド縦線（実線、lw=0.25）────────────────────────────────────
    # 原本実測（全て y=52〜y=472）:
    #   残高列 (X3〜X4): x=317.5, 335.5, 354.5, 372.5, 391.5
    #   証券類列 (X4〜X5): x=437.5, 455.5, 474.5, 492.5, 511.5
    for gx in [317.5, 335.5, 354.5, 372.5, 391.5,
               437.5, 455.5, 474.5, 492.5, 511.5]:
        c.line(gx, bot_y, gx, hdr_bot)

    # ── ヘッダーテキスト ──────────────────────────────────────────────────────
    # 原本実測: x=X+1（X1+1=66, X2+1=206, X3+1=291, X4+1=411）
    c.setFont(FJ, 7)
    c.drawString(X1 + 1, 491, "勘定")
    c.drawString(X1 + 1, 480, "ACCOUNT")
    c.drawString(X2 + 1, 491, "口座番号")
    c.drawString(X2 + 1, 480, "ACCOUNT No.")
    c.drawString(X3 + 1, 491, "残高")
    c.drawString(X3 + 1, 480, "BALANCE")
    c.drawString(X4 + 1, 491, "(内決済未確認証券類)")
    c.setFont(FJ, 6)
    c.drawString(X4 + 1, 481, "(BILLS OR CHECKS FOR COLLECTION)")

    # ── 普通預金行 ────────────────────────────────────────────────────────────
    # 原本実測:
    #   "普　通　預　金" x=75 (=X1+10), y=444.5
    #   口座番号        h=227.87, y=444.5
    #   残高            x=360.57 (右端 X4=410 に右揃え)
    #   ¥0              x=517.64 (右端 X5=530 に右揃え)
    c.setFont(FJ, 10)
    c.drawString(X1 + 10, 444, "普　通　預　金")
    c.drawString(228, 444, data["account_no"])
    c.drawRightString(X4, 444, f'¥{int(data["balance"])}')
    c.drawRightString(X5, 444, "¥0")

    # ── 以下余白 ─────────────────────────────────────────────────────────────
    # 原本実測: x=145, y=414.5
    c.drawString(145, 414, "以下余白")


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

# test

# x

"""
残高証明書（三菱UFJ銀行形式）生成ツール — Streamlit Web アプリ
"""

import io
import os
import streamlit as st
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_W, PAGE_H = A4  # 595.28 × 841.89 pt
_FONT_PATH = os.path.join(os.path.dirname(__file__), "IBMPlexSansJP-Regular.ttf")
_FONT_REGISTERED = False

APP_TITLE = "残高証明書 生成ツール"


def _setup_font():
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont("JP", _FONT_PATH))
        _FONT_REGISTERED = True


def _ja_date(d: date) -> str:
    """date → 「2024 年 12 月 26 日」形式"""
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
    F = "JP"
    L = 30           # 左マージン（pt）
    R = PAGE_W - 25  # 右端
    T = PAGE_H - 35  # 上端

    # ── 1. ヘッダー ────────────────────────────────
    c.setFont(F, 19)
    c.drawString(L, T, "残　高　証　明　書")

    c.setFont(F, 10.5)
    c.drawString(L + 120, T, "ACCOUNT BALANCE CERTIFICATE")

    c.setFont(F, 7.5)
    c.drawRightString(R, T + 8,  "同文のもの　１通発行の内第　１号")
    c.drawRightString(R, T - 2,  "This is the 1st copy of 1 duplicate issued.")

    y_sub = T - 20
    c.setFont(F, 8.5)
    c.drawString(L, y_sub, "指定口座")
    c.drawRightString(R, y_sub, "１ページ")

    c.setLineWidth(0.5)
    c.line(L, y_sub - 6, R, y_sub - 6)

    # ── 2. 発行日（右上）──────────────────────────
    c.setFont(F, 10)
    c.drawRightString(R, y_sub - 23, _ja_date(data["issue_date"]))

    # ── 3. 住所・氏名（左側）─────────────────────
    ay = y_sub - 42
    c.setFont(F, 9.5)
    c.drawString(L + 5, ay, data["postal_code"])
    for ln in [data["address1"], data.get("address2", ""), data.get("address3", "")]:
        if ln and ln.strip():
            ay -= 15
            c.drawString(L + 5, ay, ln.strip())
    ay -= 15
    c.drawString(L + 5, ay, data["name"] + "　様")

    # ── 4. 区切り線（太）─────────────────────────
    sep_y = T - 140
    c.setLineWidth(1.2)
    c.line(L, sep_y, R, sep_y)
    c.setLineWidth(0.5)

    # ── 5. 証明文（左）＋ 銀行名（右）───────────
    mid = PAGE_W / 2 + 15
    ct_y = sep_y - 19

    # 証明文（日本語）
    c.setFont(F, 9.5)
    for ln in [
        f"　{_ja_date(data['cert_date'])}現在の貴方ご名義",
        "下記勘定残高について相違ないことを証明",
        "いたします。",
    ]:
        c.drawString(L + 5, ct_y, ln)
        ct_y -= 15

    ct_y -= 4
    c.setFont(F, 7.5)
    for ln in [
        "THIS IS TO CERTIFY THAT THE BALANCE OF",
        "YOUR ACCOUNT(S) WITH MUFG Bank SHOW(S)",
        "THE AMOUNT(S) INDICATED BELOW.",
    ]:
        c.drawString(L + 5, ct_y, ln)
        ct_y -= 11

    # 銀行名（右）
    bank_y = sep_y - 22
    c.setFont(F, 19)
    c.drawString(mid, bank_y, "株式会社 三菱UFJ銀行")
    c.setFont(F, 10)
    c.drawString(mid, bank_y - 22, "MUFG Bank, Ltd.")

    # 印鑑（円で代替）
    sx, sy = R - 22, bank_y - 15
    c.setLineWidth(2)
    c.circle(sx, sy, 20, stroke=1, fill=0)
    c.setFont(F, 7)
    c.drawCentredString(sx, sy + 3,  "登記印")
    c.drawCentredString(sx, sy - 6,  "UFJ")
    c.setLineWidth(0.5)

    # お取引店・電話
    br_y = bank_y - 52
    c.setFont(F, 9.5)
    c.drawString(mid, br_y,       f'お取引店　{data.get("branch", "亀有")}　支店')
    c.drawString(mid, br_y - 14,  f'電　　話　{data.get("phone", "03(3601)4151")}')

    # ── 6. 残高テーブル──────────────────────────
    _draw_table(c, data, F, L, R, sep_y - 118)

    # ── 7. フッター注意事項─────────────────────
    fy = 72
    c.setFont(F, 5.5)
    for note in [
        "・この証明書の金額は訂正いたしません。",
        "・金額は、証明日現在の元帳最終残高を表わし決済未確認の証券類を含んでいることがあります。"
        "この場合はその金額を｢(内決済未確認証券類)｣に表示します。",
        "・｢当座貸越(総合)｣には、普通預金貸越型のカードローンご利用額も含まれます。",
        "・口座番号欄は、口座指定のご依頼の場合のみ表示します。",
    ]:
        c.drawString(L, fy, note)
        fy -= 8


def _draw_table(c, data: dict, F: str, L: float, R: float, top: float):
    """残高テーブルを描画する"""
    TW = R - L

    # 列境界（x 座標）
    X1 = L
    X2 = L + int(TW * 0.330)   # 口座番号
    X3 = L + int(TW * 0.490)   # 残高（桁グリッド付き）
    X4 = L + int(TW * 0.730)   # 内決済未確認（桁グリッド付き）
    X5 = R

    HDR_H = 30   # ヘッダー行高さ
    ROW_H = 30   # データ行高さ
    EM_H  = 26   # 空行高さ

    def draw_row(y_top, h):
        """行枠と縦区切り線を描か（金額列は点線グリッド付き）"""
        c.setDash([])
        c.setLineWidth(0.5)
        c.rect(X1, y_top - h, TW, h)
        for cx in [X2, X3, X4]:
            c.line(cx, y_top - h, cx, y_top)
        # 残高列 桁グリッド（点線）
        dw3 = (X4 - X3) / 10
        c.setDash([1, 2])
        for i in range(1, 10):
            c.line(X3 + i * dw3, y_top - h, X3 + i * dw3, y_top)
        # 内決済列 桁グリッド（点線）
        dw4 = (X5 - X4) / 8
        for i in range(1, 8):
            c.line(X4 + i * dw4, y_top - h, X4 + i * dw4, y_top)
        c.setDash([])

    # ── ヘッダー行
    y = top
    draw_row(y, HDR_H)
    c.setFont(F, 8)
    c.drawString(X1 + 3, y - 11, "勘定")
    c.drawString(X1 + 3, y - 21, "ACCOUNT")
    c.drawString(X2 + 3, y - 11, "口座番号")
    c.drawString(X2 + 3, y - 21, "ACCOUNT No.")
    c.drawString(X3 + 3, y - 11, "残高")
    c.drawString(X3 + 3, y - 21, "BALANCE")
    c.setFont(F, 6)
    c.drawString(X4 + 3, y - 10, "(内決済未確認証券類)")
    c.drawString(X4 + 3, y - 19, "(BILLS OR CHECKS FOR COLLECTION)")

    # ── 普通預金行
    y -= HDR_H
    draw_row(y, ROW_H)
    c.setFont(F, 11)
    c.drawString(X1 + 5, y - 20, "普　通　預　金")
    c.setFont(F, 10)
    c.drawString(X2 + 5, y - 20, data["account_no"])
    c.drawRightString(X4 - 6,  y - 20, f'¥{int(data["balance"]):,}')
    c.drawRightString(X5 - 6,  y - 20, "¥0")

    # ── 以下余白行
    y -= ROW_H
    draw_row(y, ROW_H)
    c.setFont(F, 10)
    c.drawCentredString((X1 + X2) / 2, y - 20, "以下余白")

    # ── 空行（ページ下部まで埋める）
    n_empty = max(int((y - 88) / EM_H) - 1, 4)
    for _ in range(n_empty):
        y -= EM_H
        if y - EM_H < 88:
            break
        draw_row(y, EM_H)


# ══════════════════════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("🏦 " + APP_TITLE)
st.caption("三菱UFJ銀行形式の残高証明書PDFを生成します")
st.markdown("---")

# ── ① 宛先情報（左側）────────────────────────────────────────────────────
st.subheader("① 宛先情報（左側）")

col_p, col_n = st.columns([1, 1])
with col_p:
    postal = st.text_input("郵便番号", placeholder="例）963-8041")
with col_n:
    name = st.text_input("氏名（フルネーム）", placeholder="例）田中　拓郎")

addr1 = st.text_input(
    "住所①（都道府県・市区町村）",
    placeholder="例）福島県　郡山市",
)
addr2 = st.text_input(
    "住所②（番地・建物名など）",
    placeholder="例）富田町 52-1 スターハイツ E-1",
)

st.markdown("---")

# ── ② 発行日（右上）──────────────────────────────────────────────────────
st.subheader("② 発行日（右上）")
today = date.today()
issue_date = st.date_input("発行日", value=today)

st.markdown("---")

# ── ③ 証明内容（中央）────────────────────────────────────────────────────
st.subheader("③ 証明内容（中央）")
cert_date = st.date_input("証明日（残高の基準日）", value=today)

col_a, col_b = st.columns([1, 1])
with col_a:
    acct_no = st.text_input("口座番号", placeholder="例）0379501")
with col_b:
    balance = st.number_input("残高（円）", min_value=0, value=0, step=1000, format="%d")

st.markdown("---")

# ── 生成ボタン─────────────────────────────────────────────────────────────
if st.button("📄　残高証明書PDFり生成する", use_container_width=True, type="primary"):
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
                name=name.strip(),
                issue_date=issue_date,
                cert_date=cert_date,
                account_no=acct_no.strip(),
                balance=int(balance),
            ))

        st.success("✅ 生成完了！")

        # 結果メトリクス
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("氏名", name.strip())
        mc2.metric("口座番号", acct_no.strip())
        mc3.metric("残高", f"¥{int(balance):,}")

        # ダウンロード
        safe = name.strip().replace(" ", "_").replace("　", "_")
        fname = f"zanko_{issue_date.strftime('%Y%m%d')}_{safe}.pdf"
        st.download_button(
            "⬇️　PDFをダウンロード",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )

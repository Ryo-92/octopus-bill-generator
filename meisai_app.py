"""
電気ご使用量のお知らせ（中部電力ミライズ形式）生成ツール — Streamlit Web アプリ
フォント: ＭＳ明朝（msmincho.ttf — 原本と完全一致）
パスワード: Streamlit Cloud Secrets の APP_PASSWORD のみ — ソースコードに記載禁止
"""

import calendar as _cal
import glob as _glob
import hmac
import io
import json as _json
import os
import random as _rand
import urllib.request as _url_req
import streamlit as st
from datetime import date, timedelta
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── ページサイズ ─────────────────────────────────────────────────
PAGE_W, PAGE_H = 595, 842  # A4

# ── カラーパレット (RGB 0.0–1.0) ─────────────────────────────────
_C_GREEN    = (0.0,   0.69,  0.314)   # 緑: 線・ラベル
_C_LT_GREEN = (0.893, 0.954, 0.828)   # 薄緑: ボックス背景
_C_BEIGE    = (1.0,   0.938, 0.75)    # ベージュ: ヘッダー
_C_GRAY     = (0.937, 0.937, 0.937)   # グレー: タイトルボックス
_C_BLACK    = (0.0,   0.0,   0.0)

APP_TITLE = "電気ご使用量のお知らせ（中部電力ミライズ形式）"

# ── 全角変換 ─────────────────────────────────────────────────────
_FW  = str.maketrans('0123456789,', '０１２３４５６７８９，')
_FWD = str.maketrans('0123456789',  '０１２３４５６７８９')

def _fw_yen(n: int) -> str:
    """3413 → '３，４１３円'"""
    return f'{n:,}'.translate(_FW) + '円'

def _fw_yen_sen(yen: int, sen: int) -> str:
    """(963,42) → '９６３円　４２銭'"""
    return str(yen).translate(_FWD) + '円　' + f'{sen:02d}'.translate(_FWD) + '銭'

def _fw_yen_sen_ns(yen: int, sen: int) -> str:
    """(115,92) → '１１５円９２銭' (no space — inline in label)"""
    return str(yen).translate(_FWD) + '円' + f'{sen:02d}'.translate(_FWD) + '銭'

def _fw_sen(sen: int) -> str:
    return f'{sen:02d}'.translate(_FWD) + '銭'

# ── フォント ─────────────────────────────────────────────────────
# ＭＳ明朝 (msmincho.ttf) — 原本と同一フォント
_FONT_PATH = os.path.join(os.path.dirname(__file__), 'msmincho.ttf')
FJ = 'MSMincho'
_FONT_REG = False

def _ensure_font():
    global _FONT_REG
    if not _FONT_REG:
        pdfmetrics.registerFont(TTFont('MSMincho', _FONT_PATH))
        _FONT_REG = True

# ══════════════════════════════════════════════════════════════
# 描画ユーティリティ
# 座標系: pdfplumber 準拠 (top = ページ上端からの距離)
# bottom 値をベースライン近似として使用
# ══════════════════════════════════════════════════════════════
def _ry(top):
    """pdfplumber top → reportlab y"""
    return PAGE_H - top

def _tsb(c, x, bottom, text, sz, col=None, align='left', charSpace=None):
    """テキスト描画 (bottom = pdfplumber の glyph 下端)
    charSpace: Noneの場合はフォントサイズ別のデフォルト値を使用。
               明示的に指定した場合はそちらを優先（フィールド固有の文字間隔）。
    """
    if col is None:
        col = _C_BLACK
    c.setFont(FJ, sz)
    c.setFillColorRGB(*col)
    # 原本の文字間隔（Tc）に合わせて設定（pdfplumber 実測値）
    if charSpace is not None:
        tc = charSpace
    elif abs(sz - 6.84) < 0.01:
        tc = 0.144
    elif abs(sz - 8.28) < 0.01:
        tc = 0.216
    else:
        tc = 0
    # ＭＳ明朝 descent = 36/256 ≈ 0.1406 × sz
    # pdfplumber bottom = baseline + descent → baseline = bottom - descent
    rl_y = PAGE_H - bottom + sz * (36 / 256)
    s = str(text)
    if align == 'right':
        c.drawRightString(x, rl_y, s, charSpace=tc)
    elif align == 'center':
        c.drawCentredString(x, rl_y, s, charSpace=tc)
    else:
        c.drawString(x, rl_y, s, charSpace=tc)

def _hl(c, x1, top, x2, lw=1.08, col=None):
    if col is None: col = _C_GREEN
    c.setStrokeColorRGB(*col); c.setLineWidth(lw)
    c.line(x1, _ry(top), x2, _ry(top))

def _vl(c, x, top1, top2, lw=1.08, col=None):
    if col is None: col = _C_GREEN
    c.setStrokeColorRGB(*col); c.setLineWidth(lw)
    c.line(x, _ry(top1), x, _ry(top2))

def _fill(c, x0, top, x1, bottom, fill):
    c.setFillColorRGB(*fill)
    c.rect(x0, _ry(bottom), x1-x0, bottom-top, fill=1, stroke=0)

def _rr_fill(c, x0, top, x1, bottom, fill, r=5.4, stroke_col=None, sw=1.08):
    """角丸矩形 塗りつぶし（全4角丸）"""
    c.setFillColorRGB(*fill)
    if stroke_col:
        c.setStrokeColorRGB(*stroke_col); c.setLineWidth(sw)
    c.roundRect(x0, _ry(bottom), x1-x0, bottom-top, r,
                fill=1, stroke=1 if stroke_col else 0)

def _fill_path(c, x0, top, x1, bottom, fill, r=5.4,
               tl=True, tr=True, bl=True, br=True,
               stroke_col=None, sw=0.18):
    """塗り・選択的な角丸（参考PDFの非対称丸角に対応）。
    原本PDFの 'y' オペレータ（cp1=現在点）と完全一致するベジェ制御点を使用。
    tl/tr/bl/br = True で対応する角を丸める。
    stroke_col 指定時は外枠線も同一パスで描画（sw=線幅）。
    """
    rt = _ry(top)     # reportlab 上辺 y（大きい値）
    rb = _ry(bottom)  # reportlab 下辺 y（小さい値）
    c.setFillColorRGB(*fill)
    if stroke_col:
        c.setStrokeColorRGB(*stroke_col)
        c.setLineWidth(sw)
    p = c.beginPath()
    # 開始点: 上辺の左側（TL角丸あり → x0+r, なし → x0）
    p.moveTo(x0 + (r if tl else 0), rt)
    # 左上 (TL) 角
    if tl:
        # PDF 'y' operator: cp1=現在点(x0+r,rt), cp2=(x0,rt), end=(x0,rt-r)
        p.curveTo(x0 + r, rt, x0, rt, x0, rt - r)
    # 左辺を下へ
    p.lineTo(x0, rb + (r if bl else 0))
    # 左下 (BL) 角
    if bl:
        p.curveTo(x0, rb + r, x0, rb, x0 + r, rb)
    # 下辺を右へ
    p.lineTo(x1 - (r if br else 0), rb)
    # 右下 (BR) 角
    if br:
        p.curveTo(x1 - r, rb, x1, rb, x1, rb + r)
    # 右辺を上へ
    p.lineTo(x1, rt - (r if tr else 0))
    # 右上 (TR) 角
    if tr:
        # PDF 'y' operator: cp1=現在点(x1,rt-r), cp2=(x1,rt), end=(x1-r,rt)
        p.curveTo(x1, rt - r, x1, rt, x1 - r, rt)
    # 上辺を左へ close で始点まで戻る
    p.close()
    c.drawPath(p, fill=1, stroke=1 if stroke_col else 0)

def _rr_outline(c, x0, top, x1, bottom, col, sw=1.08, r=5.4):
    """角丸矩形 外枠のみ"""
    c.setStrokeColorRGB(*col); c.setLineWidth(sw)
    c.roundRect(x0, _ry(bottom), x1-x0, bottom-top, r, fill=0, stroke=1)


# ══════════════════════════════════════════════════════════════
# PDF 生成
# ══════════════════════════════════════════════════════════════
def generate_pdf(d: dict) -> bytes:
    _ensure_font()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    _draw(c, d)
    c.save()
    return buf.getvalue()


def _draw(c, d):
    # ─── 1. タイトル グレーボックス（塗りのみ・枠線なし）────
    c.setFillColorRGB(*_C_GRAY)
    c.rect(13.14, _ry(51.44), 284.4-13.14, 51.44-31.82, fill=1, stroke=0)

    # 個別文字を等間隔に配置 (bottom=48.5)
    _TITLE = [('電',14.0),('気',39.3),('ご',64.5),('使',89.7),
              ('用',114.9),('量',140.1),('の',165.3),('お',190.6),
              ('知',215.8),('ら',241.0),('せ',266.2)]
    for ch, x0 in _TITLE:
        _tsb(c, x0, 48.5, ch, 13.68)

    # ─── 1b. 右上ロゴ（中部電力ミライズ株式会社）────────────
    _logo_path = os.path.join(os.path.dirname(__file__), 'mirise_logo.png')
    if os.path.exists(_logo_path):
        c.drawImage(_logo_path, 417.8, _ry(50.6), width=139.2, height=11.2,
                    preserveAspectRatio=False, mask='auto')

    # ─── 2. 発行日 (右揃え x=555.3) ──────────────────────
    _tsb(c, 555.3, 71.7, d['issue_date_str'], 8.28, align='right')

    # ─── 3. 挨拶文（年月分はベージュ角丸ボックスで囲む）────
    _tsb(c, 21.2,  89.7, '毎度お引立ていただきありがとうございます。', 8.28)
    # 年月分ボックス: x=205.56〜289.80 top=78.44〜92.84 (pdfplumber 実測値)
    _rr_fill(c, 205.56, 78.44, 289.8, 92.84, _C_BEIGE, r=5.4,
             stroke_col=(1.0, 0.0, 0.0), sw=0.72)
    _tsb(c, 209.2, 89.7, f'{d["target_year"]}年{d["target_month"]}月分', 8.28)
    _tsb(c, 297.0, 89.7, 'の電気ご使用量を下記のとおりお知らせいたします。', 8.28)

    # ─── 4. おなまえ ────────────────────────────────────────
    for ch, x0 in [('お',14.0),('な',27.8),('ま',41.6),('え',55.4)]:
        _tsb(c, x0, 112.7, ch, 8.28)
    _tsb(c, 70.9, 112.7, f'{d["name"]}　様', 8.28)

    # ─── 5–9. 各セクション ───────────────────────────────
    _draw_customer_table(c, d)
    _draw_usage_billing(c, d)
    _draw_billing_detail(c, d)
    _draw_left_panel(c, d)
    _draw_bottom_info(c, d)

    # ─── 10. ご使用場所 ──────────────────────────────────
    _tsb(c, 14.0, 766.7, '[ご使用場所]', 6.84)
    _tsb(c, 21.2, 778.2, d['address1'], 6.84)
    _tsb(c, 21.2, 789.7, d['address2'], 6.84)


# ── お客さま情報テーブル ──────────────────────────────────────
def _draw_customer_table(c, d):
    # ベージュ角丸ヘッダー（左: 左上角のみ丸, 右: 右上角のみ丸 ← 原本に合わせた非対称丸角）
    # 原本に合わせ lw=0.18 の赤細外枠を追加
    _fill_path(c, 11.34, 124.88, 110.52, 138.56, _C_BEIGE, r=5.4,
               tl=True, tr=False, bl=False, br=False,
               stroke_col=(1.0, 0.0, 0.0), sw=0.18)
    _fill_path(c, 129.78, 124.88, 577.98, 138.56, _C_BEIGE, r=5.4,
               tl=False, tr=True, bl=False, br=False,
               stroke_col=(1.0, 0.0, 0.0), sw=0.18)

    # 緑の角丸外枠
    _rr_outline(c, 11.34, 124.88, 577.98, 184.64, _C_GREEN, sw=1.08, r=5.4)

    # 水平線 (pdfplumber 実測値に完全一致)
    _hl(c, 11.34, 138.56, 577.98, lw=1.08)
    _hl(c, 11.34, 161.60, 577.98, lw=1.08)

    # 厚い縦区切り (pdfplumber 実測値: x, y-start を精密化)
    for x in [110.52, 129.78, 323.46, 372.24, 406.62]:
        _vl(c, x, 124.88, 161.6, lw=1.08)

    # 細い縦区切り: お客さま番号の桁 (pdfplumber 実測値)
    for x in [34.2, 64.8, 80.1, 95.22, 102.96]:
        _vl(c, x, 138.56, 161.6, lw=0.36)

    # 細い縦区切り: 供給地点特定番号の桁 (pdfplumber 実測値)
    for x in [423.54, 454.32, 484.56, 514.80, 545.76]:
        _vl(c, x, 138.56, 161.60, lw=0.36)

    # ── 行 1: ヘッダーラベル (bottom=135.8) ──────────────
    B1 = 135.8
    _tsb(c, 21.2,  B1, 'お', 6.84)
    _tsb(c, 34.9,  B1, '客', 6.84)
    _tsb(c, 48.6,  B1, 'さ', 6.84)
    _tsb(c, 62.3,  B1, 'ま', 6.84)
    _tsb(c, 76.0,  B1, '番', 6.84)
    _tsb(c, 89.6,  B1, '号', 6.84)
    _tsb(c, 113.4, B1, '日程', 6.84)
    _tsb(c, 187.9, B1, '契', 6.84)
    _tsb(c, 209.3, B1, '約', 6.84)
    _tsb(c, 230.6, B1, '種', 6.84)
    _tsb(c, 252.0, B1, '別', 6.84)
    _tsb(c, 333.4, B1, '契約容量', 6.84)
    _tsb(c, 379.3, B1, '力', 6.84)
    _tsb(c, 389.7, B1, '率', 6.84)
    _tsb(c, 443.0, B1, '供', 6.84)
    _tsb(c, 454.9, B1, '給', 6.84)
    _tsb(c, 466.7, B1, '地', 6.84)
    _tsb(c, 478.6, B1, '点', 6.84)
    _tsb(c, 490.5, B1, '特', 6.84)
    _tsb(c, 502.4, B1, '定', 6.84)
    _tsb(c, 514.3, B1, '番', 6.84)
    _tsb(c, 526.1, B1, '号', 6.84)

    # ── 行 2: データ (bottom=157.0) ───────────────────────
    B2 = 157.0
    _tsb(c, 12.06, B2, d['customer_no'],     6.84, charSpace=0.72)
    _tsb(c, 113.4, B2, d['schedule'],         6.84)
    _tsb(c, 131.0, B2, d['contract_type'],    6.84)
    cap = d.get('contract_capacity', '')
    if cap:
        # 原本実測: '３０Ａ' x0=333.0 ← ヘッダー「契約容量」x0=333.4 と同じ左揃え
        _tsb(c, 333.4, B2, f'{cap}Ａ', 6.84)
    pf = d.get('power_factor', '')
    if pf:
        _tsb(c, 375.8, B2, pf, 6.84)
    _tsb(c, 409.5, B2, d['supply_point_id'], 6.84, charSpace=0.72)

    # ── 行 3: 縦区切り + 検針日等 ─────────────────────────
    for x in [72.90, 201.60, 244.62]:
        _vl(c, x, 161.60, 184.64, lw=1.08)

    B3h = 170.3   # ヘッダー bottom
    B3d = 180.0   # データ bottom
    _tsb(c, 14.0,  B3h, '検針日', 6.84)
    _tsb(c, 77.9,  B3h, 'ご使用期間', 6.84)
    _tsb(c, 205.6, B3h, 'ご使用日数', 6.84)
    _tsb(c, 248.2, B3h, '記事', 6.84)

    # データ: 原本に合わせて右揃え
    _tsb(c, 70.0,  B3d, d['meter_read_date'], 6.84, align='right')
    _tsb(c, 196.9, B3d, d['usage_period'], 6.84, align='right')
    _tsb(c, 236.7, B3d, d['usage_days'] + '日', 6.84, align='right')


# ── ご使用量・ご請求額ボックス ────────────────────────────────
def _draw_usage_billing(c, d):
    # ── 薄緑 fill を先に描き、その後に外枠を重ねる ──────────────
    # （外枠を先に描くと fill が外枠の内側半分を覆い、縦線が細く見えるため）

    # 左の薄緑角丸ボックス（fill）: 上2角のみ丸, 下は直角（原本に合わせた非対称丸角）
    # stroke_col なし: 原本は fill 専用パス（境界線は外枠と _hl が担う）
    _fill_path(c, 11.34, 191.48, 360.36, 275.54, _C_LT_GREEN, r=5.4,
               tl=True, tr=True, bl=False, br=False)
    # 右の薄緑角丸ボックス（fill）: 上2角のみ丸, 下は直角 (pdfplumber 実測値)
    _fill_path(c, 363.42, 191.48, 577.98, 236.48, _C_LT_GREEN, r=5.4,
               tl=True, tr=True, bl=False, br=False)

    # ── 大パネル外枠（緑 rounded outline）── fill の上に重ねて描く ──
    # 左パネル外枠: x=10.80〜360.36  top=190.76〜690.08 (pdfplumber 実測値)
    _rr_outline(c, 10.80, 190.76, 360.36, 690.08, _C_GREEN, sw=1.08, r=5.4)
    # 右パネル外枠: x=363.42〜577.98  top=190.04〜679.10 (pdfplumber 実測値)
    _rr_outline(c, 363.42, 190.04, 577.98, 679.10, _C_GREEN, sw=1.08, r=5.4)

    # ご使用量 (bottom=200.6)
    _tsb(c, 14.0,  200.6, 'ご使用量', 6.84)
    # 原本実測: '９２ｋＷｈ' x1=309.4 → right-align at x=309.4
    _tsb(c, 309.4, 200.6, d['usage_kwh'] + 'ｋＷｈ', 6.84, align='right')

    # ご請求額 (bottom=203.1)
    B_r1 = 203.1
    _tsb(c, 364.0, B_r1, 'ご請求額', 6.84)
    _tsb(c, 563.4, B_r1, _fw_yen(d['billing_amount']), 6.84, align='right')

    # うち消費税等相当額 (bottom=214.6)
    B_r2 = 214.6
    _tsb(c, 364.0, B_r2, 'うち消費税等相当額', 6.84)
    _tsb(c, 563.4, B_r2, _fw_yen(d['tax_amount']), 6.84, align='right')

    # 右パネル仕切り線 (pdfplumber 実測値)
    _hl(c, 363.42, 236.48, 577.98, lw=0.72)


# ── ご請求額内訳 (右パネル) ───────────────────────────────────
def _draw_billing_detail(c, d):
    B_hd = 249.2
    _tsb(c, 364.0, B_hd, '［ご請求額内訳］', 6.84)

    # 基本料金 (bottom=261.0)
    B1 = 261.0
    _tsb(c, 366.7, B1, '基本料金', 6.84)
    _tsb(c, 550.3, B1, _fw_yen(d['basic_yen']), 6.84, align='right')
    _tsb(c, 553.3, B1, _fw_sen(d['basic_sen']), 6.84)

    # 電力量料金 1段料金 (bottom=272.0)
    B2 = 272.0
    _tsb(c, 366.7, B2, '電力量料金　１段料金', 6.84)
    _tsb(c, 550.3, B2, _fw_yen(d['energy1_yen']), 6.84, align='right')
    _tsb(c, 553.3, B2, _fw_sen(d['energy1_sen']), 6.84)

    # うち燃料費調整額 (bottom=284.3)
    B3 = 284.3
    fuel_str = ('うち燃料費調整額　'
                + _fw_yen_sen_ns(d['fuel_adj_yen'], d['fuel_adj_sen']))
    _tsb(c, 366.5, B3, fuel_str, 6.84)

    # 再エネ発電促進賦課金 (bottom=295.1)
    B4 = 295.1
    _tsb(c, 366.7, B4, '再エネ発電促進賦課金', 6.84)
    _tsb(c, 550.3, B4, _fw_yen(d['renewable_yen']), 6.84, align='right')


# ── 左パネル（計器セクション + グリッド線） ──────────────────
# 計器表示セル x 座標 (column 1: x=65→127.8)
_METER_CELLS = [67.7, 73.0, 78.4, 83.8, 89.1,
                94.5, 99.8, 105.2, 110.6, 115.9, 121.3]

def _draw_meter_digits(c, reading_str, bottom):
    """指示数をセル単位で描画 (半角 sz=7)"""
    if '.' in reading_str:
        int_s, dec_s = reading_str.split('.', 1)
    else:
        int_s, dec_s = reading_str, '0'

    sz = 6.84
    # 整数部: cells 0-7 右寄せ
    start = 8 - len(int_s)
    for i, ch in enumerate(int_s):
        ci = start + i
        if 0 <= ci < 8:
            _tsb(c, _METER_CELLS[ci], bottom, ch, sz)
    # 小数点: cell 8
    _tsb(c, _METER_CELLS[8], bottom, '.', sz)
    # 小数部: cells 9-10
    for i, ch in enumerate(dec_s[:2]):
        _tsb(c, _METER_CELLS[9 + i], bottom, ch, sz)


def _draw_left_panel(c, d):
    # ── 主要水平線 (pdfplumber 実測値) ───────────────────
    _hl(c, 11.34, 276.26, 360.36, lw=1.08)
    _hl(c, 10.44, 287.42, 360.00, lw=0.72)
    _hl(c, 10.80, 356.90, 360.00, lw=0.72)
    _hl(c, 10.98, 370.40, 360.00, lw=0.72)
    _hl(c, 10.80, 408.56, 359.28, lw=0.36)
    _hl(c, 10.80, 444.74, 359.28, lw=0.36)
    _hl(c, 10.80, 483.80, 359.82, lw=1.08)
    _hl(c, 10.80, 496.04, 360.00, lw=0.72)
    _hl(c, 10.80, 561.92, 360.00, lw=0.72)
    _hl(c, 10.80, 575.60, 360.00, lw=0.72)
    _hl(c, 10.80, 613.76, 243.90, lw=0.36)
    _hl(c, 10.80, 650.12, 243.90, lw=0.36)

    # ── 主要縦区切り (全体) (pdfplumber 実測値) ──────────
    _vl(c, 127.80, 276.26, 690.08, lw=1.08)
    _vl(c, 243.90, 276.26, 690.08, lw=1.08)

    # ── 上部セクション縦区切り (pdfplumber 実測値) ────────
    _vl(c,  64.98, 276.26, 356.90, lw=0.36)
    _vl(c, 181.62, 275.72, 357.62, lw=0.36)
    _vl(c, 296.10, 276.26, 356.90, lw=0.36)

    # ── 計器表示縦区切り (pdfplumber 実測値) ─────────────
    _vl(c,  64.98, 483.44, 562.10, lw=0.36)
    _vl(c, 181.62, 483.44, 562.10, lw=0.36)
    _vl(c, 296.10, 483.44, 562.10, lw=0.36)

    # ── 計器セクション ────────────────────────────────
    B_k = 286.1
    _tsb(c, 14.0,  B_k, f'計器番号{d["meter_no"]}', 6.84)
    _tsb(c, 71.8,  B_k, '第', 6.84)
    _tsb(c, 85.5,  B_k, '１', 6.84)
    _tsb(c, 99.2,  B_k, '計', 6.84)
    _tsb(c, 112.9, B_k, '器', 6.84)

    _tsb(c, 14.0, 296.9, '当月指示数', 6.84)
    _draw_meter_digits(c, d['current_reading'], 296.9)

    _tsb(c, 14.0, 308.4, '前月指示数', 6.84)
    _draw_meter_digits(c, d['prev_reading'], 308.4)

    _tsb(c, 14.0, 319.9, '差引', 6.84)
    _draw_meter_digits(c, d['diff_reading'], 319.9)


# ── 単価情報・翌月ご案内 ──────────────────────────────────────
def _draw_bottom_info(c, d):
    # ── 翌月案内ボックス外枠 ─────────────────────────────
    # 左ボックス（空欄）: x=11.34〜323.46  top=702.32〜748.22 (pdfplumber 実測値)
    _rr_outline(c, 11.34, 702.32, 323.46, 748.22, _C_GREEN, sw=1.08, r=5.4)
    # 右ボックス（翌月案内）: x=363.42〜577.98  top=702.32〜748.22 (pdfplumber 実測値)
    _rr_outline(c, 363.42, 702.32, 577.98, 748.22, _C_GREEN, sw=1.08, r=5.4)

    # 当月燃料費調整単価 (bottom=689.3)
    B1 = 689.3
    _tsb(c, 369.2, B1, '当月燃料費調整単価（税込）', 6.84)
    _tsb(c, 518.9, B1, str(d['fuel_adj_unit_yen']).translate(_FWD) + '円', 6.84, align='right')
    _tsb(c, 522.0, B1, f'{d["fuel_adj_unit_sen"]:02d}'.translate(_FWD) + '銭／ｋＷｈ', 6.84)

    # 再エネ発電促進賦課金単価 (bottom=697.7)
    B2 = 697.7
    _tsb(c, 369.2, B2, '再エネ発電促進賦課金単価（税込）', 6.84)
    _tsb(c, 518.9, B2, str(d['renewable_unit_yen']).translate(_FWD) + '円', 6.84, align='right')
    _tsb(c, 522.0, B2, f'{d["renewable_unit_sen"]:02d}'.translate(_FWD) + '銭／ｋＷｈ', 6.84)

    # 翌月（）のご案内 (bottom=714.5)
    B3 = 714.5
    nm = d.get('next_month_label', '')
    _tsb(c, 371.9, B3, f'翌月（　{nm}月分）のご案内', 6.84)

    # 翌月 検針日・ご使用期間 (bottom=728.5)
    B4 = 728.5
    _tsb(c, 371.9, B4, '検針日', 6.84)
    _tsb(c, 409.5, B4, d['next_meter_read_date'], 6.84)
    _tsb(c, 449.3, B4, 'ご使用期間', 6.84)
    _tsb(c, 506.9, B4, d['next_usage_period'], 6.84)

    # 翌月 燃料費調整単価 (bottom=739.5) — 原本に合わせ円・銭を分割描画 (円x1=490.32, 銭x0=491.04)
    B5 = 739.5
    _tsb(c, 371.9, B5, '燃料費調整単価（税込）', 6.84)
    _tsb(c, 490.32, B5, str(d['next_fuel_adj_unit_yen']).translate(_FWD) + '円', 6.84, align='right')
    _tsb(c, 491.04, B5, f'{d["next_fuel_adj_unit_sen"]:02d}'.translate(_FWD) + '銭／ｋＷｈ', 6.84)


# ══════════════════════════════════════════════════════════════
# 住所補完ユーティリティ
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def _lookup_address_by_zip(zip7: str) -> tuple:
    """
    郵便番号（7桁数字文字列）から住所を取得する。zipcloud API を使用。
    Returns: (都道府県, 市区町村, 町名)  失敗時は ("", "", "")
    """
    url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip7}"
    try:
        with _url_req.urlopen(url, timeout=5) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        if data.get('results'):
            r = data['results'][0]
            return (r.get('address1', ''), r.get('address2', ''), r.get('address3', ''))
    except Exception:
        pass
    return ('', '', '')


# ══════════════════════════════════════════════════════════════
# 認証
# ══════════════════════════════════════════════════════════════
def _check_password() -> bool:
    if st.session_state.get('_authenticated'):
        return True
    pw_input = st.text_input('🔐　パスワード', type='password', key='_pw_meisai')
    if st.button('ログイン', key='_login_meisai'):
        try:
            correct = st.secrets['APP_PASSWORD']
        except Exception:
            st.error('サーバー設定エラー：APP_PASSWORD が未設定です。')
            return False
        if hmac.compare_digest(pw_input, correct):
            st.session_state['_authenticated'] = True
            st.rerun()
        else:
            st.error('❌ パスワードが正しくありません。')
    return False


# ══════════════════════════════════════════════════════════════
# 自動計算ヘルパー（料金定数・日程計算・ランダム生成）
# ══════════════════════════════════════════════════════════════

def _fw_date(d_: date) -> str:
    """date → 'M月D日'（全角数字）"""
    return str(d_.month).translate(_FWD) + '月' + str(d_.day).translate(_FWD) + '日'

# ── 料金定数（中部電力ミライズ 従量電灯B 30A 2026年度）─────────
_BASIC_YEN,  _BASIC_SEN  = 963, 42   # 基本料金（税込）
_ENERGY_RATE1 = 21.20   # 第1段階税込単価（〜120kWh）  ← 原本実績から逆算
_ENERGY_RATE2 = 28.19   # 第2段階税込単価（121〜300kWh）
_ENERGY_RATE3 = 32.62   # 第3段階税込単価（300kWh超）
_RENEW_YEN,  _RENEW_SEN  = 4, 18    # 再エネ賦課金単価（税込）2026年度

# 燃料費調整単価テーブル（低圧 税込 円/kWh）— 中部電力ミライズ公式値
# 出典: https://miraiz.chuden.co.jp/home/electric/contract/fuelcost_transition/
_FUEL_ADJ_TABLE = {
    (2026,  7): (1, 49),  (2026,  6): (1, 35),  (2026,  5): (1, 26),
    (2025,  7): (1, 98),  (2025,  6): (2, 63),  (2025,  5): (2, 84),
    (2025,  4): (1, 64),  (2025,  1): (0, 79),
    (2025, 12): (0, 86),  (2025, 11): (0, 93),
    (2024, 12): (2, 59),  (2024,  1): (2, 33),
}

def _get_fuel_adj(year: int, month: int):
    """月別燃料費調整単価（公式テーブルにない月は最新既知値）"""
    return _FUEL_ADJ_TABLE.get((year, month), (1, 49))

def _adj_inspection(dt: date) -> date:
    """土曜 → 翌月曜(+2)、日曜 → 翌月曜(+1)"""
    if dt.weekday() == 5: return dt + timedelta(days=2)
    if dt.weekday() == 6: return dt + timedelta(days=1)
    return dt

def _inspection_date(year: int, month: int, sched: int) -> date:
    """日程番号から検針日を算出（月末超えは月末にclamp）"""
    last = _cal.monthrange(year, month)[1]
    return _adj_inspection(date(year, month, min(sched, last)))

def _gen_usage_kwh(rng, billing_month: int, usage_days: int) -> int:
    """季節・使用日数に応じたご使用量をランダム生成"""
    # 成人男性 or 女性をランダム選択
    daily = rng.uniform(4.4, 8.4) if rng.random() < 0.5 else rng.uniform(3.6, 6.8)
    # 季節係数（billing_month ≒ 検針月 = 使用期間の後半が属する月）
    factors = {
        1: 1.30, 2: 1.25, 3: 1.05, 4: 0.88, 5: 0.85,
        6: 0.92, 7: 1.22, 8: 1.38, 9: 1.12, 10: 0.90,
        11: 1.05, 12: 1.25,
    }
    return max(30, min(600, round(daily * factors.get(billing_month, 1.0) * usage_days)))

def _calc_billing(usage_kwh: int, fuel_yen: int, fuel_sen: int) -> dict:
    """ご請求額の内訳を計算して返す"""
    fu = fuel_yen + fuel_sen / 100   # 燃料費調整単価 (円/kWh)
    # 電力量料金ベース（燃料費調整前）
    if usage_kwh <= 120:
        base = usage_kwh * _ENERGY_RATE1
    elif usage_kwh <= 300:
        base = 120 * _ENERGY_RATE1 + (usage_kwh - 120) * _ENERGY_RATE2
    else:
        base = 120 * _ENERGY_RATE1 + 180 * _ENERGY_RATE2 + (usage_kwh - 300) * _ENERGY_RATE3
    # うち燃料費調整額
    fuel_total = usage_kwh * fu
    # 電力量料金合計（燃料費調整込み）
    energy = base + fuel_total
    ey = int(energy)
    es = round((energy - ey) * 100)
    if es >= 100: ey += 1; es -= 100
    fy = int(fuel_total)
    fs = round((fuel_total - fy) * 100)
    if fs >= 100: fy += 1; fs -= 100
    # 再エネ賦課金（銭以下切り捨て）
    ry = int(usage_kwh * (_RENEW_YEN + _RENEW_SEN / 100))
    # 合計・税（円以下切り捨て）
    total = int((_BASIC_YEN + _BASIC_SEN / 100) + energy + ry)
    tax   = int(total * 10 / 110)
    return dict(
        billing_amount=total, tax_amount=tax,
        basic_yen=_BASIC_YEN, basic_sen=_BASIC_SEN,
        energy1_yen=ey, energy1_sen=es,
        fuel_adj_yen=fy, fuel_adj_sen=fs,
        renewable_yen=ry,
        fuel_adj_unit_yen=fuel_yen, fuel_adj_unit_sen=fuel_sen,
        renewable_unit_yen=_RENEW_YEN, renewable_unit_sen=_RENEW_SEN,
    )

def _gen_supply_point_id(cno: str) -> str:
    """供給地点特定番号を生成（半角22桁）: '040' + お客さま番号13桁 + '000000'"""
    h = cno.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    digits = ''.join(c for c in h if c.isdigit())
    return '040' + digits.zfill(13)[:13] + '000000'


# ══════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title=APP_TITLE, layout='centered')
st.title('⚡ ' + APP_TITLE)
st.caption('中部電力ミライズ形式の電気ご使用量のお知らせPDFを生成します')
st.markdown('---')

if not _check_password():
    st.stop()

today = date.today()
_fw_tr = str.maketrans('0123456789', '０１２３４５６７８９')

# ── ① 基本情報 ──────────────────────────────────────────────
st.subheader('① 基本情報')
col1, col2 = st.columns([1, 1])
with col1:
    name = st.text_input('おなまえ', value='田中　太郎',
                         help='姓と名の間に全角スペースを入れてください')
    customer_no = st.text_input('お客さま番号（13桁）', value='１１０３９７３０２００５０',
                                help='全角数字13桁（3+4+2+2+1+1 の形式）')
with col2:
    target_ym = st.date_input('年月（月初日で指定）',
                              value=date(today.year, today.month, 1))
    schedule = st.selectbox(
        '日程（検針スケジュール番号）',
        [f'{i:02d}' for i in range(1, 20)],
        index=7,   # デフォルト: 08
        help='01〜19 から選択。検針日・使用期間・使用日数を自動計算します。',
    )

st.markdown('---')

# ── ② ご使用場所 ─────────────────────────────────────────
st.subheader('② ご使用場所')

if '_meisai_addr1' not in st.session_state:
    st.session_state['_meisai_addr1'] = '東京都　千代田区　千代田　１丁目　１－１'

postal_raw = st.text_input(
    '郵便番号',
    placeholder='例: 460-0008 または ４６０－０００８',
    help='7桁入力すると住所①を自動補完します。半角・全角どちらでも可。',
)
_zip_half   = postal_raw.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
_zip_digits = ''.join(c for c in _zip_half if c.isdigit())
if len(_zip_digits) == 7 and st.session_state.get('_meisai_last_zip') != _zip_digits:
    _z1, _z2, _z3 = _lookup_address_by_zip(_zip_digits)
    if _z1:
        st.session_state['_meisai_addr1'] = '　'.join(p for p in [_z1, _z2, _z3] if p)
        st.session_state['_meisai_last_zip'] = _zip_digits
        st.rerun()

address1 = st.text_input(
    '住所①（都道府県～番地）',
    key='_meisai_addr1',
    placeholder='例: 東京都　千代田区　千代田　１丁目　１－１',
    help='郵便番号を入力すると都道府県・市区町村・町名が自動補完されます。番地は手動で追記してください。',
)
address2 = st.text_input('住所②（建物名・部屋番号、任意）',
    value='', placeholder='例: ○○マンション　１０１号室')

st.markdown('---')

# ══════════════════════════════════════════════════════════════
# 自動計算（日程 → 日付 → 使用量 → 請求額）
# ══════════════════════════════════════════════════════════════
sched_num = int(schedule)
b_year, b_month = target_ym.year, target_ym.month
p_year, p_month = (b_year - 1, 12) if b_month == 1  else (b_year, b_month - 1)
n_year, n_month = (b_year + 1,  1) if b_month == 12 else (b_year, b_month + 1)

cur_insp  = _inspection_date(b_year, b_month, sched_num)
prev_insp = _inspection_date(p_year, p_month, sched_num)
next_insp = _inspection_date(n_year, n_month, sched_num)

usage_start      = prev_insp
usage_end        = cur_insp - timedelta(1)
usage_days       = (cur_insp - prev_insp).days
next_usage_start = cur_insp
next_usage_end   = next_insp - timedelta(1)

# 自動計算プレビューを表示
st.info(
    f'📅 **自動計算プレビュー**　　'
    f'検針日: **{_fw_date(cur_insp)}**　／　'
    f'ご使用期間: **{_fw_date(usage_start)}〜{_fw_date(usage_end)}**　／　'
    f'ご使用日数: **{usage_days}日**'
)

# 乱数キャッシュ（年月・日程が変わった時だけ再生成、おなまえや住所変更では変えない）
_cache_key = f'{b_year}_{b_month}_{sched_num}'
if st.session_state.get('_cache_key') != _cache_key:
    _rng = _rand.Random(hash(_cache_key))
    st.session_state['_cache_key']    = _cache_key
    st.session_state['_usage_kwh']    = _gen_usage_kwh(_rng, b_month, usage_days)
    st.session_state['_prev_reading'] = round(_rng.uniform(5000, 25000), 1)
    st.session_state['_meter_no']     = str(_rng.randint(0, 999)).zfill(3)

usage_kwh_n = st.session_state['_usage_kwh']
prev_rdg    = st.session_state['_prev_reading']
cur_rdg     = round(prev_rdg + usage_kwh_n, 1)
meter_no_n  = st.session_state['_meter_no']

# 燃料費調整単価（公式テーブル参照）
fuel_yen, fuel_sen = _get_fuel_adj(b_year, b_month)
nf_yen,   nf_sen   = _get_fuel_adj(n_year, n_month)

# 請求額計算
billing = _calc_billing(usage_kwh_n, fuel_yen, fuel_sen)

# 翌月 燃料費調整単価 文字列
nf_str = (str(nf_yen).translate(_fw_tr) + '円'
          + f'{nf_sen:02d}'.translate(_fw_tr) + '銭／ｋＷｈ')

# 発行日 = 今日
issue_date_str = str(today.year).translate(_fw_tr) + '年' + _fw_date(today)

# 供給地点特定番号（半角生成 → 全角変換）
sp_id = _gen_supply_point_id(customer_no).translate(_FWD)

# ── データ辞書 ────────────────────────────────────────────────
data = dict(
    name              = name.strip(),
    customer_no       = customer_no.strip(),
    schedule          = schedule.translate(_FWD),    # '08' → '０８'
    contract_type     = '従量電灯Ｂ',
    contract_capacity = '３０',
    power_factor      = '',                          # 常に空欄
    meter_no          = meter_no_n.translate(_FWD),  # '046' → '０４６'
    supply_point_id   = sp_id,

    issue_date_str    = issue_date_str,
    target_year       = str(b_year).translate(_fw_tr),
    target_month      = str(b_month).translate(_fw_tr),
    meter_read_date   = _fw_date(cur_insp),

    usage_period      = f'{_fw_date(usage_start)}〜{_fw_date(usage_end)}',
    usage_days        = str(usage_days).translate(_fw_tr),
    usage_kwh         = str(usage_kwh_n).translate(_fw_tr),

    current_reading   = f'{cur_rdg:.1f}',
    prev_reading      = f'{prev_rdg:.1f}',
    diff_reading      = f'{usage_kwh_n}.0',

    # 請求額内訳（自動計算）
    **billing,

    next_month_label       = str(n_month).translate(_fw_tr),
    next_meter_read_date   = _fw_date(next_insp),
    next_usage_period      = f'{_fw_date(next_usage_start)}〜{_fw_date(next_usage_end)}',
    next_fuel_adj_unit_str = nf_str,
    next_fuel_adj_unit_yen = nf_yen,
    next_fuel_adj_unit_sen = nf_sen,

    # U+2212（数学マイナス）→ U+FF0D（全角ハイフン）に正規化（MS Mincho での半角化を防止）
    address1 = address1.strip().replace('−', '－'),
    address2 = address2.strip().replace('−', '－'),
)

if st.button('⚡　電気ご使用量のお知らせ PDF を生成する',
             use_container_width=True, type='primary'):
    with st.spinner('PDF を生成中…'):
        pdf_bytes = generate_pdf(data)

    fname = f'Webmeisai{b_year}{b_month:02d}.pdf'
    st.download_button(
        label='📄　PDF をダウンロード',
        data=pdf_bytes,
        file_name=fname,
        mime='application/pdf',
        use_container_width=True,
    )
    yr_fw = str(b_year).translate(_fw_tr)
    mo_fw = str(b_month).translate(_fw_tr)
    st.success(f'✅ {yr_fw}年{mo_fw}月分の明細書を生成しました。')

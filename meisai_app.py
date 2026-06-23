"""
電気ご使用量のお知らせ（中部電力ミライズ形式）生成ツール — Streamlit Web アプリ
フォント: ＭＳ明朝（msmincho.ttf — 原本と完全一致）
パスワード: Streamlit Cloud Secrets の APP_PASSWORD のみ — ソースコードに記載禁止
"""

import glob as _glob
import hmac
import io
import json as _json
import os
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
    """角丸矩形 塗りつぶし"""
    c.setFillColorRGB(*fill)
    if stroke_col:
        c.setStrokeColorRGB(*stroke_col); c.setLineWidth(sw)
    c.roundRect(x0, _ry(bottom), x1-x0, bottom-top, r,
                fill=1, stroke=1 if stroke_col else 0)

def _rr_outline(c, x0, top, x1, bottom, col, sw=1.08, r=5.4):
    """角丸矩形 外枠のみ"""
    c.setStrokeColorRGB(*col); c.setLineWidth(sw)
    c.roundRect(x0, _ry(bottom), x1-x0, bottom-top, r, fill=0, stroke=1)

def _fill_path(c, x0, top, x1, bottom, fill, r=5.4,
               tl=True, tr=True, bl=True, br=True,
               stroke_col=None, sw=0.18):
    """塗り・選択的な角丸（参考PDFの非対称丸角に対応）。
    原本PDFの 'y' オペレータ（cp1=現在点）と完全一致するベジェ制御点を使用。
    tl/tr/bl/br = True で対応する角を丸める。
    stroke_col 指定時は外枠線も同一パスで描画（sw=線幅）。
    """
    rt = _ry(top)
    rb = _ry(bottom)
    c.setFillColorRGB(*fill)
    if stroke_col:
        c.setStrokeColorRGB(*stroke_col)
        c.setLineWidth(sw)
    p = c.beginPath()
    p.moveTo(x0 + (r if tl else 0), rt)
    if tl:
        p.curveTo(x0 + r, rt, x0, rt, x0, rt - r)
    p.lineTo(x0, rb + (r if bl else 0))
    if bl:
        p.curveTo(x0, rb + r, x0, rb, x0 + r, rb)
    p.lineTo(x1 - (r if br else 0), rb)
    if br:
        p.curveTo(x1 - r, rb, x1, rb, x1, rb + r)
    p.lineTo(x1, rt - (r if tr else 0))
    if tr:
        p.curveTo(x1, rt - r, x1, rt, x1 - r, rt)
    p.close()
    c.drawPath(p, fill=1, stroke=1 if stroke_col else 0)


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
    c.rect(13.1, _ry(51.4), 284.4-13.1, 51.4-31.8, fill=1, stroke=0)

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
    # 年月分ボックス: x=205.6〜289.8 top=78.4〜92.8 (pdfplumber)
    _rr_fill(c, 205.6, 78.4, 289.8, 92.8, _C_BEIGE, r=5.4,
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

    # 水平線
    _hl(c, 11.3,  138.6, 578.0, lw=1.08)
    _hl(c, 11.3,  161.6, 578.0, lw=1.08)

    # 厚い縦区切り (2行目まで)
    for x in [110.5, 129.8, 323.5, 372.2, 406.6]:
        _vl(c, x, 124.9, 161.6, lw=1.08)

    # 細い縦区切り: お客さま番号の桁
    for x in [34.2, 64.8, 80.1, 95.2, 103.0]:
        _vl(c, x, 138.6, 161.6, lw=0.36)

    # 細い縦区切り: 供給地点特定番号の桁
    for x in [423.5, 454.3, 484.6, 514.8, 545.8]:
        _vl(c, x, 138.6, 161.6, lw=0.36)

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
    _tsb(c, 12.1,  B2, d['customer_no'],     6.84, charSpace=0.72)
    _tsb(c, 113.4, B2, d['schedule'],         6.84)
    _tsb(c, 131.0, B2, d['contract_type'],    6.84)
    cap = d.get('contract_capacity', '')
    if cap:
        _tsb(c, 326.2, B2, f'  {cap}Ａ', 6.84)
    pf = d.get('power_factor', '')
    if pf:
        _tsb(c, 375.8, B2, pf, 6.84)
    _tsb(c, 409.5, B2, d['supply_point_id'], 6.84, charSpace=0.72)

    # ── 行 3: 縦区切り + 検針日等 ─────────────────────────
    for x in [72.9, 201.6, 244.6]:
        _vl(c, x, 161.6, 184.6, lw=1.08)

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
    # ── 大パネル外枠（緑 rounded outline）────────────────────
    # 左パネル外枠: x=10.8〜360.4  top=190.8〜690.1 (pdfplumber)
    _rr_outline(c, 10.8, 190.8, 360.4, 690.1, _C_GREEN, sw=1.08, r=5.4)
    # 右パネル外枠: x=363.4〜578.0  top=190.0〜679.1 (pdfplumber)
    _rr_outline(c, 363.4, 190.0, 578.0, 679.1, _C_GREEN, sw=1.08, r=5.4)

    # 左の薄緑角丸ボックス（fill）: 上2角のみ丸, 下は直角（原本に合わせた非対称丸角）
    # 外枠: 原本に合わせ lw=0.18 の極細緑線
    _fill_path(c, 11.34, 191.48, 360.36, 275.54, _C_LT_GREEN, r=5.4,
               tl=True, tr=True, bl=False, br=False,
               stroke_col=_C_GREEN, sw=0.18)
    # 右の薄緑角丸ボックス（fill）: 上2角のみ丸, 下は直角
    _fill_path(c, 363.42, 191.48, 577.98, 236.48, _C_LT_GREEN, r=5.4,
               tl=True, tr=True, bl=False, br=False,
               stroke_col=_C_GREEN, sw=0.18)

    # ご使用量 (bottom=200.6)
    _tsb(c, 14.0,  200.6, 'ご使用量', 6.84)
    _tsb(c, 309.4, 200.6, d['usage_kwh'] + 'ｋＷｈ', 6.84, align='right')

    # ご請求額 (bottom=203.1)
    B_r1 = 203.1
    _tsb(c, 364.0, B_r1, 'ご請求額', 6.84)
    _tsb(c, 563.4, B_r1, _fw_yen(d['billing_amount']), 6.84, align='right')

    # うち消費税等相当額 (bottom=214.6)
    B_r2 = 214.6
    _tsb(c, 364.0, B_r2, 'うち消費税等相当額', 6.84)
    _tsb(c, 563.4, B_r2, _fw_yen(d['tax_amount']), 6.84, align='right')

    # 右パネル仕切り線
    _hl(c, 363.4, 236.5, 578.0, lw=0.72)


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
    # ── 主要水平線 ───────────────────────────────────────
    _hl(c, 11.3,  276.3, 360.4, lw=1.08)
    _hl(c, 10.4,  287.4, 360.0, lw=0.72)
    _hl(c, 10.8,  356.9, 360.0, lw=0.72)
    _hl(c, 11.0,  370.4, 360.0, lw=0.72)
    _hl(c, 10.8,  408.6, 359.3, lw=0.36)
    _hl(c, 10.8,  444.7, 359.3, lw=0.36)
    _hl(c, 10.8,  483.8, 359.8, lw=1.08)
    _hl(c, 10.8,  496.0, 360.0, lw=0.72)
    _hl(c, 10.8,  561.9, 360.0, lw=0.72)
    _hl(c, 10.8,  575.6, 360.0, lw=0.72)
    _hl(c, 10.8,  613.8, 243.9, lw=0.36)
    _hl(c, 10.8,  650.1, 243.9, lw=0.36)

    # ── 主要縦区切り (全体) ──────────────────────────────
    _vl(c, 127.8, 276.3, 690.1, lw=1.08)
    _vl(c, 243.9, 276.3, 690.1, lw=1.08)

    # ── 上部セクション縦区切り (top=276.3→356.9) ──────
    _vl(c,  65.0, 276.3, 356.9, lw=0.36)
    _vl(c, 181.6, 275.7, 357.6, lw=0.36)
    _vl(c, 296.1, 276.3, 356.9, lw=0.36)

    # ── 計器表示縦区切り (top=483.4→562.1) ───────────
    _vl(c,  65.0, 483.4, 562.1, lw=0.36)
    _vl(c, 181.6, 483.4, 562.1, lw=0.36)
    _vl(c, 296.1, 483.4, 562.1, lw=0.36)

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
    # 左ボックス（空欄）: x=11.3〜323.5  top=702.3〜748.2
    _rr_outline(c, 11.3, 702.3, 323.5, 748.2, _C_GREEN, sw=1.08, r=5.4)
    # 右ボックス（翌月案内）: x=363.4〜578.0  top=702.3〜748.2
    _rr_outline(c, 363.4, 702.3, 578.0, 748.2, _C_GREEN, sw=1.08, r=5.4)

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

    # 翌月 燃料費調整単価 (bottom=739.5)
    B5 = 739.5
    _tsb(c, 371.9, B5, '燃料費調整単価（税込）', 6.84)
    _tsb(c, 476.5, B5, d['next_fuel_adj_unit_str'], 6.84)


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
# Streamlit UI
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title=APP_TITLE, layout='centered')
st.title('⚡ ' + APP_TITLE)
st.caption('中部電力ミライズ形式の電気ご使用量のお知らせPDFを生成します')
st.markdown('---')

if not _check_password():
    st.stop()

today = date.today()

# ── ① 基本情報 ─────────────────────────────────────────────
st.subheader('① 基本情報')
col1, col2 = st.columns([1, 1])
with col1:
    name = st.text_input('おなまえ', value='前田　篤志',
                         help='姓と名の間に全角スペースを入れてください')
    customer_no = st.text_input('お客さま番号', value='１１０３９７３０２００５０',
                                help='全角数字で入力')
with col2:
    contract_type = st.selectbox('契約種別',
        ['従量電灯Ｂ', '従量電灯Ｃ', '低圧電力', 'スマートライフプラン', 'その他'],
        index=0)
    contract_capacity = st.text_input('契約容量（Ａ）', value='３０')

col3, col4 = st.columns([1, 1])
with col3:
    meter_no = st.text_input('計器番号', value='０４６')
    schedule = st.text_input('日程', value='０８', help='検針スケジュール番号')
with col4:
    power_factor = st.text_input('力率', value='', help='低圧電力等の場合に記入（任意）')
    supply_point_id = st.text_input('供給地点特定番号',
                                    value='０４０１１０３９７３０２００５０００００００')

st.markdown('---')

# ── ② 日程・期間 ──────────────────────────────────────────
st.subheader('② 日程・期間')
col5, col6 = st.columns([1, 1])
with col5:
    issue_date  = st.date_input('発行日', value=today)
    target_ym   = st.date_input('対象年月（月初日で指定）',
                                value=date(today.year, today.month, 1))
with col6:
    meter_read_date = st.date_input('検針日（当月）', value=today)
    usage_start = st.date_input('ご使用期間 開始', value=today - timedelta(days=32))
    usage_end   = st.date_input('ご使用期間 終了', value=today - timedelta(days=1))

usage_days_calc = (usage_end - usage_start).days + 1 if usage_end >= usage_start else 0
st.caption(f'📅 ご使用日数（自動計算）: **{usage_days_calc}日**')
usage_days_override = st.number_input('ご使用日数（手動修正する場合のみ）',
    min_value=0, max_value=99, value=0, step=1,
    help='0のままにすると自動計算値を使用')
usage_days = int(usage_days_override) if usage_days_override > 0 else usage_days_calc

def _fw_date(d_: date) -> str:
    tr = str.maketrans('0123456789', '０１２３４５６７８９')
    return str(d_.month).translate(tr) + '月' + str(d_.day).translate(tr) + '日'

usage_period_str = f'{_fw_date(usage_start)}〜{_fw_date(usage_end)}'
issue_date_str   = str(issue_date.year).translate(str.maketrans('0123456789','０１２３４５６７８９')) \
                   + '年' + _fw_date(issue_date)

st.markdown('---')

# ── ③ 翌月ご案内 ─────────────────────────────────────────
st.subheader('③ 翌月ご案内')
col7, col8 = st.columns([1, 1])
with col7:
    next_meter_read_date = st.date_input('翌月 検針日',
                                         value=meter_read_date + timedelta(days=28))
    next_usage_start = st.date_input('翌月 使用期間 開始',
                                     value=usage_end + timedelta(days=1))
with col8:
    next_usage_end   = st.date_input('翌月 使用期間 終了',
                                     value=usage_end + timedelta(days=28))
    next_month_label = st.text_input('翌月ご案内の月（全角数字）',
                                     value=str(target_ym.month % 12 + 1).translate(
                                         str.maketrans('0123456789','０１２３４５６７８９')))

next_usage_period_str = f'{_fw_date(next_usage_start)}〜{_fw_date(next_usage_end)}'
st.markdown('---')

# ── ④ 使用量・計器指示数 ─────────────────────────────────
st.subheader('④ 使用量・計器指示数')
col9, col10 = st.columns([1, 1])
with col9:
    usage_kwh       = st.number_input('ご使用量（ｋＷｈ）', min_value=0, value=92, step=1)
    current_reading = st.number_input('当月指示数', min_value=0.0, value=19398.6,
                                      step=0.1, format='%.1f')
with col10:
    prev_reading_auto = round(current_reading - usage_kwh, 1)
    st.caption(f'📟 前月指示数（自動計算）: **{prev_reading_auto}**')
    prev_reading = st.number_input('前月指示数（手動修正する場合のみ）',
                                   min_value=0.0, value=0.0, step=0.1, format='%.1f',
                                   help='0.0のままにすると自動計算値を使用')
    prev_reading_final = prev_reading if prev_reading > 0 else prev_reading_auto
    diff_reading = round(current_reading - prev_reading_final, 1)

st.markdown('---')

# ── ⑤ 請求金額 ───────────────────────────────────────────
st.subheader('⑤ 請求金額')
col11, col12 = st.columns([1, 1])
with col11:
    billing_amount = st.number_input('ご請求額（円）',          min_value=0, value=3413, step=1)
    tax_amount     = st.number_input('うち消費税等相当額（円）', min_value=0, value=310,  step=1)
with col12:
    basic_yen = st.number_input('基本料金（円）', min_value=0, value=963,  step=1)
    basic_sen = st.number_input('基本料金（銭）', min_value=0, max_value=99, value=42, step=1)

col13, col14 = st.columns([1, 1])
with col13:
    energy1_yen = st.number_input('電力量料金 1段（円）', min_value=0, value=2066, step=1)
    energy1_sen = st.number_input('電力量料金 1段（銭）', min_value=0, max_value=99, value=32, step=1)
with col14:
    fuel_adj_yen = st.number_input('うち燃料費調整額（円）', min_value=0, value=115, step=1)
    fuel_adj_sen = st.number_input('うち燃料費調整額（銭）', min_value=0, max_value=99, value=92, step=1)

col15, _ = st.columns([1, 1])
with col15:
    renewable_yen = st.number_input('再エネ発電促進賦課金（円）', min_value=0, value=384, step=1)

st.markdown('---')

# ── ⑥ 単価情報 ──────────────────────────────────────────
st.subheader('⑥ 単価情報')
col17, col18 = st.columns([1, 1])
with col17:
    fuel_adj_unit_yen = st.number_input('当月 燃料費調整単価（円）', min_value=0, value=1, step=1)
    fuel_adj_unit_sen = st.number_input('当月 燃料費調整単価（銭）', min_value=0, max_value=99, value=26, step=1)
    renewable_unit_yen = st.number_input('再エネ単価（円）', min_value=0, value=4, step=1)
    renewable_unit_sen = st.number_input('再エネ単価（銭）', min_value=0, max_value=99, value=18, step=1)
with col18:
    next_fuel_adj_yen = st.number_input('翌月 燃料費調整単価（円）', min_value=0, value=1, step=1)
    next_fuel_adj_sen = st.number_input('翌月 燃料費調整単価（銭）', min_value=0, max_value=99, value=35, step=1)

st.markdown('---')

# ── ⑦ ご使用場所 ─────────────────────────────────────────
st.subheader('⑦ ご使用場所')

# address1 の初期値（未設定時のみ）
if '_meisai_addr1' not in st.session_state:
    st.session_state['_meisai_addr1'] = '愛知県　名古屋市　熱田区　一番　３丁目　２−３０'

postal_raw = st.text_input(
    '郵便番号',
    placeholder='例: 460-0008 または ４６０－０００８',
    help='7桁入力すると住所①を自動補完します。半角・全角どちらでも可。',
)
# 半角数字のみ抽出して7桁チェック
_zip_half = postal_raw.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
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
    placeholder='例: 愛知県　名古屋市　熱田区　一番　３丁目　２−３０',
    help='郵便番号を入力すると都道府県・市区町村・町名が自動補完されます。番地は手動で追記してください。',
)
address2 = st.text_input('住所②（建物名・部屋番号、任意）',
    value='市営　一番荘　３棟　２０５')

st.markdown('---')

# ── ⑧ 生成 ───────────────────────────────────────────────
_fw_tr = str.maketrans('0123456789', '０１２３４５６７８９')

# 翌月単価: "１円３５銭／ｋＷｈ" (スペースなし)
next_fuel_adj_unit_str = (str(next_fuel_adj_yen).translate(_fw_tr) + '円'
                          + f'{next_fuel_adj_sen:02d}'.translate(_fw_tr) + '銭／ｋＷｈ')

data = dict(
    name              = name.strip(),
    customer_no       = customer_no.strip(),
    schedule          = schedule.strip(),
    contract_type     = contract_type,
    contract_capacity = contract_capacity.strip(),
    power_factor      = power_factor.strip(),
    meter_no          = meter_no.strip(),
    supply_point_id   = supply_point_id.strip(),

    issue_date_str    = issue_date_str,
    target_year       = str(target_ym.year).translate(_fw_tr),
    target_month      = str(target_ym.month).translate(_fw_tr),
    meter_read_date   = _fw_date(meter_read_date),

    usage_period      = usage_period_str,
    usage_days        = str(usage_days).translate(_fw_tr),
    usage_kwh         = str(usage_kwh).translate(_fw_tr),

    current_reading   = f'{current_reading:.1f}',
    prev_reading      = f'{prev_reading_final:.1f}',
    diff_reading      = f'{diff_reading:.1f}',

    billing_amount    = billing_amount,
    tax_amount        = tax_amount,

    basic_yen         = basic_yen,
    basic_sen         = basic_sen,
    energy1_yen       = energy1_yen,
    energy1_sen       = energy1_sen,
    fuel_adj_yen      = fuel_adj_yen,
    fuel_adj_sen      = fuel_adj_sen,
    renewable_yen     = renewable_yen,

    fuel_adj_unit_yen = fuel_adj_unit_yen,
    fuel_adj_unit_sen = fuel_adj_unit_sen,
    renewable_unit_yen= renewable_unit_yen,
    renewable_unit_sen= renewable_unit_sen,

    next_month_label        = next_month_label.strip(),
    next_meter_read_date    = _fw_date(next_meter_read_date),
    next_usage_period       = next_usage_period_str,
    next_fuel_adj_unit_str  = next_fuel_adj_unit_str,

    address1 = address1.strip(),
    address2 = address2.strip(),
)

if st.button('⚡　電気ご使用量のお知らせ PDF を生成する',
             use_container_width=True, type='primary'):
    with st.spinner('PDF を生成中…'):
        pdf_bytes = generate_pdf(data)

    fname = f'Webmeisai{target_ym.year}{target_ym.month:02d}.pdf'
    st.download_button(
        label='📄　PDF をダウンロード',
        data=pdf_bytes,
        file_name=fname,
        mime='application/pdf',
        use_container_width=True,
    )
    yr_fw = str(target_ym.year).translate(_fw_tr)
    mo_fw = str(target_ym.month).translate(_fw_tr)
    st.success(f'✅ {yr_fw}年{mo_fw}月分の明細書を生成しました。')

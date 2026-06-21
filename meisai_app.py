"""
電気ご使用量のお知らせ（中部電力ミライズ形式）生成ツール — Streamlit Web アプリ
フォント: IPAexGothic（または IPAexMincho にフォールバック）
"""

import glob as _glob
import hmac
import io
import os
import re as _re
import secrets as _secrets
import streamlit as st
from datetime import date, timedelta
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── ページサイズ ───────────────────────────────────────────────────
PAGE_W, PAGE_H = 595, 842   # A4

# ── カラーパレット (R,G,B / 0.0–1.0) ──────────────────────────────
_C_GREEN     = (0.17, 0.49, 0.27)   # 濃い緑: 枠線・ラベル
_C_LT_GREEN  = (0.93, 0.97, 0.90)   # 薄い緑: コンテンツ背景
_C_BEIGE     = (0.96, 0.90, 0.74)   # ベージュ: ヘッダーセル
_C_ORANGE    = (0.97, 0.76, 0.52)   # オレンジ: お名前ボックス
_C_TOP_BAR   = (0.97, 0.91, 0.76)   # 上部バー色
_C_BLACK     = (0.0, 0.0, 0.0)
_C_WHITE     = (1.0, 1.0, 1.0)

APP_TITLE = "電気ご使用量のお知らせ（中部電力ミライズ形式）"

# ── フォント ───────────────────────────────────────────────────────
def _find_font_jp() -> str:
    for pat in [
        '/usr/share/fonts/**/*ipaexg*.ttf',
        '/usr/share/fonts/**/*IPAexGothic*.ttf',
        '/usr/share/fonts/**/*ipaexm*.ttf',
        '/usr/share/fonts/**/*IPAexMincho*.ttf',
    ]:
        hits = sorted(_glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    return os.path.join(os.path.dirname(__file__), "IBMPlexSansJP-Regular.ttf")

_FONT_PATH = _find_font_jp()
_FONT_REG = False

def _ensure_font():
    global _FONT_REG
    if not _FONT_REG:
        pdfmetrics.registerFont(TTFont('FJ', _FONT_PATH))
        _FONT_REG = True

FJ = 'FJ'

# ── 描画ヘルパー ───────────────────────────────────────────────────
def _fill_rect(c, x, y, w, h, fc, sc=None, lw=0.5):
    c.setFillColorRGB(*fc)
    if sc:
        c.setStrokeColorRGB(*sc)
        c.setLineWidth(lw)
        c.rect(x, y, w, h, fill=1, stroke=1)
    else:
        c.rect(x, y, w, h, fill=1, stroke=0)

def _border_rect(c, x, y, w, h, sc, lw=0.7):
    c.setStrokeColorRGB(*sc)
    c.setLineWidth(lw)
    c.rect(x, y, w, h, fill=0, stroke=1)

def _txt(c, x, y, s, sz=8, col=None, align='left'):
    if col is None:
        col = _C_BLACK
    c.setFont(FJ, sz)
    c.setFillColorRGB(*col)
    s = str(s)
    if align == 'right':
        c.drawRightString(x, y, s)
    elif align == 'center':
        c.drawCentredString(x, y, s)
    else:
        c.drawString(x, y, s)

def _hline(c, x1, y, x2, col=None, lw=0.4):
    if col is None:
        col = _C_GREEN
    c.setStrokeColorRGB(*col)
    c.setLineWidth(lw)
    c.line(x1, y, x2, y)

def _vline(c, x, y1, y2, col=None, lw=0.4):
    if col is None:
        col = _C_GREEN
    c.setStrokeColorRGB(*col)
    c.setLineWidth(lw)
    c.line(x, y1, x, y2)


# ══════════════════════════════════════════════════════════════════
# PDF 生成メイン
# ══════════════════════════════════════════════════════════════════
def generate_pdf(d: dict) -> bytes:
    _ensure_font()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    _draw(c, d)
    c.save()
    return buf.getvalue()


def _draw(c, d):
    # ── ① 上部カラーバー (y=820~842) ───────────────────────────
    _fill_rect(c, 0, 820, PAGE_W, 22, _C_TOP_BAR)
    _txt(c, 20, 826, 'おなまえ', 7, _C_GREEN)
    _txt(c, 578, 826, '中部電力ミライズ株式会社', 9.5, _C_GREEN, 'right')

    # ── ② お名前ボックス (y=806~820) ──────────────────────────
    _fill_rect(c, 155, 807, 285, 13, _C_ORANGE)
    _txt(c, 297, 810, f'{d["name"]}　様', 9, _C_BLACK, 'center')

    # ── ③ ヘッダーテーブル (y=748~806) ────────────────────────
    # 外枠
    _fill_rect(c, 15, 748, 565, 58, _C_WHITE, _C_GREEN, 0.8)

    # 上段ラベル行 (y=789~806, h=17)
    _fill_rect(c, 15, 789, 565, 17, _C_BEIGE)
    _hline(c, 15, 789, 580, _C_GREEN, 0.5)
    _hline(c, 15, 771, 580, _C_GREEN, 0.5)
    _hline(c, 15, 748, 580, _C_GREEN, 0.5)

    # ヘッダー縦区切り
    for x in [225, 310, 398, 468, 530]:
        _vline(c, x, 748, 806, _C_GREEN, 0.4)

    _txt(c, 120, 793, 'お客さま番号', 7, _C_GREEN, 'center')
    _txt(c, 267, 793, '日程', 7, _C_GREEN, 'center')
    _txt(c, 353, 793, '契約種別', 7, _C_GREEN, 'center')
    _txt(c, 433, 793, '契約容量', 7, _C_GREEN, 'center')
    _txt(c, 499, 793, '力率', 7, _C_GREEN, 'center')

    # データ行 (y=771~789)
    _txt(c, 120, 775, d.get('customer_no', ''), 8, _C_BLACK, 'center')
    _txt(c, 267, 775, d.get('schedule', ''), 7, _C_BLACK, 'center')
    _txt(c, 353, 775, d.get('contract_type', '従量電灯Ｂ'), 7, _C_BLACK, 'center')
    cap = d.get('contract_capacity', '')
    _txt(c, 433, 775, f'{cap}Ａ' if cap else '', 7, _C_BLACK, 'center')
    _txt(c, 499, 775, d.get('power_factor', ''), 7, _C_BLACK, 'center')

    # 下段（記事・検針日）(y=748~771)
    _fill_rect(c, 15, 748, 210, 23, _C_BEIGE)
    _fill_rect(c, 310, 748, 88, 23, _C_BEIGE)
    _txt(c, 120, 755, '記事', 7, _C_GREEN, 'center')
    _txt(c, 354, 755, '検針日', 7, _C_GREEN, 'center')
    _txt(c, 402, 755, d.get('meter_read_date', ''), 8, _C_BLACK)
    _vline(c, 310, 748, 771, _C_GREEN, 0.4)

    # ── ④ メインコンテンツボックス (y=90~748) ─────────────────
    _border_rect(c, 15, 90, 565, 658, _C_GREEN, 0.8)
    _vline(c, 362, 90, 748, _C_GREEN, 0.5)  # 左右分割

    # ── ⑤ 左パネル ─────────────────────────────────────────────
    _draw_left(c, d)

    # ── ⑥ 右パネル ─────────────────────────────────────────────
    _draw_right(c, d)

    # ── ⑦ 下部 ─────────────────────────────────────────────────
    _draw_bottom(c, d)


def _draw_left(c, d):
    """左パネル (x=15~362, y=90~748)"""
    LX, RX = 15, 362

    # タイトルエリア (y=718~748, h=30)
    _fill_rect(c, LX, 718, RX - LX, 30, _C_LT_GREEN)
    _hline(c, LX, 718, RX, _C_GREEN, 0.5)
    _txt(c, (LX+RX)//2, 730, '電気ご使用量のお知らせ', 11, _C_GREEN, 'center')
    _txt(c, (LX+RX)//2, 721, d.get('issue_date_str', ''), 7.5, _C_BLACK, 'center')

    # 対象期間テキスト (y=695~718, h=23)
    _fill_rect(c, LX, 695, RX - LX, 23, _C_LT_GREEN)
    _hline(c, LX, 695, RX, _C_GREEN, 0.5)
    yr = d.get('target_year', '')
    mo = d.get('target_month', '')
    _txt(c, LX+5, 709, f'{yr}年{mo}月分 の電気ご使用量を下記のとおりお知らせいたします。', 7, _C_BLACK)

    # ご使用情報 (y=655~695, h=40)
    _hline(c, LX, 655, RX, _C_GREEN, 0.5)
    _txt(c, LX+8, 682, 'ご使用期間', 7, _C_GREEN)
    _txt(c, LX+80, 682, d.get('usage_period', ''), 8)
    _txt(c, LX+8, 668, 'ご使用日数', 7, _C_GREEN)
    _txt(c, LX+80, 668, f'{d.get("usage_days", "")}日', 8)
    _txt(c, LX+185, 668, 'ご使用量', 7, _C_GREEN)
    _txt(c, LX+248, 668, f'{d.get("usage_kwh", "")}ｋＷｈ', 9)
    _txt(c, LX+8, 657, f'[ご使用場所]　{d.get("address1","")}　{d.get("address2","")}', 7, _C_GREEN)

    # 計器テーブル (y=543~655)
    _hline(c, LX, 543, RX, _C_GREEN, 0.5)
    _fill_rect(c, LX, 633, RX - LX, 22, _C_BEIGE)
    _hline(c, LX, 633, RX, _C_GREEN, 0.4)
    _hline(c, LX, 611, RX, _C_GREEN, 0.4)

    _txt(c, LX+8, 637, f'計器番号　{d.get("meter_no","")}', 7, _C_GREEN)
    # 第1計器
    _fill_rect(c, LX, 543, 30, 90, _C_BEIGE)
    _vline(c, LX+30, 543, 633, _C_GREEN, 0.3)
    _txt(c, LX+15, 590, '第', 7, _C_GREEN, 'center')
    _txt(c, LX+15, 580, '１', 7, _C_GREEN, 'center')
    _txt(c, LX+15, 570, '計', 7, _C_GREEN, 'center')
    _txt(c, LX+15, 560, '器', 7, _C_GREEN, 'center')

    # 列ヘッダー
    col_xs = [LX+30, LX+130, LX+225, RX]
    mid_xs = [LX+80, LX+177, LX+270]
    for mx in mid_xs:
        _vline(c, mx + 28, 543, 633, _C_GREEN, 0.3)
    _txt(c, LX+113, 637, '当月指示数', 7, _C_GREEN, 'center')
    _txt(c, LX+207, 637, '前月指示数', 7, _C_GREEN, 'center')
    _txt(c, LX+303, 637, '差引', 7, _C_GREEN, 'center')

    # 指示数の縦区切り
    _vline(c, LX+158, 543, 611, _C_GREEN, 0.3)
    _vline(c, LX+248, 543, 611, _C_GREEN, 0.3)

    # 計器データ値
    _txt(c, LX+113, 580, str(d.get('current_reading', '')), 9, _C_BLACK, 'center')
    _txt(c, LX+203, 580, str(d.get('prev_reading', '')), 9, _C_BLACK, 'center')
    _txt(c, LX+295, 580, str(d.get('diff_reading', '')), 9, _C_BLACK, 'center')

    # 燃料費調整単価・再エネ単価 (y=490~543)
    _hline(c, LX, 490, RX, _C_GREEN, 0.4)
    _txt(c, LX+8, 530, '当月燃料費調整単価（税込）', 7, _C_GREEN)
    _txt(c, LX+185, 530, d.get('fuel_adj_unit_str', ''), 8)
    _txt(c, LX+8, 515, '再エネ発電促進賦課金単価（税込）', 7, _C_GREEN)
    _txt(c, LX+210, 515, d.get('renewable_unit_str', ''), 8)

    # ── ご請求額内訳 (y=130~490) ──────────────────────────────
    _hline(c, LX, 460, RX, _C_GREEN, 0.5)
    _fill_rect(c, LX, 460, RX - LX, 18, _C_BEIGE)
    _hline(c, LX, 460, RX, _C_GREEN, 0.5)
    _txt(c, (LX+RX)//2, 465, '［ご請求額内訳］', 8, _C_GREEN, 'center')

    # 各行
    rows = [
        (440, '基本料金', 'basic_yen', 'basic_sen'),
        (416, '電力量料金　１段料金', 'energy1_yen', 'energy1_sen'),
        (392, '再エネ発電促進賦課金', 'renewable_yen', None),
    ]
    for (ry, label, yen_key, sen_key) in rows:
        _hline(c, LX, ry, RX, _C_GREEN, 0.3)
        _txt(c, LX+10, ry + 6, label, 8)
        yen = d.get(yen_key, 0)
        if sen_key:
            sen = d.get(sen_key, 0)
            _txt(c, RX - 8, ry + 6, f'{yen:,}円　{sen:02d}銭', 8, _C_BLACK, 'right')
        else:
            _txt(c, RX - 8, ry + 6, f'{yen:,}円', 8, _C_BLACK, 'right')

    # うち燃料費調整額（小さい文字・インデント）
    _hline(c, LX, 370, RX, _C_GREEN, 0.3)
    _txt(c, LX+18, 376, 'うち燃料費調整額', 7)
    fy = d.get('fuel_adj_yen', 0)
    fs = d.get('fuel_adj_sen', 0)
    _txt(c, RX - 8, 376, f'{fy:,}円{fs:02d}銭', 7, _C_BLACK, 'right')

    _hline(c, LX, 346, RX, _C_GREEN, 0.5)


def _draw_right(c, d):
    """右パネル (x=362~580, y=90~748)"""
    LX, RX = 362, 580
    CX = (LX + RX) // 2  # = 471

    # 請求額エリア (y=640~748, h=108)
    _fill_rect(c, LX, 640, RX - LX, 108, _C_LT_GREEN)
    _hline(c, LX, 640, RX, _C_GREEN, 0.5)

    # ご請求額 ラベル・金額
    _txt(c, CX, 730, 'ご請求額', 9, _C_GREEN, 'center')
    billing = d.get('billing_amount', 0)
    _txt(c, CX, 704, f'{billing:,}円', 16, _C_BLACK, 'center')
    tax = d.get('tax_amount', 0)
    _txt(c, CX, 688, f'うち消費税等相当額　{tax:,}円', 7.5, _C_BLACK, 'center')
    _txt(c, CX, 676, f'うち燃料費調整額　{d.get("fuel_adj_total_str","")}', 7, _C_BLACK, 'center')

    # 翌月ご案内ヘッダー (y=618~640)
    _fill_rect(c, LX, 618, RX - LX, 22, _C_LT_GREEN)
    _hline(c, LX, 618, RX, _C_GREEN, 0.5)
    nm = d.get('next_month_label', '')
    _txt(c, LX + 6, 626, f'翌月（{nm}月分）のご案内', 8, _C_GREEN)

    # 翌月情報 (y=540~618)
    _hline(c, LX, 540, RX, _C_GREEN, 0.4)
    _txt(c, LX+6, 603, '検針日', 7, _C_GREEN)
    _txt(c, LX+50, 603, d.get('next_meter_read_date', ''), 8)

    _txt(c, LX+6, 588, 'ご使用期間', 7, _C_GREEN)
    _txt(c, LX+65, 588, d.get('next_usage_period', ''), 8)

    _txt(c, LX+6, 570, '燃料費調整単価（税込）', 7, _C_GREEN)
    _txt(c, LX+6, 558, d.get('next_fuel_adj_unit_str', ''), 8)


def _draw_bottom(c, d):
    """下部エリア（ご使用場所・供給地点特定番号）"""
    # ご使用場所ボックス
    _border_rect(c, 15, 48, 330, 42, _C_GREEN, 0.6)
    _txt(c, 20, 78, '[ご使用場所]', 7, _C_GREEN)
    _txt(c, 20, 65, d.get('address1', ''), 8)
    _txt(c, 20, 52, d.get('address2', ''), 8)

    # 供給地点特定番号ボックス
    _border_rect(c, 350, 48, 230, 42, _C_GREEN, 0.6)
    _txt(c, 355, 78, '供給地点特定番号', 7, _C_GREEN)
    _txt(c, 355, 62, d.get('supply_point_id', ''), 7.5)

    # メインボックス外枠との区切り線
    _hline(c, 15, 90, 580, _C_GREEN, 0.8)


# ══════════════════════════════════════════════════════════════════
# 認証
# ══════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════════
st.set_page_config(page_title=APP_TITLE, layout='centered')
st.title('⚡ ' + APP_TITLE)
st.caption('中部電力ミライズ形式の電気ご使用量のお知らせPDFを生成します')
st.markdown('---')

if not _check_password():
    st.stop()

today = date.today()

# ── ① 基本情報 ─────────────────────────────────────────────────
st.subheader('① 基本情報')
col1, col2 = st.columns([1, 1])
with col1:
    name = st.text_input('おなまえ', value='前田　篤志',
                         help='姓と名の間に全角スペースを入れてください')
    customer_no = st.text_input('お客さま番号', value='１１０３９７３０２００５０',
                                help='全角数字で入力（スペース区切り可）')
with col2:
    contract_type = st.selectbox('契約種別',
        ['従量電灯Ｂ', '従量電灯Ｃ', '低圧電力', 'スマートライフプラン', 'その他'],
        index=0)
    contract_capacity = st.text_input('契約容量（Ａ）', value='３０')

col3, col4 = st.columns([1, 1])
with col3:
    meter_no = st.text_input('計器番号', value='０４６')
    schedule = st.text_input('日程', value='０８',
                             help='検針スケジュール番号（任意）')
with col4:
    power_factor = st.text_input('力率', value='',
                                 help='低圧電力等の場合に記入（任意）')
    supply_point_id = st.text_input('供給地点特定番号',
                                    value='０４０１１０３９７３０２００５０００００００')

st.markdown('---')

# ── ② 日程・期間 ───────────────────────────────────────────────
st.subheader('② 日程・期間')
col5, col6 = st.columns([1, 1])
with col5:
    issue_date = st.date_input('発行日', value=today)
    target_ym = st.date_input('対象年月（月初日で指定）',
                              value=date(today.year, today.month, 1))
with col6:
    meter_read_date = st.date_input('検針日（当月）', value=today)
    usage_start = st.date_input('ご使用期間 開始', value=today - timedelta(days=32))
    usage_end   = st.date_input('ご使用期間 終了', value=today - timedelta(days=1))

# 使用日数を自動計算
usage_days_calc = (usage_end - usage_start).days + 1 if usage_end >= usage_start else 0
st.caption(f'📅 ご使用日数（自動計算）: **{usage_days_calc}日**　（修正する場合は下で入力）')
usage_days_override = st.number_input('ご使用日数（手動修正する場合のみ）',
    min_value=0, max_value=99, value=0, step=1,
    help='0のままにすると上の自動計算値を使用します')
usage_days = int(usage_days_override) if usage_days_override > 0 else usage_days_calc

# 表示用文字列
def _fw_date(d_: date) -> str:
    """date → 全角表示（例: ４月９日）"""
    fw = str.maketrans('0123456789', '０１２３４５６７８９')
    return str(d_.month).translate(fw) + '月' + str(d_.day).translate(fw) + '日'

usage_period_str = f'{_fw_date(usage_start)}～{_fw_date(usage_end)}'
issue_date_str   = f'{issue_date.year}年{_fw_date(issue_date)}'

# 翌月ご案内
st.markdown('---')
st.subheader('③ 翌月ご案内')
col7, col8 = st.columns([1, 1])
with col7:
    next_meter_read_date = st.date_input('翌月 検針日', value=meter_read_date + timedelta(days=28))
    next_usage_start = st.date_input('翌月 使用期間 開始', value=usage_end + timedelta(days=1))
with col8:
    next_usage_end = st.date_input('翌月 使用期間 終了', value=usage_end + timedelta(days=28))
    next_month_label = st.text_input('翌月ご案内の月（数字）',
                                     value=str(target_ym.month % 12 + 1))

next_usage_period_str = f'{_fw_date(next_usage_start)}～{_fw_date(next_usage_end)}'

st.markdown('---')

# ── ④ 使用量・計器指示数 ─────────────────────────────────────
st.subheader('④ 使用量・計器指示数')
col9, col10 = st.columns([1, 1])
with col9:
    usage_kwh = st.number_input('ご使用量（ｋＷｈ）', min_value=0, value=92, step=1)
    current_reading = st.number_input('当月指示数', min_value=0.0, value=19398.6, step=0.1, format='%.1f')
with col10:
    prev_reading_auto = round(current_reading - usage_kwh, 1)
    st.caption(f'📟 前月指示数（自動計算）: **{prev_reading_auto}**')
    prev_reading = st.number_input('前月指示数（手動修正する場合のみ）',
                                    min_value=0.0, value=0.0, step=0.1, format='%.1f',
                                    help='0.0のままにすると自動計算値を使用します')
    prev_reading_final = prev_reading if prev_reading > 0 else prev_reading_auto
    diff_reading = round(current_reading - prev_reading_final, 1)

st.markdown('---')

# ── ⑤ 請求金額 ────────────────────────────────────────────────
st.subheader('⑤ 請求金額')
col11, col12 = st.columns([1, 1])
with col11:
    billing_amount = st.number_input('ご請求額（円）', min_value=0, value=3413, step=1)
    tax_amount     = st.number_input('うち消費税等相当額（円）', min_value=0, value=310, step=1)
with col12:
    basic_yen = st.number_input('基本料金（円）', min_value=0, value=963, step=1)
    basic_sen = st.number_input('基本料金（銭）', min_value=0, max_value=99, value=42, step=1)

col13, col14 = st.columns([1, 1])
with col13:
    energy1_yen = st.number_input('電力量料金 1段（円）', min_value=0, value=2066, step=1)
    energy1_sen = st.number_input('電力量料金 1段（銭）', min_value=0, max_value=99, value=32, step=1)
with col14:
    fuel_adj_yen = st.number_input('うち燃料費調整額（円）', min_value=0, value=115, step=1)
    fuel_adj_sen = st.number_input('うち燃料費調整額（銭）', min_value=0, max_value=99, value=92, step=1)

col15, col16 = st.columns([1, 1])
with col15:
    renewable_yen = st.number_input('再エネ発電促進賦課金（円）', min_value=0, value=384, step=1)
with col16:
    pass  # 将来拡張用

st.markdown('---')

# ── ⑥ 単価情報 ───────────────────────────────────────────────
st.subheader('⑥ 単価情報')
col17, col18 = st.columns([1, 1])
with col17:
    fuel_adj_unit_yen = st.number_input('当月 燃料費調整単価（円）', min_value=0, value=1, step=1)
    fuel_adj_unit_sen = st.number_input('当月 燃料費調整単価（銭）', min_value=0, max_value=99, value=26, step=1)
    renewable_unit_yen = st.number_input('再エネ発電促進賦課金単価（円）', min_value=0, value=4, step=1)
    renewable_unit_sen = st.number_input('再エネ発電促進賦課金単価（銭）', min_value=0, max_value=99, value=18, step=1)
with col18:
    next_fuel_adj_yen = st.number_input('翌月 燃料費調整単価（円）', min_value=0, value=1, step=1)
    next_fuel_adj_sen = st.number_input('翌月 燃料費調整単価（銭）', min_value=0, max_value=99, value=35, step=1)

st.markdown('---')

# ── ⑦ ご使用場所 ──────────────────────────────────────────────
st.subheader('⑦ ご使用場所')
address1 = st.text_input('住所（都道府県～番地）', value='愛知県　名古屋市　熱田区　一番　３丁目　２－３０',
                         help='区切りに全角スペースを入れてください')
address2 = st.text_input('建物名・部屋番号（任意）', value='市営　一番荘　３棟　２０５')

st.markdown('---')

# ── ⑧ 生成 ───────────────────────────────────────────────────
def _fw(n: int, sen: int) -> str:
    """例: (1, 26) → '１円　２６銭'"""
    fw = str.maketrans('0123456789', '０１２３４５６７８９')
    return str(n).translate(fw) + '円　' + f'{sen:02d}'.translate(fw) + '銭'

def _fw_unit(n: int, sen: int) -> str:
    fw = str.maketrans('0123456789', '０１２３４５６７８９')
    return str(n).translate(fw) + '円　' + f'{sen:02d}'.translate(fw) + '銭'

# 表示用文字列の準備
fw = str.maketrans('0123456789', '０１２３４５６７８９')

fuel_adj_total_str = f'{fuel_adj_yen:,}円{fuel_adj_sen:02d}銭'.translate(
    str.maketrans('0123456789,', '０１２３４５６７８９，'))

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
    target_year       = str(target_ym.year).translate(fw),
    target_month      = str(target_ym.month).translate(fw),
    meter_read_date   = _fw_date(meter_read_date),

    usage_period      = usage_period_str,
    usage_days        = str(usage_days).translate(fw),
    usage_kwh         = str(usage_kwh).translate(fw),

    current_reading   = f'{current_reading:.1f}',
    prev_reading      = f'{prev_reading_final:.1f}',
    diff_reading      = f'{diff_reading:.1f}',

    billing_amount    = billing_amount,
    tax_amount        = tax_amount,
    fuel_adj_total_str= fuel_adj_total_str,

    basic_yen         = basic_yen,
    basic_sen         = basic_sen,
    energy1_yen       = energy1_yen,
    energy1_sen       = energy1_sen,
    fuel_adj_yen      = fuel_adj_yen,
    fuel_adj_sen      = fuel_adj_sen,
    renewable_yen     = renewable_yen,

    fuel_adj_unit_str = _fw(fuel_adj_unit_yen, fuel_adj_unit_sen),
    renewable_unit_str= _fw(renewable_unit_yen, renewable_unit_sen),

    next_month_label        = next_month_label.strip(),
    next_meter_read_date    = _fw_date(next_meter_read_date),
    next_usage_period       = next_usage_period_str,
    next_fuel_adj_unit_str  = _fw(next_fuel_adj_yen, next_fuel_adj_sen),

    address1          = address1.strip(),
    address2          = address2.strip(),
)

if st.button('⚡　電気ご使用量のお知らせ PDF を生成する',
             use_container_width=True, type='primary'):
    with st.spinner('PDF を生成中…'):
        pdf_bytes = generate_pdf(data)

    yr_fw = str(target_ym.year).translate(fw)
    mo_fw = str(target_ym.month).translate(fw)
    fname = f'Webmeisai{target_ym.year}{target_ym.month:02d}.pdf'
    st.download_button(
        label='📄　PDF をダウンロード',
        data=pdf_bytes,
        file_name=fname,
        mime='application/pdf',
        use_container_width=True,
    )
    st.success(f'✅ {yr_fw}年{mo_fw}月分の明細書を生成しました。')

"""
æ®‹é«˜è¨¼æ˜æ›¸ï¼ˆä¸‰è±UFJéŠ€è¡Œå½¢å¼ï¼‰ç”Ÿæˆãƒ„ãƒ¼ãƒ« â€” Streamlit Web ã‚¢ãƒ—ãƒª
åº§æ¨™ã¯ã‚µãƒ³ãƒ—ãƒ«PDFã‹ã‚‰pdfminerã§å®Ÿæ¸¬ã—ãŸå€¤ã‚’ä½¿ç”¨
ãƒ•ã‚©ãƒ³ãƒˆ: å…¨ãƒ†ã‚­ã‚¹ãƒˆ â†’ IPAexMinchoï¼ˆåŸæœ¬é€šã‚Šï¼‰
ç·šå¹…: å…¨ç·š 0.25ptï¼ˆåŸæœ¬é€šã‚Šï¼‰
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

PAGE_W, PAGE_H = A4   # 595.28 Ã— 841.89 pt


def _find_font_jp() -> str:
    """IPAexMincho ãƒ•ã‚©ãƒ³ãƒˆãƒ‘ã‚¹ã‚’å‹•çš„ã«æ¢ã™ï¼ˆStreamlit Cloud: fonts-ipaexfontï¼‰"""
    for pattern in [
        '/usr/share/fonts/**/*ipaexm*.ttf',
        '/usr/share/fonts/**/*ipaexm*.otf',
        '/usr/share/fonts/**/*IPAexMincho*.ttf',
    ]:
        hits = sorted(_glo[.glob(pattern, recursive=True))
        if hits:
            return hits[0]
    # ãƒ•ã‚©ãƒ¼ãƒ«ãƒãƒƒã‚¯: IBMPlexSansJPï¼ˆãƒ­ãƒ¼ã‚«ãƒ«é–‹ç™ºç”¨ï¼‰
    return os.path.join(os.path.dirname(__file__), "IBMPlexSansJP-Regular.ttf")


_FONT_JP_PATH = _find_font_jp()
_FONT_REGISTERED = False

# åŸæœ¬PDFã‹ã‚‰ã‚¯ãƒ­ãƒƒãƒ—ã—ãŸéŠ€è¡Œåï¼‹å°å½±ç”»åƒï¼ˆBase64åŸ‹ã‚è¾¼ã¿ï¼‰
_BANK_SECTION_B64 = (
    "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˜Ú›P“MÓˆ‚ˆ›ŞZRÔÚÍSØ]ÒXÛVÒšŞV™ŞLÛİPÌŒ˜Xœ•Ü•œ\KËÛ›‘ÌšĞÍ“TŒİM[Ñ’\ĞÍMY›MTH‚ˆ‘ZÙİÙ‹İŒÔÙÛĞŠÒ’ÙœÌ™”MÒšX›[Í
Ò[İ[^QÛÌZÍšÔ‘Ô›V›VšÖTQĞœÒTšĞ–•Õ›H‚ˆšQÔ”^›[˜TT”•ÍÍ“ŠËİŒ›‘]ÕŒNXÌÒÚ[ÜRPĞÙÎÔ›ÜPÛSÒÛİUMZœššÛ”Ôˆ‚ˆKÙ”^Z”Ş˜ÙÒRĞ“MšÖİS›^™\™LÙJŞ™ÙÕT–‘Œ–ŒQŒÒÚX˜Û•ÛLZÔ“ZÜÚ˜’œÑZZPÈ‚ˆ›SİÕNÎZ^]QÚËÔÚÕÑÌ›U]^UİÌ”œÚ\˜ÑÜMPÖÙTVQSZÕÛ”‘”•ÓÛ“ÖœU–SÈ‚ˆ•Ğ˜œÙ^TÖZ”‘MZÙ”ÓLÑĞ”L”TUŒRÎMÓLšÒÑVL™‘\Q]İÚS\R‘Z”ØÙ›Ğ˜[Yˆ‚ˆšS“^^KÖJİ^KÌUMÎRXÖNTŞ“]šÙÚ[Í™\Œ”PUKÑVœMšPÜ™ÊËÙÖ˜Ú™ÍÙÚÔÈ‚ˆ‹ÙMÍŞ\˜šÖS‘Û^˜İQ‘™RÒ[ÕÌØYY™œ“˜“YTËÜÜÎUMÚ]R™œ”œŒŞTÕÑVR•SÒŒÍˆ‚ˆŠÒ”İ’’JÌJÙMĞ[NÌ]Ñ‘ÑU’Ú[ÜMYŒš]œS’XS”MÒ•U›ÍQRÑRšÊÙLÒÚˆ‚ˆ›ËÓJÙÎUÚÕœÕTİÙ]–ÎM
ÑÔš™ÙŒİLÙ][•NS‘ÌœRYİYTT‘ÙŒØ‹ÔÜ^‘–ZQÜ‚ˆ“Ìœ^“”›RŒ™Ù”JËÒšÜZRÎY]–‹ÒÍ›Ñ‘ÒSTØ]ĞÙšŞR™LÔÒYİ’‘šÖŒ^U”ÙLİU‚ˆÔĞ™›Q‘š’–’MURÔZÒœXTÚšZ‘SŒÓYÛÛĞÌSÛœØXİV˜ÖÔ•^XÛÒÖ•\U“ÎUÍÙSÌˆ‚ˆ˜“›İÛĞØÒœQÔ™Ğ’UM•YšM“UİŞ›SÜÚÕ^SYTTV•šÒTœĞRÌMšÖŒ•Q”V”œÈ‚ˆ–Ì™X›Ú•ÙšÍ[ÒQPMÍNYÒP^Z]’\›QRÔØYYÍS“U’V™M’TQİU–PPPŒ’ĞH‚ˆ–L”•RŞSY
ÑÍÙÑÍšÙÕÒQ›ÎÌ^”T’ÛÒ‘L•TÜ•™S“ÒŒÕYŒÑ›]š™ÑŠÕ’‘İ“Rœ•ˆ‚ˆ”LÎšXÕšQZ›‘QY“RœTRÍŒÛY]^SLØ›UR™RV’JÓVÍÚ[ÒÒœ[LÙÙM^”šŞNØÒˆ‚ˆœÌ˜“›Zš\İ^UM–“PÔLÙMXÍÍšM‘R•SJÒNXÑÜ•œ\Õ’XÕ”[›ÕÜ›R˜ÙÍËËËÛ™™™•XÛÍQKÔ‚ˆ‘Õ‘]“ÓQTŒÍœS[Ö“Ğ“]Jİ•˜V›‘”ÕLÕÍ”ÌÕXNSSQÔËÑÚÒV^ÜÌÕ˜ZİZKÓÈ‚ˆŒ”ZZLSZUšÖ•ÕÜÍØ“ÛŠËÖ“[TÊÖMSÚ”™Y”ZÖ]ÙĞ‘R›Ş–ÍÒœŒİS™ÕÖ•\U•“È‚ˆÚT[MT˜œŒšÒŠÓÛZT[TÑ‘ÜRœXÚÔĞR™\Q’‘[–ŒN“M™“Œ“›\ŞšÊÔ™V›kQZÖJÎ
ÔÚÈ‚ˆ™^Ğ^VœY•M“\ÛR”ÖÖ\ZZVQÑšTKÎÔÚ–ZRQÑR’Û•ZM
ÔÛMU‘SÍš^–”›UNZ’•’‚ˆ•T[•^YÚŞ“šZU•LŒT”[˜–šNQ˜šMKÜ•ÕÙœÙÙĞ[ÚĞ•ÔĞM”ÍVSÍMZÓ\Ñ™UÓØÛœUÚÖŠÖTˆ‚ˆ‘[•RšØÛV]–ÕÔ˜NšM•[™šUÓÛ™[SœQ•ZQQSPQ™Rš’ÚP‘P”U[Ñ’ĞÑ–LVH‚ˆ–œĞ•TRMÓKÖMĞÜU\ÖJÕšM’ÜÚš›Í•
ÓĞ’”ÑÌÔÕY•›ÚYÙØ˜ÍÙİSÚËÈ‚ˆ˜Œ˜Ú\İUÖ˜\›Ø˜Ü]VXÚœ]ŒËÍŞ™•ÒÚXÓÓXŒÍ^MÓZ^ÔÑ\İ•Ş”“ØÙS‘ÎYZ]ÙšLÑÜ‚ˆ’Ü“LÔÕ’ÊÙ˜’]SÚİ
Í–ÍÖ–ŒÑÚ•œVØZUÊØ“PÔ[ÒÒ[Ø“[–œœRŞ’ÖMMÖVUØÈ‚ˆ”MÎMR‘ÛX›MQUJŞÕT”ÑÕ•RJÊÚ[œRLRÛMXÊØÊØËÓ•M‘X™ŒİZÚTÎ\\ÌQ“[È‚ˆ˜RÙÔ‘Íš”›Ì›USZTŞİZ[]^œÛ›[ÚRZQNJÚ˜Z–[R›U›•ÕÒÑ–œÌ˜–
ÒŞ\]–‚ˆšÖKÚÎY•‘İŒÍÍŠÍ›RLÒšÙÕÚY™‘ÔY]’Ø™™œ]ÒYZ”™Ş\–”TRÙÊÙ›\ÑNH‚ˆ]ÜŒÔ›ZZ”ŒPÕĞ”TQZĞLÍL[P”PĞ™ÖRMXİ•M–SZU›ÜÔÙÙY™‹ÍÍ]ÒQQ“Òˆ‚ˆ–’•\ZZ’Jİ””Ü\T’Í”ÍÖ\ÕÓÑL“PÙ^TUZÌZÜİ›NTššS\U“İLÙÌRYT‘N\È‚ˆœÙUÜÜR“ÚYZ]’\ÙÑ™ÕÑZÒŠÌÚÜÓĞQ”QTPSPSZ•™”ĞšZÕÌÕÑš‘Êİ[‹ØÑ[ÍŒ]P\Õ™ˆ‚ˆ™ÓÎİSZUÑ\šØZT]™ÑPSÕÙLT’PÔÚÍ•ÚÍY\–™ÛÑ’QØÜ™•ŒZXÛTÕVšÓÓ˜ÒÈ‚ˆ™Ù–Ö›ŠÙ™™ÑTŞVšÛšÍØÒ’MÜİT›SÒÒÕÛ˜ÑŞ™ÑX\PÕÛR›MÖÔRÎ›MšRJÈ‚ˆŠÛ[šÛÕšÙNUÌÌÊËÙ‹ËÊÒ–˜UP™Ú’˜İ–ÛšŒ™MÙ
ËÛÍ‘ÙÖYPÖÔÒŒ‘•™‘–ÍU^ÑH‚ˆœLY]’šXÛœMTÔTÌV™ËÙŒÍİŒÜŒÒ˜NKËÌÌ™MNUS–ÓLN[–Xİ–ÊÚRZRRR[ÕUÑLM‹ÙLÙˆ‚ˆ™]•ÌL•ÙY™KÙTÎŠØUÊÕMJÍÓM[\ËÍ\PZÛ–VT“]œ“’–Ğ[ÓŞÎZ^”™T[UÓØH‚ˆV“Ö[‘MÌ[MŒØ^MÙTÚ–Œ\Œ^ØœZQÖV“ZTRUT^Z•LP[™œÓ[Q]–ÛMTİ‚ˆœL˜™˜ŠËÕÌÙ–›Ô•Ñ–‘ŒÔ“‘L^MKÜŒÕ]˜ÖÒ\ÙLİÚÌŒ‘–QØÑTSİMİŞMV]ŒXT•˜–İŒÍÈ‚ˆJËÙŒÍÜXKÓÌQPYÍV[Rš\M™\NLZLØ›LSUÛÍXİU]VÛĞÒS–SšMÙM”•Ìİ
Ø“›^XÚÒÍˆ‚ˆ™ÚMXœRÛSÔZL\ÔÚÓQ“Û•‘•ØLÕËİŒÍÒNĞÒZMVØÍ•LËËİ™TP[ÍYQUY\L‚ˆNUN”šÖ‘\RÚŞMÙMÒMÓÎJÊÒ[ÑÑÌÓÖLÍ]RQ™PQŞYŞZ[ÔÍšTP]PÑÙP•Vˆ‚ˆ›ÚÔQŠÓ\–ÜÖ]Ğ”–SĞ–XÚÔØ”‘ÔÛ’MšV›^X]˜–šJÕ˜ÓŒ’[ÒÛÕÓÜV‘\ÑËŞ™•‚ˆ›‹ÔP™Y\–ÕÖ’›Ô
İÌØÜÒTœX[QT”Ò\’“ÚYJĞQÛ–•’[^QNZŒ^™Z‘U[Ú]“‘PÍR‚ˆ^[İ”–ĞÔ“Œ’›“ÎV^“LZ›ÔMÚ^]“Ô[–MÕØØ\ŒMXUÜÚÔÔM’ÎZšÒÒ
ÔÒÈ‚ˆ’”ÕNYTYÒšX›KİŒÍØÖœ[]šÒ\KÔP˜œšÚUMÌ›ŒŞPØQÜ™MMMKÜŒMNJÊÜ[Ñ”U’”“ˆ‚ˆMÓMZÎ[^V“[ŒÔÍœ’İÜÕÖ–YÙ™šXÍÙRÙZÜPÓR‘ÍJÙ’Xœ•˜RŒ˜]ŒØYPJÕˆ‚ˆ‘‘‘Î‘˜]ŒY]ŒSÒ’ÍSRÖ“L™“ÛšŒX™RYŒTXÔL‘Ôœ^QR[ZŞ[›‘PÜ\QNTŞN‘È‚ˆÖTÚÜ˜Ğ™ÒÔŞÖ’LİU\ÕÔZÍY‘œ›ZÚÚT•XŞ–SVSŒTÒ“™İ]–ÎYİÖRÓÒ\QÙÜPRM‚ˆ“Ş–ŠËÔÚRĞ“[UİÖ[•š]ÖXÓQÍÒU’ÑÎJÍ\Œ\^œS’[NJÊÕXS‘Ò”Õ[TNÈ‚ˆ”•‘Y™”P”ÜĞ”‘ÌİÚ˜™LJÍÙ›ÌÜN™ŞšŒS”•NV‘UU^TÓJËØP]ÙÛ•U›”URŒH‚ˆ˜™LØ“›N‹Í“‘Ú–œÌ˜RJÔÔZÍSÕ›ÛÊĞÎÖİÙ“ZÌZ‘”Q‘MÓZM›ÌTMMYRR[YÍ›[ÕP”™Ş›İXH‚ˆ•œÍ^œ“šĞÒ™ÔœÍÛÙSØÙ\ÕP”šœÌTŒËÔXœ•ÎZ‹ĞİÑRUQ’ØZX’PÜÍÓÔ–YĞÔÕ–”ÌVÑÚTR’‚ˆœ›ÕSÓÛSÌÙZÜÑ‘›Q\[T‘İ–’ÖZUT™X›ÜSZQĞQS˜M–’‘‘”]Ì˜V]ÍÛĞÖ[ĞÚÙİÕR™]Íˆ‚ˆšİÓŒÑÑZTÎTS‘ĞV‘ZØ[•ÖMZQÌŞŒ\ĞRP^’XÔ[Ü›šŒÍœMTXšÚ
Ù’“›“ÓYY™ŠÛPˆ‚ˆ‹ÚÑZÕŞNY]LÌÍÍØ™R‘^YQYÕM™ÜœÔ•–UŒ™ÛUÎZÑİXÙÖVšŞV•Ü–›‹ÙŒRÛÛÕˆ‚ˆ“›Õ[›V\’N
ÍØÚÎœ›
ËÛœVœQÕÓ•ÜÌ˜•œLXSÕYŒÛ‹ËÙ˜’VŒMÎM’ÒV™“‘ÍŒÈ‚ˆÍ™İ]œ•˜[ŒY[İÙÚYËØœÌ˜“Y\ZMŠÕ–‘‘YKÎTR•TÌš•›]œTL^‹Ô“Ø\[^SS‘\Ì‘‹È‚ˆ™‹ÎPÌÛZÍÛ]ÖSQ\™“]Ü•œL˜S\˜ÍPRÔÛ\XZÜÕM\X[‘İ–ŒÍÜÓÒ
ËÙLTY“Ö•ÔÕ‚ˆš\RÛİİ–İL\LT’\ÕÒÑ”İœÛUÕQYÒ–YŒNY–Z”ŒYÚMTœŞœÍT’™ÛRXÔÑYÈ‚ˆ“Ş\Ù”]ØÒ“MSœİÊÌ\LX•YR˜ØÔMÌ^ŒÍİÒšÍÓÛÜLŞXÑİÜÒÛUÍØÙ‘MÌÕĞİÎYKÖ˜È‚ˆÚ›•ZZİš“Y’
Ù”•MÕNUZ‘›UØœ™’•’“X™‹ÚÍÎËËŞšŞV“ÎJÍYÍš˜UÈ‚ˆŒÒšV[RšVZÑ’•œ‘’ÛÚŒNLŠÚŒÙÌ›M™›LØœ•YÌØ›ÙYRZ‘ŒÖQRQSØTËÊÎY]–‚ˆ”ÙØURÙÙ’]Ô^]VKÔÎ]Ğ›ĞÍM[S”ÛT›PV’MMÍ›”•ÒQÍ[JĞ‘N[QXÊÕ\[]ÚÛ”Ñ˜ÓUØÈ‚ˆš™^PVPY]YÒØ–™S™RXUĞ›ÓSØÚRNRV›ĞÕUSSĞS]ZÚ›ÒĞÒÛLÑ”Ó™’ÑNLÍVRĞQĞˆ‚ˆRLÓ”Í˜”PYÔÙ“ŞY‘PUXĞÚ[Ù^”šV˜ÜØĞŒÜ˜[”PĞZÓ›^TÜY”ÛÙSÕLUŞJÚ•–•ˆ‚ˆ’Ëİ\•PÓPTÑ[•SÍ™›ÙœŒ]ÒÎUQ”“QÎĞ‘ØÎ\ÌŒ”ŒL–™Ì”ŒÕÛØ]›œÔÚÜTÜU˜]LÙÓš^‚ˆ”’ĞUMÕRPĞYÛÕØ’šÛÜ’ÛÜU“šT™RSœYXÜZÌ^ŒM
ÖÚ”’\S‘œVU‘”‹ÌÌ›LÜ]È‚ˆšM]Œ\Œ›œ™T
ÔŒÖœÛVÍİ’Ôİ^œÌ˜“ÍÙLÜMİMÊÔ‘İR›‘MŠÍÚÔÕœLQ’˜™YÍ“Ú[ÜRÚH‚ˆ›İ’LÖÕXÚYZTËÍÊÑÙTZŞšÑQZÌÖNS]İ–NÑUÔÍJØÖZTÑÔ›ŒÍÎMY]Î]LÓ›Íˆ‚ˆ“ÚšÍ[VšQ
Ò’ÓŞ›Z™]”™İÙœØNXS‘Î[^Y™’’JÔMÑÌÚMÖ[RšTÛ›ÒšVĞZZTÓ‘ÓŒ“‘]‚ˆ–œÒ’›™Ò•ZQR™Û•ÓŞšXS“\ÛPÚ˜RÒŒ“YÛœ”ŒÌÌÌLÍÜ•ÛSUŞ]‹Í™”ÖŒUÖ[ÜUØ’šÙR‚ˆÍSŒÙÙUU“‘L•QËÖÌ”\ÜTÜÌ˜“Û˜œÙSÑPU’™ŠØ’ĞÕS^˜œ›Şœ[JÎ•\ÚÕQZÕ\ËÈ‚ˆ]ÚÙÑÎĞÛTšÖP‘ÛUš––“
İĞÒÔ[ŞTÔĞQÚ•’VPÓÕ™RTØÑMQšÔ\^P^\–MUÌPĞ\ŒİÍÈ‚ˆÌY]’V•^QÙĞ[ÚŒSĞVNZRÙœÓLÜ‘U˜Ö^œŞÓ\“›ÌPŒ”QY‘‹ÔQššÑÔÓQ˜ÔŞYYZRPÔH‚ˆ˜XÕ˜ÜMUÖQÑÑ[‘™Ó\Ü^TØ™Y”Y”P\RĞPZÚZØÔV˜ÒŠØËÍœÔ’PÜZÌ•ŞÈ‚ˆ‘Í^ŒMœ“ÚPÑ‹ÛÖŒ‘’“LÛMXËØÓĞ]œÚÙÓQ^Øİ•M–“[•TÜİR™ÖUÒŞSYXİÙÎ\È‚ˆ“’‹İ–LNN
ÕÖ‘ÔšÍ–SSÒ]–šÖÌÌ’İ‘[•M–QXVŒY^]ÜR‘ZU’ÛÚ\•œŞ“N’‚ˆ”XÜ›Sš[ÓQÑRĞ^UYNNYL™ØÕÚÔÊÓÙØÛPÛ‘\TÍÕZQXQMœÜ•T^šY››ÖR’šŒÚÈ‚ˆV“ÒMÚÍœÚV“›]İVÌ‘”Ó›^V˜İR‘^XÊÙ]•Î]LØÌÌÍSSÒVQŞ”Ó˜LPÜVˆ‚ˆœU“Û]–\ÕÔXÓÒ™U[ÚÖLJËÙ›Ù™™”T˜U™šQT^›NS“”Ş‘[ËÍRÛ”™ÒšMXÕÒÌX]\ÙH‚ˆ‹ÓNÑ”P•\[œ\ŞVœX™XQÜS]ÑÛÌQš^SİİŒ˜’›Ü•ÜÓÔÑšÓSÔTPÙMMÑÊİ•Ü™LXNYœH‚ˆŒX]Ù[œTÓ\ÓÙÌÙSÑÕ›MXÜU˜ZLZİ™İ–˜“›œKÛ\]Ú\S–‘œ^V’[SNÜR
Ş“MPL[ÕXšR‚ˆ“ÚS]Ó‘ZSMRSÙUÓÑYÌÖMÚÌ‘QPRÌZSÚXÙŒ–”İ›
ÍÎPY\Q^ZÕ]–ZÜMY”Y™ÓVMÓœ–H‚ˆÑÔR‘Ô^PZÌ“ÓÒQÒTÛ›ÛYŞQ‘ÜØÌSÍ™ÛÔ^RŒÑŒĞMR˜MÙ–MSLØ[ÙÒÍ›“ÓKÙ^’ĞÎÈ‚ˆšM–PPSMRPNV’Œ‘™”Î[’ÜLV^V‘™\Û‘ÌÒ•Y^ML[Ö‹ÌÙÎJÓİ›YÒPÍ]ÌTˆ‚ˆŒULQÛÌÍPÛMÕ’‘Œ^\ÓMÙN]Œ˜]œÛÚPQ›œœ˜Ò™ÖUÓ••Ò•Ñ™•^[•ÜLMŠËØY[R\XÈ‚ˆ–MŒÙ™”“•›UÒTÑÚ[N‹ÓÎNÔVšËÎ•MÎZ
ÔÑÎ[ÛZÍRTÓÍŞÔ]JÖS•Ü•XŞ”]ÛÓ‚ˆPQNŒËËËÙ™”LŞ”^JÔÛ•›’]–“MRV”LÕŠÕŠÌMT‘’ÌØÓUÜ[]\X•ÍœRÖKËÊÑÍÓš]›È‚ˆŠİØÑĞœ\ŠØÒY™Ó‘ĞUQĞ™ÖQĞš–œ‘]RÔÚÜV’ÔZÒÖ[RšXÛÙ’ØYŒŞÛÚQšYÖ•ÍÙZ–M“È‚ˆ”‹ÊËÒÕ“
ÍÙŒ™PSĞ\MS’ÌUÜU’Ó‘Ú˜ÜU’ÍY]ZÒRŞNY]Í™•PÖMŞY‹Õ”Õ”\‘YTÙˆ‚ˆ\ŞMXÊÙLÓ“‘Z’\VMZ™ÜÒPÒÚ\U“›Z•œŒMS’ÑŒÔÓPQÛÜÛ•VÛ\ÓÑÍŞSY]’ÍİV“È‚ˆš\’›LØœUœLX[Ô‘T’ØÒRŞÔ”››šYVÑšT–URÑ•YİÓQ“Z˜İÓT™ÔQQ‘^UQŒÓŒš”RQM‚ˆ“ĞYÛÑ[URËØ›”ÕYQ”‘UÎÊÛÌ”PĞ”ÜÔ›ZUPMSÛQÜ–[ÚÌXNSSİLÜ‚ˆ‘SØ^VZŒÚMPJËÎJÓRšV[\Í[^›UÌUPÍÛXYÑRÒVYZ”Q]œT™•Ş^šR]V‘ÓÕÙØXSPĞÚR”ØXÍÈ‚ˆ\Õ^Ş’‘UTL‹Ì–MXİœÓPÍ˜ÕUUŞTİÍ^™ÔÔ™ŠÑMYSRÔ^]PQS[[Ø‘ÒSZÓœQ^‚ˆŠÓY•Ó‘ØŒXœÜ\Ó›™‘“’•ÓLÖUØ™Œ›XZÕ‘“˜œUKÕXP[
Ö”ŒUÊÓÌÖ”™È‚ˆ˜ÊÌÒÛÒš[“œLÍÚÖ‘Ü›\“Í–ÛQR˜S\^\”VŒŒÖQ›ÌœÓÒ‹ÍÜ‘Ğ”SSUVPRŒœÍÑÙYSÖH‚ˆ›ZÛNQMVXV•œŞ[Ûİ–]ŒLÔÒÍÙP–JÚ”Zİ\ŞTSX™ÑNYUœÙKŞ[œZÖ]ĞÒKÕPVYY‚ˆŠØ^YÚĞRÑZÜZÖ“Ø–YPP\œ–ĞŒÕÚ“œÌ^\^ÙVœ›˜šŒÔ[Q™ZÍŞ™MÌ”P\\ZÍˆ‚ˆœÙÚÌŞÙUSœXPPSÔÍ“UXQ\SÔÍPÙ’Õ•ŠÛÔU””YÒQÛÛXÛ“‘LUÖV“šÍYLMÜŞ]ËÛÈ‚ˆŠİ]Ø^VšœZJÚ[Ì›Î\YJÕ“NVR•ÚÑÛ•™˜U–œLĞZ
ÑŠÔ’ÓÛŞ˜Ñ]U™ØÜÜSÖKÈ‚ˆšQ™™İ•‹ÕŞ[™QQ•‘œMËØÙY’LS˜”ÎMTØŒÚÚÒ›NXÕÕœZÒœVœÖœ™šÑ–‹İ˜ÑTœRUÙ[‘È‚ˆ™”Yš“ÑÙÔ–šÔP˜ÛÍLYÍ\M›\SÎŒÜ\ÓL“ÎQŞœÒRİÔQSJÑœÙœUÜŒÚUÈ‚ˆ‘LšSRÍQœ\RSĞ™İLÔËÛŒ‘›TŒÔYØÖMİ–’›LUÙÛÜRÌÑÍU\™Ş›VZ\^]’ØÜT’Ö“È‚ˆ•˜‘YÕÙR“”ÑİMÚš\R”ÖLÛŞNX[Íİ™‘•NRT’YXœ[•ÖÓ^QİØÎ[^Ğİ[LØTR–’–PÖŒÈ‚ˆÔÍ”\š
ÌÑĞP^PŒÕœİZNL‘XLKÚTQNJÓ–ŠÔÜŒRQÜ˜›]’İ‹Ù”LÌKÜ™VŒ
Ü•ÙVJÜT‚ˆ•ÊÓÎ•]ÛĞÔÜU[SŠÛİŒÙXSÍL]œQ‘YÔÍZİÎÛ™ÔÙÚ‘šĞ›\“ÖÕÔÍ–SÔX”[È‚ˆ•ÖÍ™Ğ”ÌPÖ’‹ÎZ˜[ÒMÒİ–Y’LÍN[RÍÜLİİÚÚQ™ÔšÌİ“ÍRLÖ[ÑšÒ]Y‚ˆÚYÚLÍ^™™‘]Í“PÕMœÔÍYMÔNœTSS^™ÜšU‘‘ËÔÍM[ÒœÔPØÒ›•ÌMÌ“ÒRÙNS”T‘ÒH‚ˆ’œÔÑ]Ğ›‘ÕšœÒPZPRÒLÍ[V‘”RÒÓšŒ’ÍMPV[ÖLRÙÖÔXİV™[YÎ^[ÓİZÑRØÓØ˜ˆ‚ˆPšØS‘Ú”N’‘TPĞVMšÓÚYÔÒPZ\İŒÑRÙMÛ”PQZÎ˜X–KÌİ›SÑQĞR˜ÛÛTR”M›R‚ˆšÑÜÑ™İÑQLL’ËĞXÌR”İš‹Û’‹ÎQ[ÑQUÜ\ÍÕÛÕZÑ’ØYØšÕÙÑZ
ÕÜLÓÚV
ÎMËÑQÚJÒ“N˜È‚ˆ“
ÙSVÌSTÔ˜’ŒÌ›JËĞYQÒĞÕU‘VRŒ•–ZÍ™Û“İKÛSÛÑİLØÔL\URÕĞÍ‘ZS”ÚİLŒ•È‚ˆŒ[LÖŠÛ”RÌRÑÔÍÑ”ÙÜ˜Ú“š^˜“YÛ\ÓÙRÖKŞ”X››Ñ”PÓSYZÔTSÑLËÔŠÌŒ[È‚ˆ›’Ñ™İÖSšÔ[^]SY”ŞPÑÒ]ÓNSJÒÜTÍ›ZÚÑÕÙÑĞÖ™ÖT\œÑÑ]‘ÙĞ]ÍXÓÔ]^]LŒ’Û“ÌLš‚ˆ’ÕÙÖ[”Œ^]ÚÒ]”œÖ]•˜ŞTP•T“ŞXÚÔİY“œÜ\ÛÍŒUÍUÍÑXŠÒ˜S–”“Ö’S–ˆ‚ˆ”X“İL\ÊÔNLİÎXŒYÚ\YL™ŒVY‹ÎZÑ•LÎ•MÜP™Îš–YN^
ÊÛİ‘KËØš›È‚ˆ–ZÜÖRÚRSSÔ™VÙÙYšÖZĞ‘‘[ZZPÑXŞ^VSİÌ^SššRÖ˜U“SĞÑP”ÙÔ[–JĞXVŒš”H‚ˆ›ÓÑ™”ZÙP›T™Ü]VYÛSZ\PQPUÖL“ÊÑTRĞPÚLQ‹Ò•’VLÚÒÎšÜÔĞPĞV^TP’LĞ••LP[ˆ‚ˆ–“[KÖØØLTR–İVXĞQÑ•XÓ[œÔÖŒXŒ’šZÚRRMœÑV™Ğ™Ø“MÑÚÜTÚÖRSS^YÒÙÚ”İX]È‚ˆ•Ü’LŒSÍ˜Ùİ›•Û”‘[\œYSÎZPÜYZŞM’‘Ú“]Ü]ËÒÓœZİ\‹ÎNQÒ”ÕYİÔ”V‘•[^M‚ˆ“]ÍRœŠŞR›ÚZİÑÖ“MÕŒÑNUÚÖJÓÍÓL›”œ\ÓĞTİØÓÚTXÔ‘UÛ[TS•Ú”NÎ‚ˆ‘\ÍÒĞRÔÔLMÚÍ”Ö‘–RPVQÚST”T
ÚÑÓQQU]ÚZÎ[ÓĞPUİÓ]“^Öš\U“’ÊÖ˜TÔ‘È‚ˆ”ÚÑNÔÛÛ•ŒØ””^Mœ”N
ÖRÌŒŒXÍÕŒ‘SĞ–SY\‘TU’]ĞÓLÕĞSZYÒÚP”[ÚšXÌÖ]È‚ˆ‘šÕØÛ”ÓYTÑšTÜ•“šÒ\TSÕ“ÒÒM][ÖLMÍØÑMÕØÜÔ’UNÓŒĞ“œ\›İšÜPŒÒÑÎR[H‚ˆV˜ÚœJÜZÚ™TÒZ˜ÖÌ\ŒVL[™ÑM™™ÒRVLNU“’ÜL[šÕM’ÑTQÓÍÕLP“LÓÌĞÍÊÑH‚ˆ“[™ÎLP[ØU˜™Û^M›•˜Ü–‘ŒŞ[Õ”ÜSPRÖR›Ò‘VšİYœÔ]ÚËÒL”R˜ÑÜ]Ù›ÓŒÙLMÌH‚ˆRœTUUN‘›’›Í˜İÛ–Tœ‹ÚÊÍJÌÍ‘VS•Û‘Ñ™ÓSUÑUXYÒÑÔ^YÓSĞ‘RU˜Ú“TUÚÖ“”ÑPSH‚ˆ›ZYİ™
Õ™P]U”“™›Œ^’œ’ŞšÖ•ÛœSÛœœÖT’‹Ñ›ÎQTØ‹ÙPVYÜÕY‘˜ÑQ^H‚ˆ‘İXĞĞÓ’\RİÑZ‹ÙÖRĞ›ÙU˜™•ŞŒJÛ\]Õ””““‘Ú”[ÓÑYQPVMœRQ\šZÎSSS“š’Õ‚ˆXÒTUÛŒÑM›ÔXÔ–ŞÌŞQœRœÍÌÌÌR˜Œ^ÓÛ˜Ö]XÚ–‘•\Ü^ÛYTTÓS˜Ù\\Ô››ZKÛÚ‚ˆ‘“XØÌ
ÊÙ™Ù[PÓTŒ”›ØŞM“šİ•R“[ÑÔ]ÓV
ÑTšŒÓ™Ñ›TQ™ÑšÕÖ”ZØ“Mˆ‚ˆšSŞ™UJÍÌSÍPÜšTÛÙZR]”ÛÖ–›˜ÚZV™–Û[TÛÙPPQÍ’ÖZ[Ú[ŒÜM™œĞ\Ö–^‚ˆœÍ[ŒY[ÚÚĞZS”\RÖX]UP]ĞĞ\Î’M[ÒÜZŒİÚŒÚ”›ÊÒĞ›’ŒÜ[ÒÚZ˜İÍŞYSP]ĞšH‚ˆQÓZRQPRÑQMSÛÍÙPPÔQ™UYİ”M™SQPQ•Œ\LR‘“›ŒY[VV™ÑXVœÒÒ–›]Ù˜ÍÜN[‚ˆ‘ÙT–QSYšZÒ]ÔSSÕÔ^PQSÜU‹ÚÙ››Ó˜ÔİÙÚÒ“”ØÑMPSĞÚÕ‘TZ\ÌÖ‘ÕÑÑœUPS\NÈ‚ˆ’QÕŠÕšYUÙÕL‘šTšÌRÜœÖ‘ÓÑMSÚÌ•MÚËÑĞNMMY“ÜSÓÑL[ÛSY\ÙQÛ˜ÒÊÈ‚ˆ‘LŞŒÌ[˜”›”›ĞÕŞLUÎR[š[ÎÑİLÌÕÊÕ™˜ÚYUÌŒS‘İÖS‘Ü“[ÍŞXİ‘”•ZÚPRZÜˆ‚ˆœ[ŒšÑSÜ[PYTNİRÑİÓ^[Xİ\ØLRPU‘ËÒ
Ú\ÌÜÓÑÙQÌ™“M”“LQØ˜Ù[Ñ\ÕÈ‚ˆ•”’ÙŒÑ[TUR]U–šLQœÜÔÒŒÕÜRPP™ÕÔXRİÛÜÚÔZœÓUÒÌÒ^ÛÒ“’ÊÙÔTRØĞQN[İÎÒH‚ˆ–]ÙÔÎ‘’ÜRQRÒ[ÔTQ‘ĞVUP”ØØ]ÕØ’QİPTÊÙLœÜL˜ÕZMVYUİĞšŒ’ÖšRTĞÎQSˆ‚ˆL˜P\PÙİ’–\QÛYÌĞŞ““QPÊÕLÔÌ^MĞTTRÍSQ”›RSQ’V˜U•ÒÔ‘[”ÙÕÒ“İÍˆ‚ˆ“ÛQXŒMÖ]šœMØÕÑÚ[JÕRØÎŒÑ\‘Ö“”Ø’ÖØR]Ù\ÜXV›š^Y”M–]ÌØ\–M\QÚPÕUÙÈ‚ˆÖŒ™ÛÒTM‹ÚR•ÖZ’KÔNĞ]ÓÓYTÌÖ[ÕZVQÜYJĞšP’^›RJØÙ^[LTQÕMÛ™ĞÜœ\”H‚ˆÔ”QŒ”ŞT]M\U‘œØÍ[ÍŞ^™[ÛÛĞÚQ’›ÓPÕRÚXY]YÙĞ]Ñ•^UQ^ZUÛUš›ŒÓ•ÌĞˆ‚ˆ™Í›\YVUÚÖš]ÛİLSSÎQÍĞÌİTXZÓšÚŞUP\\Y™Üİ›TTTXĞX“Œœ]ÜXNSĞÜØ™X™Ğˆ‚ˆ’LÜ›RŠÔSÛ\TÙ“Ñ”’L›š\ŒÑš’ÑĞÍ’ÔÙRØ˜ÌÔ‘Z’’Ş\TÜÕUŠÕ˜˜Õ^LXİ’Ó‘ĞÕZ‚ˆÔÔR™X›ÒŠÌÛÖÎTVĞ^^RÕY]ÓØĞYÍ“ÓÙMSPœVÊÕYÚİÑÍ•Ö\ÍYMPÛÛ[MYËÙ^]Ü“ŠÍÖH‚ˆ‘ŒÅ·g§wt&–´¤uB³D³”fV¤ƒ’³”T–V&·&4f…tÇ†„6³¤c#†”ç„Ô”Æge6#–GƒC…4E4DÂ ¢$s–vã6ä×¥&ó7f5Wt$&¦öµ4–Ó”ÃS#t¤c$¥¦×Ee¤gegC"ö4ÆB´•¥wTdTVÖÕ§%ct„â¶ÇVã•„ETb ¢#„„cd&‡w4eFdÒ³&ô6‡77§µW…g#”öe‡D'ƒ–¤Ä÷—²µddS$EUƒd…c‡u&&E$$TÔ'$ÆE3–¶b ¢%C‡$Ä–vµ†#6§7W6&ä§†Õ‚ódCFDÔ¦$äÓcTG¥6Åge3e—ScEC$·6¶Ów5”³tFÔtô¦w…g„„Öw“#tÒ ¢$&röÕ'UCvW§6–5–&c##s‚ôU$ÃV¶å„ÇeäÅESd„$Ó—b÷U—T&”6sFC–¦Ä4—c¦U‡T6v5§ ¢'u'dó‡$EeGƒ$¦²´Õ—7s'&Õ†„Æ¶2·t¤´SV”·¥sE$6”tC6¤&ç$‡stFÖV4Vu73&æ•"ô·w$’ ¢$6öv•”W„†„Äæ”w–ót46¶6ÔôU£VÄTµ„Eôt&´„tTu5dWtDÆöÆe$×4æ•WDW£r÷¦bõ„–&§$„Ã%B ¢#vDçd„â÷g†Å–$DÃ†ôóc„Ã6#%fb³dæ—tW•C–4…4ftv4´—–uƒ¦ÇFTUV‚ö5&…ET¶t¤#Ce6suW¤â ¢$·5£„6$¶V¥DôTôD&s2ô·3DDÇSÓgR´Tsg4õvt„¦4dÕ…W4–TöõWC'tv…§…Gf×EƒÄuFs&¦%r ¢'fDÔÄÄT'•5¤Æ‚ôwFÖÆò³7tç”D—tää3†–u¥£%TG—t$ãRõg„–¶×†–”ÆeCUGd£D·4”s…¥5dE5SDEuu§ ¢%e´µ“FÔT7T§fÃ$„c„TÆÓT”£TFVƒ4÷¦ÕV#T†GTcgFEtãw7ew#CSDF…$f¦ó„CW¥V¥'T7¥Fç“GSb ¢&öC'ƒ3sut&"ô£6§ƒ3w•”6Sv¥C”v'W—fgGtç–G„s$‡4$§•W•£Ç”„g6¤e†&ÓF„Fwu”ävwföt$â ¢#t„fÆ&¶$ÓTfVƒEW¥G6“ws—…4å&t$öÔ†—…4vuBô£fW”fBô†´&7gsef•u4sfB÷4¤÷sV¦‡t“&U—2 ¢$ÓgF³vG¦f'òô¦¥G…u†ö3DGDS%D$µFæµ§7'GFõ‡t”…FS‡f$V‡¦³g4ÅW#E£DF…‡„&ƒ$‚ ¢$ÓtµƒWGV†fF´ss‡t3TÓ6fB÷d´ã$ÄÔæ'%—Eguv§…•£Vó&æwg•&Ç§FFö%7v5’²´Õ“†Ôç7FU†b ¢&Å¦'4v×W¤3wTövÄvÕ7f¥Vgc–vÆó…täv¥C‡Dƒ3fÕ¦D÷tÔÖ‡$T“cƒs5”dB·t3”Ç%d¤Ä”R÷ó…sR ¢$gfÅt„æä„w¤TÕT–‡–7¤„ÖTæ3&'¦Ó#'Uu–Se£3U5VEâµ·W7#Ttós5D36ÓD6sC„vw33c”s¥‡§‚² ¢&ÇÆ$%&Ã”ÖÄ¶6†ô”FF–Ä—w7ôõc”7–6Å”ÖÄ6V´ED…&æä–¦¥f&µT…B³t¶Ev·ç'„Å7—¤¦vB ¢&v6g5tÂõFF3”²µtu6·´tD‡6Öôdf–dÇ¤††f´eFÆ„w§×e„µ#…÷%Ô×&Ó†µs4æ3uôT„Gg„R ¢$%$Òõ'$—¥U„¥4¦B·f6¥WV•„GU¦ã6ƒd&Fµ•W…4DÅÄuDGVç5fDöBµ$÷¦$„æ'Fã#‚·e$&æÃr ¢#We#ƒ3v†t×G6”Öòµ%33's³6†VäEfE5F“7S‡Tæ”öf'Tö6ógvSg7D”•DGÇ36ÓFuUTÖ¤b ¢&ôÕÄ”…UUB·tóf”7'GT§†U’õ‡dC„FÔ…‡w#u—gf¥wVÔ´Ö#6„×uf„µCdô´&§%f#e„Æƒ‡CSf4“fã”‚ ¢&eõu3tWbô”ææ5£e#3gfCrôT¶„¥D†£TVæw¤÷Edd%'—3†$¥Öf#&W"¶&VfÃµ3T–µ6D¶#&ç£2¶#D" ¢%%¤¶¶Ã–sT”ôub¶Ww—Uf´d¥6†e„dvW„t”VÅ„S$4f„wggd5†"÷'tÄ„—¦ESe—vÆDÆ÷‡#'†v² ¢&•s5w¢¶×c36Æ¢´´&·¦¥„6tD—“6f–‡vä†£„Ä4V¶µddtV#ä#”Ô–—U†Ãb¶EfR¶ÓDDçU†Åcd£WU„öfÒ ¢&Ä¦Sveµs#fô$u…6'¦Wt´äfÅrôÅtW%V•†&÷…GGU†"µ4†GF4ãud44§……fô&•‚´–3t×F’öGtÅt’ ¢&ÄÓVW…Fs†•$äõÂó„dfÆ3sfD¤ç‚öE”†44¶×eW4–Ô¦÷F¶¶§FÄgGuu¤w„‚´"·t×6v6µv†¢ôÇƒ’ ¢$—6¶V´õ&Es‡fFe•¢óT²õ–Ãgeä£†s6vÕ‡D¤gGtÃƒs$e‡fÔ‡—fE‡3v„$DDÔ²ö’õd¶Tç…Wg¶E$dµw ¢$v‡&T”$u¤¦s$×gc#”ÄæÒô¶B³'¤DwfÃ7‡5•”T¤§g„V¥…“v¤÷¦&çW%•'D"ö¤%…•Vc—”"õƒu§†&TV7¢² ¢&ó6U¥'%w6·…¥ctv…döõ—cd•£C$ÇFãv¦tÔÔ—‡s„¥3B³f—sG„#$4¥7dg¦tT§$“eeFõ•¤¦×EƒD÷E‡tÔ ¢'…å‡V%¤äFåvtf§æGƒu§D·•””£3döGVÖu„…%d´óD6–6ÅÕ…‡…£fS–ÅRóf6#£—3$×Fg–§¦2 ¢$D…ƒgCwE'—¤ƒ4†–‚³V'$SU6µdÖdu6”e¦Ç3sf”ç„Ö#•—„&bôÖgTE—…ƒ£“CVµ£DfCe£ƒ7V7b ¢$ÆÕuƒdSFGe¦Ä¥5T7†7TT3V7Ut´g’ò·£õƒ‡u£"¶dÆÇƒC†f7‡…‡#C—ecrôæw„×ró”…SDö”Ä$Ò¶F£’ ¢%VfFTƒsS4§¦÷6Ä‡–÷gÄUW‡&Æ•sV7E‡¥¦Årõ54ó'U”Öt”d%“v£F„…G$ó¶„s•4swtÖó5“c5B ¢'cT¦ãV¶#u£%¥D“eDõv%f„Äãt$ÆGE³3—s&UC$Gg4ÓRõ…¤E†ö%•4¶ôTÅ”gE7D#• ¢'&¶4veSgdC§$f”“”CDÆs$Å%%—£v3“3v³V4§¦§S#6“†$æ3#…§–$Ç¦§37Ubõ”4¶U’´Ä£ƒ¦ÄÖÔ3 ¢$ÓT…cU'7ƒfÇ'–uƒ3c†¥6“bó#–F3T7F´egÄ£ö&…äçg#s–Fõ¥$–s†WeôÕDu#S6Ä$TT¤5§s’ ¢%dÔ¤cE%d‡ƒ…6¶ôµFDÕU%¥WU…gãtd6ä§•–Ô¶–ö–vÅ3V#†dg‚÷Vö–¦GS4¤·–5„g…GUDGTÆ“B ¢&¤—tÖ†Ôv7•†„¤×W–“GDÆT†“E6w”Tf7†ÓƒUW%cTµ6¶µ%&D†C4Gv´¦•–”””äÂöV¦fÇU†ódv–'¥V%GDFõ’ ¢&ÆÕƒ’öc#—dÇ¤—•b¶ƒ4¥&ÆÕtu—¶–õGd46•%—2²´ôE5¤¦WwWu&dƒ#vG4öƒ„æôä¥—Sf³sd—•5d¢ ¢$W7W”Ó6$Ó$ÄæäC‚÷§C#vD6sDõf…$bõ¥dt†‡"´õdÔE“cTä’ô‡t6Væ4E5WÒ²öFvdE%4fdUsf†–•·&år ¢$E•TGts‡4ãd”C—d¥4ôÇ%f–#’µS†åC—‡¤†¶u%¤öF7¢õC”c4Ã6ScvdÄfÓw2³tÃ”"µ·”VÅS" ¢#……$äµ¤³%G”¥vW5Suw3„ôÒµ–TÖWƒFG–ôä…6Å“%dDÖ†´4“Ue•4–4ƒd„fuuƒ3“Vç–Æ¦Fäb ¢%ƒ3„D&Dõd—DÇC—”ö&„%ä¤÷S4æ…U$†Ä4£t·vÖ#–”dÃu¦Ä¤gWdw$Õ4¤£u“gs—¤'t6äÇ…”§et%–r ¢'C„e&¥cƒ$T„tR¶Dö…TD5•D—u”Õ”£CW…deU%$fÆÕt×6EgÅgS$Å„ÔW–Ó#vGf³S’ò÷fæç„7c–FFb ¢&³t÷Äµ6¤–¥–…w%g•—¤¦‚³6ETÔ“…G¥ö´vã¤TÕSvGU†T´¤–Ät'µ6¶6UvÅ7g—fã#6G¦6Ö¦Gb ¢&gW¥”ÖV5'”5‡”ÓtôFs…–¤µuw'#–fõ4¥W#fDÖäÆ“wVÖ#“––––”D†WC#†gw¤×s7§§¥FgÇsG”3ò ¢&e¥–5„•e6…uW•—uuDƒS&…¢µEæ²¶ff÷tD$ÕT„Bò÷c„ãCC¤„”Vµ•’·5†”´×7tæWF¢·GƒV¢ ¢&¤UWs‡F'6F×F†Õ34ƒcVµ¦—fÖäçw‡7ƒ3v¦Ôô×'7‡FÅRõ¥Uƒ'„&„Ã²ö³”§UÓ&”¶ä§#T'vÃ#fô§G¥&#r ¢%B÷7DR¶FæC35‡fäƒ4‡“wU¦VÆÇ„ÅG#„¤õƒ4tö#‚ôõƒ4‡‡dµv†WW‡W'$”ÖÅ”TD„wFÓƒ#V#Ct³gEuc5B ¢%ä¤5WSvöÕ“vE#…eDcU634vf6æ¦v¤Ó4ä#&UW'F–‡C…†5•——”¶#…WccSD&v´ô'tôæ—•¦7f7U„ó’ ¢'f#$¥³C’²¶U†×¥§5U%VÕ5$µ6²¶µ“#&TtT–vöÄ57–V”´FödÃFö”õF³T¶uw‡%g#§3v‡u„c4ò ¢$4ô¶6äg‡U†gfçFÇ5åFóô„FƒV7Ew¥§“TÖ¦åu'DS&¤”ÕSt¦µ5„Äô's†W„Öd‡ƒ†d†ç£S’·7•¤Ót´d„S" ¢&–E6÷–dæ”·r÷'£F¥‡'§fVÇ§D´Æõe§—–e%¦•F³tç“V7Ö¤—–åwS&–dó%sWs—C'cVFÆÕFäåc‚ ¢'sW4U%”v“d£ge–fÄsVW“D‡—s†S…ƒ†„ã‡„%äµ#•F´ÕG&Ã£TóD4••¥——uEust—66Ää„d6·" ¢#3Guf£S%fg'döÄ…ƒ“RôvFä3w…„7V¥6¶eG&Ö7S4ÕT§6w‡7u¤²ô55t7…Vt3D¶µDw†´çeTÂ ¢&Å•²¶d—Döcf†·”dw—§Võ”f·–Âöç§t„vtEdö²µ7†g§3Cr÷„DCte¦×†W„vfFs$FF¶×E•„åGRõ‡$Â ¢$#4ÖFÒó4#‡v&s$„e—fäö$·StFEw¤FEv´¦¶uDÕsT†Ò¶†ô…UFDÕ¤u&ãs’²÷c3s‚ó†'#vGC#E•öÖÖ ¢$$Ö´Â÷dScED´£E„¤£7–gEwfv†õ”–wâ¶D6$5V†µ¤uCs–•4UVDöåvåGÅwVµwc–6ä§“–gfç¥¢ ¢'6Õt¶ö·–ä¶Ä¦·•¦…•t…6–Åô´7'sEµ#†ó†U¦÷•¦7…Ff“B´Ó6#“C…§7u“F£F”—CC4§£Ws–Ô" ¢&ót”fÕ$CÃ…’µ#CS#–dÔ$%f4Ö'–æD'WC‚µ¤Ó†G4çfgc3s“’²ö&¶•F¦&ôw¶‡„6ä§sd#6Tµ”×fB ¢$Ôs…GS–ƒG$fb´SgCdô”#$ötç£SE”6t'v&'†ã45dóå–µeC—TÔ¥–·“d53we–ÇDsWeƒÖC–Ò² ¢&ä3Ef„Äç£VGGƒ$u”†—$´ÖÓcR·†¦Ö¤µW&Äe“vT6„§W7d‡¦ä‡%“tT×F•T#d†DÇ†6´•7§3fÅD·sST‚ ¢&Ät§cf…%–tƒƒ“…•†ÄÕUe4¦÷'†sUt…Bö’´…¥CDçT6Å–£w—d£f%“U‡—5ãtDãf§$ƒ$·&ÆÔö" ¢#4ã‡c‡W†fvg–õ¤stc4§¥%U“—dEu¦—µ$ÓFv2ôDDG¢ós’¶g”4ôu•D—”Öæ'C'Ug3w…%Wwwc7%s…Tó6 ¢'EWUT´de“%••§Cc†V&Gc7væÓ6$çS&¦VCSDsU†“t÷§7EweƒWV&Öge…ecU„Æã6Óe‡fSwUF£w‚ ¢#‡dÃc”äåG‡sEd…V¥'36”…%t¥w…5VÄ¦•—–ö—fVæ„U$UE$ç¤Uƒ„õ&ÓWDÇ'3GuDd¥3#s—–”¶–ö”’ ¢&4†C6cSU§dÆE§$å§%e¤$TGs……c5—e†¤æåDuWfÓƒ%vµ¤†ƒWVvÓWdÄÔWƒ&G%–µ5sWV'U&T4äÖ´¤5² ¢$¤5Gu#†T‡Swgg#VcW´ƒ”ästÄÔç†äBõDÖävvWec5v"¶Öçd”F¢³W43%&µ†G”ãdóU'gC3#Tr ¢$4öätE†#VV%cV¤¥GSt§ƒ…E&ƒw¤Sg$•#„ÓfFög6ä”w¦3eeDc55F†ôô5¤Ç•VÆ÷–óFõ%VUU—efÅrµB ¢'w4$×„äµVg„„u—„Æ‚ó–…4””TÄs3vW#W$Ç#E…eSD%T„'¤…g—Fµw%eVUD—VæsD‡%f÷“v…´ÓGB ¢&¤WFäöãu–åGGtÖÃvƒuT&FÃ$&WeS–d7g•—§G„…§…U”wdÃsdD4–eGsƒgE7w¤R¶Vd–³…U'#”‡R ¢#6'EESôÄg“–WEwf4WõGd—§3Eu&DgWGwT4””4´—TÔd¥5W#ssv§T¶ö§s•fWU„Vä3†×&µduW5u‚ ¢%gV7Ud¶Å6Æ&Å¦t–…F¦6”6dãE„$–·Eƒc†ÇDWTô¤t%3wC7#c–gEw%fF5v–We¦ó–EröeWe² ¢#6„d5#CF7e7WU„¶Å“†e£S3wG„¶Å7%gWe‡#de7Eu„ÇC$Å$…t%2ôæ6G£’²ö6¤—•ÆÅ736'G“E¦r ¢'…ƒtdU„æÕDöå–4ôuCSC†µucS‚¶$ãV7gWc7ä†§v¥Ge6´D'sG4Väwu&µEg¶…WDÆ‡sFTå'ÖÒ ¢'$E3„Æ'´u2¶g–R¶e3T¦ÆfDU…–f†¦#t…'tÖUgWd„Gw…FÔÖƒ&%#$Ó3Ub¶ã%t„…–6S&sCsófv’ ¢%†×†¶FWTÔ¥“fFƒTväsfãW43–“7guG#D4%“DvÖ•6D³$…¤öæ5ddU•v¶äÇ‡s†uv´òöUdDÄ÷sSV†¢ ¢"õFÂ÷se¥F44s$†ó–GVG“”‡´ô¥UT”G“D´gU4F6ÄÆDÓbõW756ç–dFÄÇ6et…Õ5†„Õ#V%&f$$$R ¢'’ö£W”¶†§%†¥&¤ç´ç6t“öe¤Ò¶WfÄÆµe"·f'FRô†•%—dg6ã3s—$¦Ç—„£c$Äf¤#¶õSfD÷–6ä£SƒfB ¢&W•ƒTçgW&•v—utTDÖÕDÕ¤u&´´$&sD4fÕw•DdV£…•–Ç“$æ–÷–†w&…WF†×Gr´F'FÓ¥¦´vB ¢$öåT“ƒ%fµ¤Å'S6g$öåG4TÇ¥¦Ç#²ô†…UcdFƒU„Æ…We†‡t6äç¤‡£S„4F§ƒB²ögceö†ÅudUR ¢$W„•6†wu¥W#S†V4¶§¦ää–÷dtD'r²¶Uv—Cvc7$f×£”‡“E“g4c%ugFD£„•EgEf÷dcGT†…†¦F%s" ¢&–gRõç¤tvtÔD$æ•—GTÖ”öÇæãF4%%d4§§v•'c‡ƒµ†#V&ã%E¦see¦see„6ÕuGƒ#g#R ¢$wC$FäÄ5“e¦Ô¥5Stcvµ“eWÆ6vDäç2õ„c‚´„%¦Õ—t´¦²ó#cv66Ã¤ä4'$F§'c–gWVçdÕW$v–B ¢'C£Ff†fgg…–UFæ„Õƒe”$7”FdÃ&õV´eV–43…¤b´ÖÕ&õe„Å—G’¶³†—&å7dD%Õtv4ä·–¦F¦•vä2 ¢%d7¦ÓwdÓ”ó‡×£bõ$c–•‡%…T$&‡§væ‡t³gvÂ²¶ÅtCF$¥g…4çF•…"³ÖwG¦34¦ó–Wv6‚ ¢'Ds6$æ´Ut¦–B²öVµ4ä„ÔÖ&GVåcufeU%d„öåGC3F4´g3&eæ£’ò÷eG†ä§••4¶'B²µFcFwUT×³R ¢%&DÓ5G¦öDG•‡õCe£t…‡U%„µ6·C†äw¦GS4æ—…“—S&%GG#—–SSU‡C'Ew¦E$dvÖ‡'µ4tÔ%5r ¢&äGC4Æ–÷F×•¥E$õ£%¦Ò÷f¦¦£'ƒe&s6'†Õ4¦$w‡5FGc6‡s6&‡v‡4$çU$´s&6UvåF‡…õ‚ ¢&#–×”¥7w6¤ft¦cE¥”&„eVV$ÖÕ…×¤&Æeƒ„däv¥#†34•TÄgt”DtfsW7•¦„DCc’³’óvG2¶d÷†5DR ¢'Dw%d¶•–Ô&ÃCF×¤'r·U…•uT%†ÓvÕ¥—e$3vS–Ó&$Ä$æç–¦gTt'–BµsgDäãu6WfÄT¥„†÷5CS–¤r ¢'E4S–s#c–ƒ$5•–”$E3U§CTE„—dÃ2öS–´%DVã3•&¶Äµ§VÅTu§sVFóÕƒs2ö’õvsug&ÖR ¢#&T£&Gg"ö¥g36StUS…§´S4g“F'5“&&£tg„Ub·†¥w‡%'T6v´e'T³GDE—2ö6×¦SD6ÇGG'3" ¢#„d†B÷F4w£Vµ3U†„6Å‡v%&ÔÕc”T¥72¶ã4st×¤¤VÇ–E…‡CböcF4ô‡##vGW¥—5%—Ev×¦WdæÇFFò ¢%Vã#vG'£W33vÓV6ww7f†5GWUf‡–ôÆÂ²¶dõD–µ&tçd¤ÕsWV'554”¤†äE'3'$b²õ‡õ‡¦ÓtôÔb ¢$7…¥W$f—†ô§5&¶$fó4Æç§”Ö”—'#v7'¥Vã”¶Æ3$Ô4$ó3’õ6DöäVtôtEg¶Vfgg&óódv£ ¢%dÕ#ÔGƒS‡w…“†”†ã7§—–VGR³vGS6g#„â¶¦ÃV%c’²öÅ3V6–„¥—Es–u•Tä¦·V……–F–¤Ã#‡dV„r ¢$Çt3GSw5Dwt”VÄåCc–eCeVT†£CgEw&•u†ÓwSb¶gc3e7W†6d†e†twCGUSõs%VDã“†ÖEõ†Vç’ ¢&#•£VÖg'„“V‡UT53fTs†E'e„ö5tT#WWT¶5„ÖWVóE¥§”6TFVvÆÅW$CR¶t–Ãt6×Es”Çu5FƒF—b ¢&¦$3F7‡6ä£D¦–t•”W“d‡“fvbõ”ätDÖEwfÂ´ts6DóG#gwW5%v÷t4¥U”$f—d”3…TCdtS—¥cr ¢$ÕEW$×V–6vDäU“†fó„Ã‡v3wwf'7vE7'$Ç§„7#RöÖ¤æö×3tç¦S5—6ô†ƒFÕ§Vô…GFF×“U“†4ôö¦R ¢'eGD3d#”“&UD–f–ÅS4%df§GC’´ô„FÕ3s$“gw7UC4Ã¶·”Ö6fc’µEV„“$Äæç¢³6'G‡3eEec³’ ¢#““Sw6—uv¥&ó´$$„Fç§4†§‚·#Ese4E§§fä…‡4cW—¤ÄÖw…GDv¥'TÆsFÓƒ%sstDF‡r÷c3r¶f÷”¢ ¢$W–4ôv¥$”dU†ÓU„E4´T×U4å64T–v³fæ“GTÅ3Ä¤”F×¥§W¤Ä74”Ôf”ç¦S5w%g§–ƒFEE”×3%dÂ ¢#e–#G“$§C6U‡vÃecƒ36#e„³F…v#tb·CC7£•6ô´#seeVÄÕwtätöCT´W$5çDu‡tÅSv”R ¢&vôv–Ä¥#¶VöBöW£3‚¶¤&ô¶d6wtT¤¶ôv…¤£u$Ç$6ô6•VÃFFƒv¦¦'ƒGU§”w“Rô£D4·C$t´×%Dòò ¢&÷'s†¤—Vä3—5óu§G75v÷wt#4ô3%DÅW–#u•#E'f¤D•55sS65„g3ss—Vå‡&gfæÆÃSvBós###„vsDUR ¢$õ&VUwgæãf¥5„¶eF&Cc„õ5¶„¦t–ö–tt&v4t†„TÖ¤W„U§…5…gS6&³$´$d7S6gf¦öÔ¦õvÆFÃb ¢#VÅS…G„v¥'Æf¦‡Dv¥'FgS5§G†÷u¥†'5t—4çgE3U—5v&GT…VåD¶ç§t¤åu“TdÓTc6&´ó&'C'%T ¢%”E's†TD²³cFóTE¦c…Fcf&Ç¤v$Ä´t3—†§†ææÃvS'R´µd³#òôôD÷ttDƒ£57#fdTs”—“…’ ¢&ÃƒC%¦w&$Cuƒw$ãgfDö¶Ó3eTc…&Vä&¥V„¥D¤·e&DöÆsSeuµƒwt¤ÄTô„$¤e”&3t§G¦Ft´Ær ¢'5¦öÖ§4…w#'#“t—esf£“†‡¥¶C6õ6¤tC—tÓg…v¢ó…W#SvÇ–Å„væu‡f³“w&Ç7%—6S†å†§BµgDR ¢#•Gc32öGVåƒ3s“†dæ×•–ö–—Esv4ôFsR·uÕW¦´§¦³Tõw&”¶d†å¤u&´Ts6CEsDed¶Ç“Tç§Ô7„vÇ" ¢#„¥U¥6”´ÖTô…dÔdäÖE%—5tÅg”VDu%U†Gfã6%¤D•d³4TÆ×6W$T$TÇ’·d¦³&„Ã’³5ws%ƒsb ¢$å4u•Æ·•c““•%Täsv7Tew%fãR¶g&ÓWV$æç£Tµ6æóUu“‡„†¦‡sD´dFƒTµ6¶õ”äs6'sDTuu¥£$Ä#ä" ¢#6dóeÃdVÂ²÷W%S#‡¥†Ä•…VV$gEw35††¦D´w…6–VC7s6×—GFÔâ³&…T³S3EGFƒvÇTÅ…&¢·Ö’ ¢$DöÆäB³Dsää7”wwD†¦t¤„–F6¤ƒ–÷¦ôd#$ƒ%V%fƒ‡f4eU4µ…6Ä¤5¤£ScFõC”·s5”vg4gdCcW¢ ¢#ƒw—DóSb´C‡$×¤wDsU”B·cÂõeE&t$âös–ô´”F6Ã4‡¦’²¶Dr¶F•‡&ƒF#%¦wf5#uT´&u'dÅvÓ‚ ¢&Fs„DUvU&µ¤egÅ$$4S•#·f'CctÃu—§s„„G“F×¥£Fæ7•%dfç£SFÅd¤cfÃ‡…wUv·£‡’ ¢%D·%4FUTÃ²µ&ó4´f'C#gEtÄt7”Eg”¤„TVåG¶–÷—$$ö•$–Ä6…¤3W”ÖãR÷†GF¤$tÄ×6te•g ¢%&Dã#u§F§ƒC”öÔ„6„ÃS’³sw§¦§6´öevÅ¥‡$ÆÆ“%„ÄfÄ3‡VåCSTÕD$åg—åW&†g„d%‡4dEµV–ÔFt2 ¢$u¤õ3–GVµTVµT&ô'#cEbô4t$§$“d†ÆtDÄ¤ÖƒUWvdCDæÓ%g7§%Dò¶—–ã'†vÄµ•tô´t7'e6¦dÃ ¢"ô£¤´ô…"ô”3“6÷gb÷f×5DT%§V·”“„S‡fd$F„f'$e4ÃótVÃ'ô×3‡E…”&³G†·–¥wE…uv7R ¢"¶c´u–“&g“#CdÃRöçv÷¶US…§&‡fU3„2÷†6'gT‡dä—7“6'c73…†'ƒC†¤æ×£U&Åwe‡’ ¢'$4ä†§W¥—5”Ô”“Cv£wC#wC&¥$–Ä•c$ÇcDÇTVW”Ô¦FÆÕv–Eç†ÔƒcWe§•w¦Ã•‡#—%gS7†÷u¢ ¢%%Fó„ô„CEF³•3Wwe5ƒ4W„ÕDT„F‡vt—wtäF34·—$Å¦$Ä—4óW3uUde$5´¦c†U¦³Vs%g#CFD÷tÄ ¢%c“—E…åFõ¦…4'”–÷—gggc–D&Öw£ef·$¶Ä—µW£‡$¶öÖÆ#–4E„'v4ÖÕ4¥V³•¦·¥§¦”óG¦”ò ¢%•¦vfgf¦ƒ4ÆÇ£D¥'%3•¦ƒtv¥gä†gU„ö6TÔ&ód&¶t$Eä÷Fc$ÖÓE¤5¦'“Uu¥Â¶ä…†Ó”ÄfÓ†¤B ¢&Ås3Wr·D%4ã%†7$d4ôuu5£UE”7†·$6V'¤EwWE—…vv”´Å¢¶F#S6W¦”öÄö¤–Ä÷$–ä76³Tt" ¢'$å‡4F´…¤¦Ó¦µ‡ƒ6GT•wrôD”¤—d"´v„µ†ä'gUv„”´4ä2õ”—vGtÇ–4e¦‡&R³Vg#†³%&DdÆâ ¢%'$3–WeƒctÅ7$÷¦Rõ‡¥E%dfµue¤æT5t†–ÆóGT—•“†ÓF4ô†³6÷”Ö¤–ô´6s•C¶–óå%Tö¥’ ¢'5t÷%g”u”%G—Ww¤e†Ö”ó6g3$„†Dvç£W3'£"³4F†s'fçƒWEw%f¤V&£6'C5CSe¥F$$†§ƒDD&w… ¢##“…wd#&E3E$×µF³T$ÖåG$5“†U–õ„ÃSefÅ%U”u£C†Töfgg7W¥WWT…‡#÷u¤Ó¥UvƒR ¢&¶CdÅ“†vöV†¤fW5tÄcvGS3s—“TÓ4Æ·•ÆÇ“Täö—v´¤5$ÖÕD$$f6UD–¶7U„Ã3–×…“W¢ó3s——Ew$¦‡b ¢%w¤öæG¥'s…„g†7dÃc”†§ƒFDô„&rõ§„Æ“GVfgc$E´¢¶dDDCF4ô…§F³”ò¶fgV…FTv†õ¤u%UwE†'er ¢#E…f%wV³U5WDÅõT×¤Ö¤¤öäF…'3&$å§3&“”vsE“45VÆ–Ó•¦„s–d´†f&eUvdöVÖfTV&ã§F³¢ ¢#Tu–´ƒµT&×U£wFåg2µ&¶ô$%&•t$EuUcFW”¶t…63v¤DdT7WtÕT%uCS—¦ós–eDdTD—ge#wöTâ ¢'µ”%”¤&¶ô6¦³USEc‡tÔV„‡UVD…V´Öç—'†D&·4F&·—'7Rõ†tµ””"÷…—g¦×g&¦ƒvÇ–däv‡”ô'u’ ¢#G“VGVtD¥§33SgDE'&³v6ƒCC…”ãSS7f—…“„×‡vDÒ¶U$÷§3•wCF¤DtE'3$¤c–GS6'FVcÇ•Få‡$fÅB ¢'Dv¥&wVCE…vDõ„öÓ&´35”c–'3–Æ7V•#Svç£S—¤u—§U£ggf¶Ó3vCc•”ä6vô6tSfD÷ƒR¶Tt„ƒ†…‚ ¢##u§F3#U•3#S4µ6åGC6·4ÕtÃTÕ¦Ç£Vw¤¦U¤5VÄÕDÕ–bô„dg•4ÖbôÆ·•‡£5FÓCT•4v„Uƒ’¶VVb ¢&·¤âò²³#7§¶e2¶VdCW£W7ƒ…V·•¥W„FƒtöcS$æ…–¤„g—Wt4W–Dö´tfõEf3d##–#%W7“r ¢'FÓ7†B¶ÆTeD´µc‡võ…5ssS$Gƒ4UtÖÆC–#7–·¶R³„†34VÖdöe–4W’öf¶ƒ†Ó%FgDÖFgDÇbö†…tÕ¥F×b ¢#w”Çv&¶¥sgV„Ätäf¶vG•&ç–öc4‡e—$f†¤„t73s•”£V£ƒ3W–•§#VW”öw¤´³¤3f×cV¤gr´Er ¢%$7„¢´âõDgg%c'†ÄSs57–åfåg¦2õ£ƒõcU‚²´´&—…—Ç—%&W†ãwC#v$æ×”§ô¥¤ôÕcG”´$Öâ ¢%F×¦DöÕtÅggS4ÆÆ§EfóV¦—FDv§#6'Dv´ECwC´×cwC#uD¦·”Æ“GU£B·§w6$T’óƒDÔtC#vGgc&e ¢&æÃ’òõEVÄ¥•…V¦Å7d¶ÅGV´ãCvæ%•&6Gƒsss%†ä§—3&tV¶tô†£C÷%f“4$SF³•–u$’÷£’ö&GS5§r ¢&Ç5§…„õv¥–4ô†'“V7&ódö¤—”Çtæƒ‡UTµTôÔe$µeUs–³DÔ4#eS6ST4æfbó“—ud'fDw$„Ew ¢'E†'C'$æç§¦ö6§V¦ódÔDä·§6gc7u&¶fÔÔD„–¤Æ“GV·–EFÆw2µ”Æ´äS6&$Æ&Ew4Ft5$¦wu”äÖ‡â ¢%svGWFGgDT&„õ&µu£G…“Ew%b²õ„†Ä¥V³†åWfã3uã3f$ç“CBöc3†d‡ƒ•DWt3‡f#5‡&Ã#v7U„² ¢'”Ö¤—”Ö¤–Ã“c•6ôôugr¶÷•&ÓGgWeƒS…§ƒDDg7¦åG3&–ÖGc‡“dÖs'×&”¤Ôöt$tu&DÖ33#eb ¢'¦ÂôFƒ3„f7sSGT¦Ó&dS3R·tÆ´å—¤³tgF¦´¦´‡–tµ…CTÕ3'&c3tEƒ„´ÔudGV3tæÔ7&ÇDõ‡„Då‚ ¢'DöçV‡&$ÇeuDVt£6&¤"ó&ã7¢övtf&&6„7ƒU7–ƒ5‚õgc“#vôG$DÅ„&TCv…uÔ&ds†3„ÅCV·e3Õ‚ ¢$‡#S$†ÄÄ$‡#3SWuVDÇG“EtÃeFç§ãs’·fVç7U…ô´6çÓeU²õÅfUTe†#g$TÃG•… ¢#„¦#uWEtƒe5–bó%#†b²öTD•&'w%f%ôsÔ†“%·f´„GuDôä4Õç„¶f4³gÓ–g'7VgWu#“…Rö´b ¢&¥T”µ6´dÔ4¤õE—Vƒ–'¥“C–Rµ$Õ…&ô´â·d£–S$5#T×S–v–ô¢ócVÇ'—VVöf$ä§TvFW4g6wTg3tÒ ¢%‚µTÅ4$4„ó$U…–•vöÓ&æ³Eó„×¥—‡g´Fµ55w¤„d7w–Ó$%3%–dæó”uô¥e5d·G§DåutÅ„Ffb ¢&tÖµ7ƒfÕ†´“—V–ôÄ×fvfw4Ä$&wu•dÃs†U¥†‡£—3T“’övå–DæTTÆGã3VG6•“ƒFÕV'—¦“7evÒ ¢$&s4÷ÄæW4f£TöWS3…SåG5tv¦dó%vdó3f6ó†7†Ç—7TDF—d'EwD4fdÔ„$Ö¤DÆó4ôÖÖ·vt%”T'2 ¢"öWU4d&V´'…çvæ¶ô„”—§¤45‡5…C'‡¢õÆÃ5ƒsSvç—D7VÆ7“&&2³66ƒ–r³7dõ¥S”Ã•3§b ¢&cdÄÃc–‡‚¶æÕ§fÒ÷¦Ô6”ç¦UƒS6¶—b÷#V%$çg¥ƒ‡ƒ'töä¥W%#†e¢óvFWf‡7D£…dDÆuuV•„—£„3%§b ¢"µtc–´—b´õ“De„†rôBô„Uv6f&dÃ–Töå„³6tBô“'–¤U$#E"´õ–”·'dô$¤äÓu„÷&T#$¤&sæ·6" ¢%G‡CE”§DGfã‡VäEwfå•F¶¦Öt¶fæT$÷µ¦Ç—F4äTRµ„7T6dÄ$fôG¦GT&d÷'tS‡d¥v–F—d6µ£¦R ¢$†ôdöTU%G3D5$ÅäÔt4…vFÄ6W”ÔõdÆ„ôôt#6gEEfuD¥T—”÷3f$VÆ5•¤wcT¤2·ƒw†vå¦æÕÔ ¢&Äµ%TT5G64v#“F’õ†Ä56ç”…Fódõ&µtÃGG„Õ4Ó„ge#v&3v³&%¤u%e¤¥6ÆU#4f•'vÆ#µv§t'¦$ôä’ ¢$¦UT%–³4fåFVäGDwV“7fÓd‡ss“&Ö6õTtD&s2õU£Ew$µ„#„Uf§e”&VÃ&ä¤µt%734’µF'G…#FƒV’ ¢%64eV´„„”SUeô&V³GsfÅt§%deu'†7g—FD6ô5'#fW–Ebò÷„ç6õ„tt&sä$£D¶µ—„Òõ¤d2õ‚ ¢'6·“·74¦¥Vã”†ƒVDT§Ö3“D7†ô‡“‚÷Ö…£&¥ôT„D7†vgc6†U‚ó•5•S%6$¥6VT’óu3utôTôB ¢$&s†÷„–”4ôÃTæ•3$çfeWD&¥DÓä6u4Ö&sV7TtD&säÓuôTtD&s£&¥ôTtD&ó¤äv¥ôTtB ¢'††¶äv¥ôT†¤Däv¥ô„tt&säv¥ô„tt&säv¥ôTôD&säv–6õTtD&säÓuôTtD&s£&¥ ¢&ôTtD&ó¤äv¥ôTtD&ó¤äv¥ôTtG††¶äv¥ôT†¤Däv¥ô„tt&säv¥ôTôD&säv–6õTtD&s ¢$äÓuôTtD&säÓuôTtD&s£&¥ôTtD&ó¤äv¥ôTtG††¶äv¥ôT†¤Däv¥ô„tt&säv¥ô„tr ¢$&säv¥ôTôD&säv–6õTtD&säÓuôTtD&s£&¥ôTtD&ó¤äv¥ôTtG††¶äv¥ôTtG††¶äv¥ ¢&ôT†¤Däv¥„å§–‡–ôtôÓ4åd%¦ÆÕe¢öö7d¶¶Õ3ƒUe%¤V³e†ÕFtDetdµu&gfçƒ—Võ¤‡cS5G&´tB ¢&‡&5sdvÄ65•”–e#7'eDÔ×–”µÄ‚õfÇT…Dc"¶Ò÷#tSed&wu„âó6ót”c²õ§E$&Vç·”e”´e4”–6Â ¢$¤5Ô†§ƒC–W%b÷•¥ƒs‚µ333’·•¥e#t†w‡ƒ’öäE'VÔ¦”–ÔSv„$3Tµ„£†×'Å7E†ææÖ'C"öcwGS2 ¢#s”¶Å3•e÷Æ$TUgƒvG“U—G“‡¤ÒôWU„¦v%GEwe††wu§6Ó6'Fã—3$&ó•†5•–t4ÆÓWU%–ãTõF´4”§r ¢#‚¶$å&ófdÄ¤£gµWd4·¥“&GW%Wf&Æ&stôCfDÖDó5–´äd4•4¦gvÇ%c#ugõ‚÷¥6“v”õFãR ¢'b²´–âµDÕrõ§6Õ…G³få“E&Ô¦•–å#äF¶U——„£f§ƒC†Tär¶Gtôå$&¶¢µ6·¢²´ôT†çVbóF7%6D´R ¢$5$Ó&$æ†w3–â³'•&r²ögbò÷GC““fVçä´d&wv2÷tæu†ö¦w„õTevt$¥%STW&´¦vvsÓÒ ¢  ¦FVbö&æµö–Öu÷F‚‚’Óâ7G# ¢""$&6ScN88~8+>8;Î888~8nKˆi˜.89^8*8*N8:¾8¾i»8ŞX{®8~8898+8).‹ùN8’"" ¢–×÷'B&6ScBÂFV×f–ÆRÂ†6†Æ– ¢öF—"ÒFV×f–ÆRævWGFV×F—"‚¢÷F‚Ò÷2çF‚æ¦ö–â…öF—"Â'¦æ¶õö&æµ÷6V7F–öâçær"¢–bæ÷B÷2çF‚æW†—7G2…÷F‚“ ¢v—F‚÷Vâ…÷F‚Â'v""’2öc ¢öbçw&—FR†&6ScBæ#cFFV6öFR…ô$äµõ4T5D”ôåô#cB’¢&WGW&â÷F€ ¤õD•DÄRÒ.jè¾š¹Š‹Îiˆîi»‚yIşh‰88N8;Î8:²   ¦FVb÷6WGWöföçB‚“ ¢vÆö&ÂôdôåEõ$Tt•5DU$T@¢–bæ÷BôdôåEõ$Tt•5DU$TC ¢FfÖWG&–72ç&Vv—7FW$föçB…EDföçB‚$¥"ÂôdôåEô¥õD‚’¢ôdôåEõ$Tt•5DU$TBÒG'VP  ¦FVbö¦öFFR†C¢FFR’Óâ7G# ¢""&FFR(i"8Ã##b[›BbiÈ‚Riz^8Ş[Ú.[ÈşûÈƒj8îiÈ8;¾iz^8şXXš
Ş8+89®8;Î8+8s.j[˜^ûÈ’"" ¢ÒÒb"¶BæÖöçF‡Ò"–bBæÖöçF‚ÂVÇ6R7G"†BæÖöçF‚¢F’Òb"¶BæF—Ò"–bBæF’ÂVÇ6R7G"†BæF’¢&WGW&âb'¶Bç–V'Ò[›B¶×ÒiÈ‚¶F—ÒizR   ¢2)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)H)@(ŒAƒRš"@(ŒƒŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠR ()‘•˜•¹•É…Ñ•}Á‘˜¡‘…Ñ„è‘¥Ğ¤€´ø‰åÑ•Ìè(€€€}Í•ÑÕÁ}™½¹Ğ ¤(€€€‰Õ˜€ô¥¼¹	åÑ•Í%< ¤(€€€Œ€ôÉ±}…¹Ù…Ì¹…¹Ù…Ì¡‰Õ˜°Á…•Í¥é”õĞ¤(€€€}‘É…İ}•ÉÑ¥™¥…Ñ”¡Œ°‘…Ñ„¤(€€€Œ¹Í…Ù” ¤(€€€‰Õ˜¹Í••¬ À¤(€€€É•ÑÕÉ¸‰Õ˜¹É•… ¤(()‘•˜}‘É…İ}•ÉÑ¥™¥…Ñ”¡Œ°‘…Ñ„è‘¥Ğ¤è(€€€(€ô€‰)@ˆ€€€Œ%A•á5¥¹¡¼ƒŠPƒ–:šr³¿–£
·
ç#O»W
§Ï ((€€€€ŒƒW
§¯#Şk–æ¾ò#–:šr°èƒ–£Şh€À¸È×¾ò$(€€€Œ¹Í•Ñ1¥¹•]¥‘Ñ  À¸ÈÔ¤((€€€€ŒƒŠRŠR €Ä¸ƒcğƒŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠR (€€€€Œƒ–:šr³–ºšâ°è€‹šº/¦®c¢¢óšb;šnàˆàôàÀ°äôàÀÌ¸Ô°Í¥é”ôÄÔ(€€€Œ¹Í•Ñ½¹Ğ¡(°€ÄÔ¤(€€€Œ¹‘É…İMÑÉ¥¹œ àÀ°€àÀÌ°€‹šº/¦®c¢¢óšb;šnàˆ¤((€€€€Œƒ–:šr³–ºšâ°è€‰=U9P	19IQ%%QˆàôÈĞÔ°äôàÀÌ°Í¥é”ôÄÔ€€€Œ¹Í•Ñ½¹Ğ¡(°€ÄÔ¤(€€€Œ¹‘É…İMÑÉ¥¹œ ÈĞÔ°€àÀÌ°€‰=U9P	19IQ%%Qˆ¤((€€€€Œƒ–:šr³–ºšâ°è€‹–B3šZ»
¸¸¸¸ˆàôÌØĞ°äôÜàä¸Ô°Í¥é”ôÄÀ(€€€Œ¹Í•Ñ½¹Ğ¡(°€ÄÀ¤(€€€Œ¹‘É…İMÑÉ¥¹œ ÌØĞ°€Üàä°€‹–B3šZ»
»¾òG¦kfë¢†3»–²³¾òG–>Üˆ¤((€€€€Œƒ–:šr³–ºšâ°è€‰Q¡¥Ì¥ÌÑ¡”€ÅÍĞ½Áä¸¸¸ˆàôÌÈä¸ÀÌ°äôÜÜĞ¸Ô°Í¥é”ôÄÀ(€€€Œ¹‘É…İMÑÉ¥¹œ ÌÈä°€ÜÜĞ°€‰Q¡¥Ì¥ÌÑ¡”€ÅÍĞ½Áä½˜€Ä‘ÕÁ±¥…Ñ”¥ÍÍÕ•¸ˆ¤((€€€€Œƒ–:šr³–ºšâ°è€‹š2–ºk–>–êœˆàôÜÔ°äôÜÔä¸Ô°Í¥é”ôÄÀ(€€€Œ¹‘É…İMÑÉ¥¹œ ÜÔ°€ÜÔä°€‹š2–ºk–>–êœˆ¤((€€€€Œƒ–:šr³–ºšâ°è€ˆÄƒëó
àˆàôĞÜä¸ÄÈ°äôÜÔä¸Ô°Í¥é”ôÄÀ(€€€Œ¹‘É…İMÑÉ¥¹œ ĞÜä°€ÜÔä°€ˆÄƒkó
àˆ¤((€€€€ŒƒŠRŠR €È¸ƒfë¢†3š^—¾ò#–>Ï–Ó¾ò'ŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠR (€€€€Œƒ–:šr³–ºšâ°èàôĞÄà¸Èà°äôÜÈä¸Ô°Í¥é”ôÄÀ(€€€Œ¹‘É…İMÑÉ¥¹œ ĞÄà°€ÜÈä°}©…}‘…Ñ”¡‘…Ñ…l‰¥ÍÍÕ•}‘…Ñ”‰t¤¤((€€€€ŒƒŠRŠR €Ì¸ƒ’ö?š&ïšÂ?–B7¾ò#–Ş›¾ò'ŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠRŠR (€€€€Œƒ–:šr³–ºšâ°èƒ¦×’úÿV«–>ÜàôÜÔ°äôÜÄÌ¸ĞÌ°Í¥é”ôÄÀ°ƒ¢†3¦ZL€ÄÕÁĞ(€€€Œ¹‘É…İMÑÉ¥¹œ ÜÔ°€ÜÄÌ°‘…Ñ…l‰Á½ÍÑ…±}½‘”‰t¤((€€€…‘‘É}ä€ô€Øäà(€€€™½È±¸¥¸m‘…Ñ„¹•Ğ ‰…‘‘É•ÍÌÄˆ°€ˆˆ¤°‘…Ñ„¹•Ğ ‰…‘‘É•ÍÍˆˆ°€ˆˆ¤°‘…Ñ„¹•Ğ¢address3", "")]:
        if ln and ln.strip():
            c.drawString(75, addr_y, ln.strip())
        addr_y -= 15  # ç©ºè¡Œã§ã‚‚è¡Œé€ã‚Šï¼ˆæ›¸å¼å›ºå®šãƒ¬ã‚¤ã‚¢ã‚¦ãƒˆï¼‰

    # åŸæœ¬å®Ÿæ¸¬: æ°å x=75, y=653.43ï¼ˆã‚¢ãƒ‰ãƒ¬ã‚¹è¡Œæ•°ã«é–¢ã‚ã‚‰ãšå›ºå®šï¼‰
    c.drawString(75, 653, data["name"] + "ã€€æ§˜")

    # â”€â”€ 4. åŒºåˆ‡ã‚Šç·š â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: (75,637)â†’(495,637), lw=0.25
    c.setLineWidth(0.25)
    c.line(75, 637, 495, 637)

    # â”€â”€ 5. è¨¼æ˜æ–‡ï¼ˆå·¦ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: x=89.28, y=610.02, size=10
    c.setFont(FJ, 10)
    c.drawString(8=, 610, f"ã€€{_ja_date(data['cert_date'])}ç¾åœ¨ã®è²´æ–¹ã”åç¾©")

    # åŸæœ¬å®Ÿæ¸¬: x=85, y=594.76
    c.drawString(85, 594, "ä¸‹è¨˜å‹˜å®šæ®‹é«˜ã«ã¤ã„ã¦ç›¸é•ãªã„ã“ã¨ã‚’è¨¼æ˜")

    # åŸæœ¬å®Ÿæ¸¬: x=85, y=580.02
    c.drawString(85, 580, "ã„ãŸã—ã¾ã™ã€‚")

    # è‹±èªè¨¼æ˜æ–‡: x=85, y=564.42/549.42/534.42, size=7
    c.setFont(FJ, 7)
    c.drawString(85, 564, "THIS IS TO CERTIFY THAT THE BALANCE OF")
    c.drawString(85, 949, "YOUR ACCOUNT(S) WITH MUFG Bank SHOW(S)")
    c.drawString(85, 534, "THE AMOUNT(S) INDICATED BELOW.")

    # â”€â”€ 6. éŠ€è¡Œåï¼‹å°å½±ï¼ˆåŸæœ¬PDFã‹ã‚‰ã‚¯ãƒ­ãƒƒãƒ—ã—ãŸç”»åƒã‚’ãã®ã¾ã¾è²¼ä»˜ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬ bbox: x=288ï½542, y=543ï½622ï¼ˆPDFåº•åŸºæº–ï¼‰â†’ width=254pt, height=79pt
    c.drawImage(_bank_img_path(), 288, 543, width=254, height=79, mask="auto")
    c.setLineWidth(0.25)

    # ãŠå–å¼•åº—ãƒ»é›»è©±
    # åŸæœ¬å®Ÿæ¸¬: "ãŠå–å¼•åº— è‰æ´¥ã€€æ”¯åº—" x=280, y=534.5, size=10
    c.setFont(FJ, 10)
    c.drawString(280, 534, f"ãŠå–å¼•åº—ã€€{data.get('branch', '')}ã€€æ”¯åº—")

    # åŸæœ¬å®Ÿæ¸¬: 'é›»'(280,519.5) 'è©± 077...'(290,519.5) â†’ é€£ç¶šæç”»
    c.drawString(280, 519, "é›»")
    c.drawString(290, 519, f"è©±ã€€{data.get('phone', '')}")

    # â”€â”€ 7. æ®‹é«˜ãƒ†ãƒ¼ãƒ–ãƒ« â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _draw_table(c, data, FJ)

    # â”€â”€ 8. ãƒ•ãƒƒã‚¿ãƒ¼ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: x=65, y=45/39/33/27, size=6
    c.setFont(FJ, 6)
    notes = [
        "ãƒ»ã“ã®è¨¼æ˜æ›¸ã®é‡‘é¡ã¯è¨‚æ­£ã„ãŸã—ã¾ã›ã‚“ã€‚",
        "ãƒ»é‡‘é¡ã¯ã€è¨¼æ˜æ—¥ç¾åœ¨ã®å…ƒå¸³æœ€çµ‚æ®‹é«˜ã‚’è¡¨ã‚ã—æ±ºæ¸ˆæœªç¢ºèªã®è¨¼åˆ¸é¡ã‚’å«ã‚“ã§ã„ã‚‹ã“ã¨ãŒã‚ã‚Šã¾ã™ã€‚"
        "ã“ã®å ´åˆã¯ãã®é‡‘é¡ã‚’ï½¢(å†…æ±ºæ¸ˆæœªç¢ºèªè¨¼åˆ¸é¡)ï½£ã«è¡¨ç¤ºã—ã¾ã™ã€‚",
        "ãƒ»ï½¢å½“åº§è²¸è¶Š(ç·åˆ)ï½£ã«ã¯ã€æ™®é€šé é‡‘è²¸è¶Šå‹ã®ã‚«ãƒ¼ãƒ‰ãƒ­ãƒ¼ãƒ³ã”åˆ©ç”¨é¡ã‚‚å«ã¾ã‚Œã¾ã™ã€‚",
        "ãƒ»å£åº§ç•ªå·æ¬„ã¯ã€å£åº§æŒ‡å®šã®ã”ä¾é ¼ã®å ´åˆã®ã¿è¡¨ç¤ºã—ã¾ã™ã€‚",
    ]
    fy = 45
    for note in notes:
        c.drawString(65, fy, note)
        fy -= 6


def _draw_table(c, data: dict, FJ: str):
    """
    æ®‹é«˜ãƒ†ãƒ¼ãƒ–ãƒ«ã‚’æç”»ã™ã‚‹
    åŸæœ¬ pdfminer å®Ÿæ¸¬å€¤ã«å®Œå…¨æº–æ‹ 
    å…¨ç·š: lw=0.25, å®Ÿç·šï¼ˆsetDash([])ï¼‰
    """
    # â”€â”€ åˆ—å¢ƒç•Œï¼ˆx åº§æ¨™ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: X1=65, X2=205, X3=290, X4=410, X5=530
    X1, X2, X3, X4, X5 = 65, 205, 290, 410, 530
    TW = X5 - X1  # = 465

    # â”€â”€ è¡Œã® y åº§æ¨™ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    top_y   = 502   # ãƒ†ãƒ¼ãƒ–ãƒ«ä¸Šç«¯
    hdr_bot = 472   # ãƒ˜ãƒƒãƒ€ãƒ¼ä¸‹ç«¯ / ãƒ‡ãƒ¼ã‚¿è¡Œä¸Šç«¯
    bot_y   = 52    # ãƒ†ãƒ¼ãƒ–ãƒ«ä¸‹ç«¯
    ROW_H   = 30    # å…¨è¡Œã®é«˜ã•

    c.setDash([])         # å®Ÿç·šï¼ˆå¿…ãšæœ€åˆã«ãƒªã‚»ãƒƒãƒˆï¼‰
    c.setLineWidth(0.25)  # åŸæœ¬: å…¨ç·š lw=0.25

    # â”€â”€ å¤–æ  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.rect(X1, bot_y, TW, top_y - bot_y)

    # â”€â”€ ä¸»è¦ç¸¦åŒºåˆ‡ã‚Šç·šï¼ˆãƒ†ãƒ¼ãƒ–ãƒ«å…¨é«˜ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: x=205, 290, 410 ãã‚Œãã‚Œ y=52ã€œy=502
    for cx in [X2, X3, X4]:
        c.line(cx, bot_y, cx, top_y)

    # â”€â”€ æ°´å¹³åŒºåˆ‡ã‚Šç·šï¼ˆhdr_bot ã‹ã‚‰ ROW_H æ¯ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: y=472, 442, 412, ..., 82 (x=65ã€œ530)
    y = hdr_bot
    while y > bot_y:
        c.line(X1, y, X5, y)
        y -= ROW_H

    # â”€â”€ æ•°å­—ã‚°ãƒªãƒƒãƒ‰ç¸¦ç·šï¼ˆå®Ÿç·šã€lw=0.25ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬ï¼ˆå…¨ã¦ y=52ã€œy=472ï¼‰:
    #   æ®‹é«˜åˆ— (X3ã€œX4): x=317.5, 335.5, 354.5, 372.5, 391.5
    #   è¨¼åˆ¸é¡åˆ— (X4ã€œX5): x=437.5, 455.5, 474.5, 492.5, 511.5
    for gx in [317.5, 335.5, 354.5, 372.5, 391.5,
               437.5, 455.5, 474.5, 492.5, 511.5]:
        c.line(gx, bot_y, gx, hdr_bot)

    # â”€â”€ ãƒ˜ãƒƒãƒ€ãƒ¼ãƒ†ã‚­ã‚¹ãƒˆ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: x=X+1ï¼ˆX1+1=66, X2+1=206, X3+1=291, X4+1=411ï¼‰
    c.setFont(FJ, 7)
    c.drawString(X1 + 1, 491, "å‹˜å®š")
    c.drawString(X1 + 1, 480, "ACCOUNT")
    c.drawString(X2 + 1, 491, "å£åº§ç•ªå·")
    c.drawString(X2 + 1, 480, "ACCOUNT No.")
    c.drawString(X3 + 1, 4=1, "æ®‹é«˜")
    c.drawString(X3 + 1, 480, "BALANCE")
    c.drawString(X4 + 1, 4=1, "(å†…æ±ºæ¸ˆæœªç¢ºèªè¨¼åˆ¸é¡)")
    c.setFont(FJ, 6)
    c.drawString(X4 + 1, 481, "(BILLS OR CHECKS FOR COLLECTION)")

    # â”€â”€ æ™®é€šé é‡‘è¡Œ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬:
    #   "æ™®ã€€é€šã€€é ã€€é‡‘" x=75 (=X1+10), y=444.5
    #   å£åº§ç•ªå·        x=227.87, y=444.5
    #   æ®‹é«˜            x=360.57 (å³ç«¯ X4=410 ã«å³æƒãˆ)
    #   Â¥0              x=517.64 (å³ç«¯ X5=530 ã«å³æƒãˆ)
    c.setFont(FJ, 10)
    c.drawString(X1 + 10, 444, "æ™®ã€€é€šã€€é ã€€é‡‘")
    c.drawString(228, 444, data["account_no"])
    c.drawRightString(X4, 444, f'Â¥{int(data["balance"])}')
    c.drawRightString(X5, 444, "Â¥0")

    # â”€â”€ ä»¥ä¸‹ä½™ç™½ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # åŸæœ¬å®Ÿæ¸¬: x=145, y=414.5
    c.drawString(145, 414, "ä»¥ä¸‹ä½™ç™½")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Streamlit UI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

st.title("ğŸ¦ " + APP_TITLE)
st.caption("ä¸‰è±UFJéŠ€è¡Œå½¢å¼ã®æ®‹é«˜è¨¼æ˜æ›¸PDFã‚’ç”Ÿæˆã—ã¾ã™")
st.markdown("---")

# â”€â”€ ãƒ©ãƒ³ãƒ€ãƒ åˆæœŸå€¤ï¼ˆã‚»ãƒƒã‚·ãƒ§ãƒ³å†…ã§å›ºå®šï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if "rnd_acct" not in st.session_state:
    st.session_state["rnd_acct"] = str(random.randint(1000000, 9999999))
if "rnd_balance" not in st.session_state:
    st.session_state["rnd_balance"] = random.randint(1000000, 4000000)
if "rnd_cert_offset" not in st.session_state:
    st.session_state["rnd_cert_offset"] = random.randint(1, 3)

# â”€â”€ â‘  å®›å…ˆæƒ…å ±ï¼ˆå·¦å´ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("â‘  å®›å…ˆæƒ…å ±ï¼ˆå·¦å´ï¼‰")

col_p, col_n = st.columns([1, 1])
with col_p:
    postal = st.text_input("éƒµä¾¿ç•ªå·ï¼ˆå…¨è§’ï¼‰", placeholder="ä¾‹ï¼‰ï¼‘ï¼ï¼‘ï¼ï¼ï¼ï¼ï¼‘")
with col_n:
    name = st.text_input("æ°åï¼ˆãƒ•ãƒ«ãƒãƒ¼ãƒ ï¼‰", placeholder="ä¾‹ï¼‰ç”°ä¸­ã€€å¤ªéƒ")

addr1 = st.text_input(
    "ä½æ‰€â‘ ï¼ˆéƒ½é“åºœçœŒãƒ»å¸‚åŒºç”ºæ‘ï¼‰",
    placeholder="ä¾‹ï¼‰æ±äº¬éƒ½ã€€æ–°å®¿åŒº",
)
addr2 = st.text_input(
    "ä½æ‰€â‘¡ï¼ˆç•ªåœ°ï¼‰",
    placeholder="ä¾‹ï¼‰è¥¿æ–°å®¿ã€€ã€€ï¼‘ï¼ï¼‘ï¼ï¼‘",
)
addr3 = st.text_input(
    "ä½æ‰€â‘¢ï¼ˆå»ºç‰©åãƒ»éƒ¨å±‹ç•ªå·ãªã©ï¼‰",
    placeholder="ä¾‹ï¼‰æ–°å®¿ãƒãƒ³ã‚·ãƒ§ãƒ³ï¼‘ï¼ï¼‘",
)

st.markdown("---")

# â”€â”€ â‘¡ ç™ºè¡Œæ—¥ï¼ˆå³ä¸Šï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("â‘¡ ç™ºè¡Œæ—¥ï¼ˆå³ä¸Šï¼‰")
today = date.today()
issue_date = st.date_input("ç™ºè¡Œæ—¥", value=today)
if issue_date is None:
    issue_date = today

st.markdown("---")

# â”€â”€ â‘¢ è¨¼æ˜å†…å®¹ï¼ˆä¸­å¤®ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("â‘¢ è¨¼æ˜å†…å®¹ï¼ˆä¸­å¤®ï¼‰")
cert_date = st.date_input(
    "è¨¼æ˜æ—¥ï¼ˆæ®‹é«˜ã®åŸºæº–æ—¥ï¼‰",
    value=issue_date - timedelta(days=st.session_state["rnd_cert_offset"]),
)

col_a, col_b = st.columns([1, 1])
with col_a:
    acct_no = st.text_input("å£åº§ç•ªå·", value=st.session_state["rnd_acct"], placeholder="ä¾‹ï¼‰0265071")
with col_b:
    balance = st.number_input("æ®‹é«˜ï¼ˆå††ï¼‰", min_value=0, value=st.session_state["rnd_balance"], step=1, format="%d")

st.markdown("---")

# â”€â”€ â‘£ ãŠå–å¼•åº—æƒ…å ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("â‘£ ãŠå–å¼•åº—æƒ…å ±ï¼ˆå³å´ï¼‰")
col_br, col_pa = st.columns([1, 1])
with col_br:
    branch = st.text_input("æ”¯åº—å", placeholder="ä¾‹ï¼‰è‰æ´¥")
with col_pa:
    phone = st.text_input("é›»è©±ç•ªå·", placeholder="ä¾‹ï¼‰077(563)8811")

st.markdown("---")

# â”€â”€ ç”Ÿæˆãƒœã‚¿ãƒ³â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if st.button("ğŸ“„ã€€æ®‹é«˜è¨¼æ˜æ›¸PDFã‚’ç”Ÿæˆã™ã‚‹", use_container_width=True, type="primary"):
    errs = []
    if not postal.strip():   errs.append("éƒµä¾¿ç•ªå·ã‚’å…¥åŠ›ã—ã¦ãã ã•ã„ã€‚")
    if not name.strip():     errs.append("æ°åã‚’å…¥åŠ›ã—ã¦ãã ã•ã„ã€‚")
    if not addr1.strip():    errs.append("ä½æ‰€â‘ ã‚’å…¥åŠ›ã—ã¦ãã ã•ã„ã€‚")
    if not acct_no.strip():  errs.append("å£åº§ç•ªå·ã‚’å…¥åŠ›ã—ã¦ãã ã•ã„ã€‚")
    for e in errs:
        st.error(e)

    if not errs:
        with st.spinner("PDFã‚’ç”Ÿæˆä¸­â€¦"):
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

        st.success("âœ… ç”Ÿæˆå®Œäº†ï¼")

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("æ°å", name.strip())
        mc2.metric("å£åº§ç•ªå·", acct_no.strip())
        mc3.metric("æ®‹é«˜", f"Â¥{int(balance)}")

        safe = name.strip().replace(" ", "_").replace("ã€€", "_")
        fname = f"zanko_{issue_date.strftime('%Y%m%d')}_{safe}.pdf"
        st.download_button(
            "â¬‡ï¸ã€€PDFã‚’ãƒ€ã‚¦ãƒ³ãƒ­ãƒ¼ãƒ‰",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )
    )

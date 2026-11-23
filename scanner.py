import sys
import time
import json
import sqlite3
import traceback
import numpy as np
import pandas as pd
import requests as req
import os
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ======================================================================
# ⚙️ GENEL AYARLAR VE GÜVENLİ SABİTLER
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")

BATCH_SIZE = 25
DELAY_BETWEEN_BATCHES = 5

BIST_TICKERS = [
    "AEFES","AGHOL","AKBNK","AKSA","AKSEN","ALARK","ALFAS","ALTNY","ANSGR","ARCLK","ASELS","ASTOR","AVPGY","BALSU","BERA","BIMAS","BINHO","BRSAN","BRYAT","BSOKE","BTCIM","CANTE","CCOLA","CIMSA","CLEBI","CWENE","DOAS","DOHOL","EFOR","EGEEN","EKGYO","ENERY","ENJSA","ENKAI","EREGL","EUPWR","FENER","FROTO","GARAN","GENIL","GESAN","GLRMK","GRSEL","GRTHO","GSRAY","GUBRF","HALKB","HEKTS","IEYHO","TRENJ","ISCTR","ISMEN","KCAER","KCHOL","KONTR","TRMET","TRALT","KRDMD","KUYAS","LMKDC","MAGEN","MAVI","MGROS","MIATK","MPARK","OBAMS","ODAS","OTKAR","OYAKC","PETKM","PGSUS","RALYH","REEDR","SAHOL","SASA","SISE","SKBNK","SMRTG","SOKM","TABGD","TAVHL","TCELL","THYAO","TKFEN","TOASO","TSKB","TTKOM","TTRAK","TUPRS","TUREX","TURSG","ULKER","VAKBN","VESTL","YEOTK","YKBNK","ZOREN","A1CAP","A1YEN","ACSEL","ADEL","ADESE","ADGYO","AFYON","AGESA","AGROT","AGYO","AHGAZ","AHSGY","AKCNS","AKENR","AKFGY","AKFIS","AKFYE","AKGRT","AKMGY","AKSGY","AKSUE","AKYHO","ALBRK","ALCAR","ALCTL","ALGYO","ALKA","ALKIM","ALVES","ANGEN","ANHYT","ARASE","ARDYZ","ARENA","ARMGD","ARSAN","ARTMS","ARZUM","ASGYO","ASUZU","ATAGY","ATAKP","ATATP","ATEKS","ATLAS","ATSYH","AVGYO","AVHOL","AVOD","AVTUR","AYCES","AYDEM","AYEN","AYES","AYGAZ","AZTEK","BAGFS","BAHKM","BAKAB","BALAT","BANVT","BARMA","BASCM","BASGZ","BAYRK","BEGYO","BESLR","BEYAZ","BFREN","BIENY","BIGCH","BINBN","BIOEN","BIZIM","BJKAS","BLCYT","BMSCH","BMSTL","BNTAS","BOBET","BORLS","BORSK","BOSSA","BRISA","BRKO","BRKSN","BRKVY","BRLSM","BRMEN","BUCIM","BULGS","BURCE","BURVA","BVSAN","BYDNR","CASA","CATES","CELHA","CEMAS","CEMTS","CEMZY","CEOEM","CGCAM","CMBTN","CMENT","CONSE","COSMO","CRDFA","CRFSA","CUSAN","CVKMD","DAGI","DAPGM","DARDL","DCTTR","DENGE","DERHL","DERIM","DESA","DESPC","DEVA","DGATE","DGGYO","DGNMO","DIRIT","DITAS","DMRGD","DMSAS","DNISI","BIGTK","DOCO","DOFER","DOGUB","DOKTA","DURDO","DURKN","DYOBY","DZGYO","EBEBK","ECILC","ECZYT","EDATA","EDIP","EGEGY","EGEPO","EGGUB","EGPRO","EGSER","EKIZ","EKOS","EKSUN","ELITE","EMKEL","EMNIS","ENDAE","ENSRI","ENTRA","EPLAS","ERBOS","ERCB","ERSU","ESCAR","ESCOM","ESEN","ETILR","ETYAT","EUHOL","EUKYO","EUREN","EUYO","EYGYO","FADE","FLAP","FMIZP","FONET","FORMT","FORTE","FRIGO","FZLGY","GARFA","GEDIK","GEDZA","GENTS","GEREL","GIPTA","GLBMD","GLCVY","GLRYH","GLYHO","GMTAS","GOKNR","GOLTS","GOODY","GOZDE","GRNYO","GSDDE","GSDHO","GWIND","GZNMI","HATEK","HATSN","HDFGS","HKTM","HLGYO","HOROZ","HRKET","HTTBT","HUBVC","HUNER","HURGZ","ICBCT","ICUGS","IDGYO","IHAAS","IHEVA","IHGZT","IHLAS","IHLGM","IHYAY","IMASM","INDES","INFO","INGRM","INTEK","INTEM","INVEO","INVES","ISATR","ISBIR","ISBTR","ISDMR","ISFIN","ISGSY","ISGYO","ISKPL","ISKUR","ISSEN","ISYAT","IZENR","IZFAS","IZINV","IZMDC","JANTS","KAPLM","KAREL","KARSN","KARTN","KATMR","KAYSE","KBORU","KENT","KERVN","KFEIN","KGYO","KIMMR","KLGYO","KLKIM","KLMSN","KLNMA","KLRHO","KLSER","KLSYN","KLYPV","KMPUR","KNFRT","KOCMT","KONKA","KONYA","KOPOL","KORDS","KOTON","KRDMA","KRDMB","KRGYO","KRONT","KRPLS","KRSTL","KRTEK","KRVGD","KSTUR","KTSKR","KUTPO","KUVVA","KZBGY","LIDER","LIDFA","LILAK","LINK","LKMNH","LOGO","LRSHO","LUKSK","LYDHO","LYDYE","MAALT","MACKO","MAKIM","MAKTK","MARBL","MEDTR","MEGAP","MEGMT","MEKAG","MEPET","MERCN","MERIT","MERKO","METRO","MHRGY","MMCAS","MNDRS","MNDTR","MOBTL","MOGAN","MOPAS","MRGYO","MRSHL","MSGYO","MTRKS","MTRYO","MZHLD","NATEN","NETAS","NIBAS","NTGAZ","NTHOL","NUGYO","NUHCM","OBASE","OFSYM","ONCSM","ONRYT","OPK30","OPX30","ORCAY","ORGE","ORMA","OSMEN","OSTIM","OTTO","OYAYO","OYLUM","OYYAT","OZGYO","OZKGY","OZRDN","OZSUB","OZYSR","PAGYO","PAMEL","PAPIL","PARSN","PATEK","PCILT","PENGD","PENTA","PETUN","PINSU","PKART","PKENT","PLTUR","PNLSN","PNSUT","POLHO","POLTK","PRDGS","PRKAB","PRKME","PRZMA","PSDTC","PSGYO","QNBFK","QNBTR","QTEMZ","QUAGR","RAYSG","RGYAS","RNPOL","RODRG","RTALB","RUBNS","RUZYE","RYGYO","RYSAS","SAFKR","SAMAT","SANEL","SANFM","SANKO","SARKY","SAYAS","SDTTR","SEGMN","SEGYO","SEKFK","SEKUR","SELEC","SELVA","SERNT","SEYKM","SILVR","SKTAS","SKYMD","SMART","SMRVA","SNGYO","SNICA","GATEG","SNPAM","SODSN","SOKE","SONME","SRVGY","SUMAS","SUNTK","SURGY","SUWEN","TARKM","TATEN","TATGD","TBORG","TCKRC","TDGYO","TEKTU","TEZOL","TGSAS","TKNSA","TLMAN","TMSN","TNZTP","TRCAS","TRGYO","TRILC","TSGYO","TSPOR","TUCLK","TUKAS","TURGG","UFUK","ULAS","ULUFA","ULUSE","ULUUN","UNLU","USAK","USDTR","VAKFN","VAKKO","VANGD","VBTYZ","VERTU","VERUS","VESBE","VKFYO","VKGYO","VKING","VRGYO","VSNMD","YAPRK","YATAS","YAYLA","YBTAS","YESIL","YGGYO","YIGIT","YKSLN","YONGA","YUNSA","YYAPI","YYLGD","ZEDUR","ZRGYO"
]
BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

# ======================================================================
# 🗄️ SQLITE TEKRAR ÖNLEME (HAFIZA) YÖNETİCİSİ
# ======================================================================
def init_db():
    conn = sqlite3.connect('bot_signals.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_signals (
            ticker TEXT,
            strategy TEXT,
            signal_date TEXT,
            PRIMARY KEY (ticker, strategy, signal_date)
        )
    ''')
    conn.commit()
    conn.close()

def signal_already_sent(ticker: str, strategy: str) -> bool:
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('bot_signals.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM sent_signals 
        WHERE ticker = ? AND strategy = ? AND signal_date = ?
    ''', (ticker, strategy, today))
    exists = cursor.fetchone()
    conn.close()
    return exists is not None

def mark_signal_sent(ticker: str, strategy: str):
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('bot_signals.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO sent_signals (ticker, strategy, signal_date)
        VALUES (?, ?, ?)
    ''', (ticker, strategy, today))
    conn.commit()
    conn.close()

# ======================================================================
# 📩 TELEGRAM GÖNDERİM FONKSİYONU (429 Flood Koruma Mekanizmalı)
# ======================================================================
def telegram_gonder(message: str):
    if not BOT_TOKEN or not TELEGRAM_CHAT_IDS or not TELEGRAM_CHAT_IDS[0]:
        print("⚠️ Telegram Token veya Chat ID eksik! Mesaj gönderilemedi.")
        return
    for cid in TELEGRAM_CHAT_IDS:
        if not cid: continue
        retries = 3
        for attempt in range(retries):
            try:
                data = {
                    "chat_id": cid,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                resp = req.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data, timeout=15)
                
                if resp.status_code == 200:
                    time.sleep(1.2) # Mesajlar arası flood sınırı önlemi
                    break
                elif resp.status_code == 429:
                    try:
                        retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                    except:
                        retry_after = 5
                    print(f"⚠️ Telegram 429 Flood Sınırı! {retry_after} saniye bekleniyor...")
                    time.sleep(retry_after + 1)
                else:
                    print(f"Telegram API Hatası ({resp.status_code}): {resp.text}")
                    break
            except Exception as e:
                print(f"Telegram Gönderim Hatası: {e}")
                time.sleep(2)

# ======================================================================
# 📊 MATEMATİKSEL İNDİKATÖR VE PRO HESAPLAMA MOTORU
# ======================================================================
def pine_rma(src, length):
    alpha = 1 / length
    return src.ewm(alpha=alpha, min_periods=length, adjust=False).mean()

def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_macd_cross(df: pd.DataFrame) -> bool:
    if len(df) < 35: return False
    df = df.copy()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    cross_current = (macd.iloc[-1] > signal.iloc[-1]) and (macd.iloc[-2] <= signal.iloc[-2])
    cross_previous = (macd.iloc[-2] > signal.iloc[-2]) and (macd.iloc[-3] <= signal.iloc[-3])
    return bool(cross_current or cross_previous)

def calculate_adx(df, period=14):
    try:
        if df is None or len(df) < (period * 2):
            return 20.0, "ZAYIF / YATAY ⚖️"
        df = df.copy()
        high, low, close = df['High'], df['Low'], df['Close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
        plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10)
        minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10)
        sum_di = (plus_di + minus_di).replace(0, 1e-10)
        dx = 100 * abs(plus_di - minus_di) / sum_di
        adx = dx.ewm(alpha=1/period, adjust=False).mean().iloc[-1]
        if np.isnan(adx): adx = 20.0
        status = "GÜÇLÜ TREND 🚀" if adx > 25 else "ZAYIF / YATAY ⚖️"
        return float(adx), status
    except:
        return 20.0, "ZAYIF / YATAY ⚖️"

def calculate_mfi(df, period=14):
    try:
        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
        raw_money_flow = hlc3 * df['Volume']
        positive_flow = raw_money_flow.where(hlc3 > hlc3.shift(1), 0).rolling(window=period).sum()
        negative_flow = raw_money_flow.where(hlc3 < hlc3.shift(1), 0).rolling(window=period).sum()
        mfi = 100 - (100 / (1 + positive_flow / (negative_flow + 1e-10)))
        val = mfi.iloc[-1]
        return val if not np.isnan(val) else 50.0
    except:
        return 50.0

def calculate_pro_metrics(df_target, df_weekly):
    try:
        if df_target is None or len(df_target) < 50: return None
        close = df_target['Close']
        current_price = close.iloc[-1]
        
        rsi_daily = calculate_rsi(close, 14).iloc[-1]
        rsi_weekly = calculate_rsi(df_weekly['Close'], 14).iloc[-1] if df_weekly is not None and len(df_weekly) > 14 else rsi_daily
        
        adx_val, adx_status = calculate_adx(df_target, 14)
        mfi_val = calculate_mfi(df_target, 14)
        money_flow = "PARA GİRİŞİ ✅" if mfi_val > 50 else "PARA ÇIKIŞI ❌"
        
        return {
            "price": current_price, "rsi_d": rsi_daily, "rsi_w": rsi_weekly,
            "adx": adx_val, "adx_status": adx_status, "mfi": mfi_val, "money_flow": money_flow
        }
    except:
        return None

# ======================================================================
# 📌 PINE SCRIPT BİREBİR İNDİKATÖR MOTORLARI
# ======================================================================
def calculate_leda_indicators(df):
    try:
        if len(df) < 30: return None
        df = df.copy()
        high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']
        hl2 = (high + low) / 2
        hlc3 = (high + low + close) / 3
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        
        atr_ap = tr.rolling(window=14).mean()
        mf = hlc3 * volume
        upper_mf = mf.where(hlc3 > hlc3.shift(1), 0.0)
        lower_mf = mf.where(hlc3 < hlc3.shift(1), 0.0)
        pos_mf = upper_mf.rolling(window=14).sum()
        neg_mf = lower_mf.rolling(window=14).sum()
        df['mfi'] = 100 - (100 / (1 + (pos_mf / (neg_mf + 1e-10))))
        
        at = np.zeros(len(df))
        upT = (low - atr_ap * 1.0).values
        dnT = (high + atr_ap * 1.0).values
        mfi_vals = df['mfi'].values
        
        for i in range(1, len(df)):
            if mfi_vals[i] >= 50:
                at[i] = max(upT[i], at[i-1]) if not np.isnan(at[i-1]) else upT[i]
            else:
                at[i] = min(dnT[i], at[i-1]) if not np.isnan(at[i-1]) else dnT[i]
        df['AlphaTrend'] = at

        atr_st = pine_rma(tr, 7)
        up_st = (hl2 - 3.0 * atr_st).values
        dn_st = (hl2 + 3.0 * atr_st).values
        trUp = np.zeros(len(df))
        trDn = np.zeros(len(df))
        tsl = np.zeros(len(df))
        trend = np.ones(len(df))
        close_vals = close.values
        
        for i in range(1, len(df)):
            trUp[i] = max(up_st[i], trUp[i-1]) if close_vals[i-1] > trUp[i-1] else up_st[i]
            trDn[i] = min(dn_st[i], trDn[i-1]) if close_vals[i-1] < trDn[i-1] else dn_st[i]
            if close_vals[i] > trDn[i-1]: trend[i] = 1
            elif close_vals[i] < trUp[i-1]: trend[i] = -1
            else: trend[i] = trend[i-1]
            tsl[i] = trUp[i] if trend[i] == 1 else trDn[i]
            
        df['TSL'] = tsl
        df['buy'] = (df['AlphaTrend'] > df['TSL']) & (df['AlphaTrend'].shift(1) <= df['TSL'].shift(1))
        df['sell'] = (df['AlphaTrend'] < df['TSL']) & (df['AlphaTrend'].shift(1) >= df['TSL'].shift(1))
        return df
    except:
        return None

def check_hu_cross_signal(df: pd.DataFrame) -> bool:
    len1, len2, smoothLen = 200, 400, 20
    if len(df) < len2 + smoothLen + 2: return False
    df = df.copy()
    hu_base1 = wma(df['Close'], len1)
    hu_base2 = wma(df['Close'], len2)
    hu_raw = (2 * hu_base1) - hu_base2
    df['HU_Line'] = wma(hu_raw, smoothLen)
    df['cross_up'] = (df['Close'] > df['HU_Line']) & (df['Close'].shift(1) <= df['HU_Line'].shift(1))
    return bool(df['cross_up'].iloc[-1])

def check_mavilim_signal(df: pd.DataFrame) -> bool:
    if len(df) < 55: return False
    df = df.copy()
    k1 = df['Close']
    k2 = wma(k1, 3); k3 = wma(k2, 5); k4 = wma(k3, 8)
    k5 = wma(k4, 13); k6 = wma(k5, 21)
    df['K7'] = wma(k6, 34)
    df['cross_up'] = (df['Close'] > df['K7']) & (df['Close'].shift(1) <= df['K7'].shift(1))
    return bool(df['cross_up'].iloc[-1])

def check_triple_confluence_signal(df: pd.DataFrame) -> bool:
    if len(df) < 85: return False
    df = df.copy()
    df = calculate_leda_indicators(df)
    if df is None: return False
    k1 = df['Close']
    k2 = wma(k1, 3); k3 = wma(k2, 5); k4 = wma(k3, 8)
    k5 = wma(k4, 13); k6 = wma(k5, 21)
    df['Mavilim'] = wma(k6, 34)
    df['WMA79'] = wma(df['Close'], 79)
    leda_buy = df["buy"].iloc[-1]
    mavilim_cross = (df['Close'].iloc[-1] > df['Mavilim'].iloc[-1]) and (df['Close'].iloc[-2] <= df['Mavilim'].iloc[-2])
    wma79_cross = (df['Close'].iloc[-1] > df['WMA79'].iloc[-1]) and (df['Close'].iloc[-2] <= df['WMA79'].iloc[-2])
    return bool(leda_buy and mavilim_cross and wma79_cross)

def calculate_rsi_most_matrix(series_close: pd.Series, rsi_len=14, most_sma=3, most_ema=2, mov_short=5, mov_mid=40, mov_long=160):
    rsi_val = calculate_rsi(series_close, rsi_len)
    sma_rsi = rsi_val.rolling(window=most_sma).mean()
    base = sma_rsi.ewm(span=most_ema, adjust=False).mean()
    mov5 = base.ewm(span=mov_short, adjust=False).mean()
    mov40 = base.ewm(span=mov_mid, adjust=False).mean()
    mov160 = base.ewm(span=mov_long, adjust=False).mean()
    
    yellow_cross_30 = (base.iloc[-1] > 30 and base.iloc[-2] <= 30) or (base.iloc[-2] > 30 and base.iloc[-3] <= 30)
    bm_cross = (mov40.iloc[-1] > mov160.iloc[-1] and mov40.iloc[-2] <= mov160.iloc[-2]) or (mov40.iloc[-2] > mov160.iloc[-2] and mov40.iloc[-3] <= mov160.iloc[-3])
    near_50 = mov40.iloc[-1] >= 48 or mov40.iloc[-2] >= 48
    blue_cross_red_above_50 = bm_cross and near_50
    
    return {
        "base": base, "mov40": mov40, "mov160": mov160,
        "yellow_cross_30": yellow_cross_30,
        "blue_cross_red_above_50": blue_cross_red_above_50
    }

def calculate_rsi_signals(series_close: pd.Series):
    rsi_val = calculate_rsi(series_close, 14)
    sma_rsi = rsi_val.rolling(window=3).mean()
    base = sma_rsi.ewm(span=2, adjust=False).mean()
    mov5 = base.ewm(span=5, adjust=False).mean()
    mov40 = base.ewm(span=40, adjust=False).mean()
    mov160 = base.ewm(span=160, adjust=False).mean()
    
    yellow_cross_green = (base.iloc[-1] > mov5.iloc[-1] and base.iloc[-2] <= mov5.iloc[-2]) or \
                         (base.iloc[-2] > mov5.iloc[-2] and base.iloc[-3] <= mov5.iloc[-3])
    cond_red_near_50 = (mov160.iloc[-1] < 50) and (mov160.iloc[-1] >= 40)
    cond_blue_below_red = mov40.iloc[-1] < mov160.iloc[-1]
    
    yellow_cross_30 = (base.iloc[-1] > 30 and base.iloc[-2] <= 30) or (base.iloc[-2] > 30 and base.iloc[-3] <= 30)
    yellow_bottom = (base.iloc[-1] <= 40) or (base.iloc[-2] <= 40)
    dip_signal = (yellow_cross_30 or (yellow_cross_green and yellow_bottom)) and cond_red_near_50 and cond_blue_below_red
    
    yellow_mid = (40 <= base.iloc[-1] <= 45) or (40 <= base.iloc[-2] <= 45)
    orta_signal = yellow_cross_green and yellow_mid and cond_red_near_50 and cond_blue_below_red
    return dip_signal, orta_signal

# ======================================================================
# 🚀 PRO BÜLTEN KART FORMATLAYICI (Stop, TP ve Skor Kaldırıldı)
# ======================================================================
def send_pro_report(strategy_title, ticker, tv_link, pro, badge=""):
    badge_line = f"<b>{badge}</b>\n\n" if badge else ""
    msg = (
        f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n"
        f"📌 <b>Strateji:</b> {strategy_title}\n"
        f"{badge_line}"
        f"🎯 <b>Hisse:</b> <a href='{tv_link}'><b>{ticker}</b></a>\n"
        f"💲 <b>Fiyat:</b> {pro['price']:.2f} ₺\n\n"
        f"📊 <b>Osilatörler </b>\n"
        f"💹 Günlük RSI: <b>{pro['rsi_d']:.2f}</b>\n"
        f"💹 Haftalık RSI: <b>{pro['rsi_w']:.2f}</b>\n"
        f"💪 ADX: <b>{pro['adx']:.2f} ({pro['adx_status']})</b>\n"
        f"💥 <b>{pro['money_flow']}</b> (MFI: {pro['mfi']:.1f})\n\n"
        f"<i>ℹ️ Otomatik Akıllı Sinyal Sistemi</i>"
    )
    telegram_gonder(msg)

# ======================================================================
# 🚀 ANA TARAMA MOTORU
# ======================================================================
def run_targeted_screener():
    init_db()
    print(f"🚀 Seçilen Strateji Çalıştırılıyor: {SELECTED_STRATEGY}")
    telegram_gonder(
        f"🎯 <b>Emekli Sinyal Tarama Başlatıldı.</b>\n"
        f"📊 Mod: <b>{SELECTED_STRATEGY}</b>\n"
        f"🤖 Bot için <b>6 Özel Strateji</b> aktif.\n"
        f"🔍 Kendi kullandığınız indikatörler ile kontrol ediniz.\n"
        f"📰 Güncel piyasa verilerini ve haberleri takip etmeyi unutmayın.\n"
        f"🤖 Bot aktif ve tarama gerçekleştiriliyor...\n"
        f"⚠️ <i>Sinyaller bilgi amaçlıdır, Yatırım Tavsiyesi Değildir.</i>"
    )

    s1_uzun_ralli = []
    s2_base_30 = []
    s3_matrix_wm = []
    s4_uclu_kesisim = []
    
    s5_leda_d_sade = []
    s6_leda_d_macd = []
    s7_leda_w_sade = []
    s8_leda_w_macd = []
    
    s9_hu_d_sade = []
    s10_hu_d_macd = []
    
    s11_mav_w_sade = []
    s12_mav_w_macd = []
    
    s13_hassas_dip = []
    s14_hassas_orta = []

    for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
        batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
        try:
            data_1d = yf.download(batch, interval="1d", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            data_1wk = yf.download(batch, interval="1wk", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)

            for full_ticker in batch:
                ticker = full_ticker.replace('.IS', '')
                
                try: df_d = data_1d[full_ticker].dropna() if len(batch) > 1 else data_1d.dropna()
                except: df_d = pd.DataFrame()

                try: df_w = data_1wk[full_ticker].dropna() if len(batch) > 1 else data_1wk.dropna()
                except: df_w = pd.DataFrame()

                # Çifte Onay Kontrol Bayrakları
                leda_d_signal = False
                leda_w_signal = False

                # 1. Uzun Vade Ralli
                if not df_d.empty and len(df_d) >= 180:
                    res_r = calculate_rsi_most_matrix(df_d['Close'])
                    if res_r["blue_cross_red_above_50"]:
                        st_name = "💎 1. UZUN VADE RALLİ"
                        if not signal_already_sent(ticker, st_name):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s1_uzun_ralli.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_name)

                # 2. Base 30
                if not df_d.empty and len(df_d) >= 30:
                    b_res = calculate_rsi_most_matrix(df_d['Close'])
                    if b_res["yellow_cross_30"]:
                        st_name = "🟡 2. RSI-MOST BASE 30"
                        if not signal_already_sent(ticker, st_name):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s2_base_30.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_name)

                # Matrix Orta Hat 50
                if not df_d.empty and len(df_d) >= 100:
                    df_w_res = df_d.resample('W').agg({'Close': 'last'}).dropna()
                    if len(df_w_res) >= 50:
                        m_res = calculate_rsi_most_matrix(df_w_res['Close'])
                        if m_res["mov40"].iloc[-1] > 50 and m_res["mov40"].iloc[-2] <= 50:
                            st_name = "📅 3. MATRIX ORTA HAT 50"
                            if not signal_already_sent(ticker, st_name):
                                tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                                pro_w = calculate_pro_metrics(df_w_res, df_w)
                                if pro_w: s3_matrix_wm.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_name)

                # 4. Üçlü Kesişim
                if not df_d.empty and check_triple_confluence_signal(df_d):
                    st_name = "💥 4. ÜÇLÜ KESİŞİM (GÜNLÜK)"
                    if not signal_already_sent(ticker, st_name):
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                        pro_d = calculate_pro_metrics(df_d, df_w)
                        if pro_d: s4_uclu_kesisim.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_name)
                elif not df_w.empty and check_triple_confluence_signal(df_w):
                    st_name = "💥 4. ÜÇLÜ KESİŞİM (HAFTALIK)"
                    if not signal_already_sent(ticker, st_name):
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                        pro_w = calculate_pro_metrics(df_w, df_w)
                        if pro_w: s4_uclu_kesisim.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_name)

                # LEDA KONTROLLERİ (Sade, MACD ve Çifte Onay Kontrolü)
                if not df_d.empty and len(df_d) >= 35:
                    res_leda_d = calculate_leda_indicators(df_d)
                    if res_leda_d is not None and res_leda_d["buy"].iloc[-1]:
                        leda_d_signal = True
                        st_sade = "📊 LEDA GÜNLÜK (SADE)"
                        if not signal_already_sent(ticker, st_sade):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s5_leda_d_sade.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_sade)
                        
                        if check_macd_cross(df_d):
                            st_macd = "📈 LEDA GÜNLÜK + MACD"
                            if not signal_already_sent(ticker, st_macd):
                                tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                                pro_d = calculate_pro_metrics(df_d, df_w)
                                if pro_d: s6_leda_d_macd.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_macd)

                if not df_w.empty and len(df_w) >= 35:
                    res_leda_w = calculate_leda_indicators(df_w)
                    if res_leda_w is not None and res_leda_w["buy"].iloc[-1]:
                        leda_w_signal = True
                        st_sade_w = "📊 LEDA HAFTALIK (SADE)"
                        if not signal_already_sent(ticker, st_sade_w):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                            pro_w = calculate_pro_metrics(df_w, df_w)
                            if pro_w: s7_leda_w_sade.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_sade_w)
                        
                        if check_macd_cross(df_w):
                            st_macd_w = "📈 LEDA HAFTALIK + MACD"
                            if not signal_already_sent(ticker, st_macd_w):
                                tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                                pro_w = calculate_pro_metrics(df_w, df_w)
                                if pro_w: s8_leda_w_macd.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_macd_w)

                # ⭐ ÇİFTE ONAY KONTROLÜ (Hem Günlük Hem Haftalık Leda Al Sinyali)
                if leda_d_signal and leda_w_signal:
                    st_double = "⭐ ÇİFTE ZAMAN DİLİMİ ONAYI (GÜNLÜK + HAFTALIK LEDA)"
                    if not signal_already_sent(ticker, st_double):
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                        pro_w = calculate_pro_metrics(df_w, df_w)
                        if pro_w:
                            send_pro_report(st_double, ticker, tv_link, pro_w, "⭐ GÜNLÜK & HAFTALIK ÇİFTE ONAY")
                            mark_signal_sent(ticker, st_double)

                # HU KONTROLLERİ (Sade ve MACD - Günlük)
                if not df_d.empty and check_hu_cross_signal(df_d):
                    st_hu_sade = "💎 HU GÜNLÜK (SADE)"
                    if not signal_already_sent(ticker, st_hu_sade):
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                        pro_d = calculate_pro_metrics(df_d, df_w)
                        if pro_d: s9_hu_d_sade.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_hu_sade)
                    
                    if check_macd_cross(df_d):
                        st_hu_macd = "💎 HU GÜNLÜK + MACD"
                        if not signal_already_sent(ticker, st_hu_macd):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s10_hu_d_macd.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_hu_macd)

                # MAVİLİM KONTROLLERİ (Sade ve MACD - Haftalık)
                if not df_w.empty and check_mavilim_signal(df_w):
                    st_mav_sade = "🌊 MAVİLİM HAFTALIK (SADE)"
                    if not signal_already_sent(ticker, st_mav_sade):
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                        pro_w = calculate_pro_metrics(df_w, df_w)
                        if pro_w: s11_mav_w_sade.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_mav_sade)
                    
                    if check_macd_cross(df_w):
                        st_mav_macd = "🌊 MAVİLİM HAFTALIK + MACD"
                        if not signal_already_sent(ticker, st_mav_macd):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                            pro_w = calculate_pro_metrics(df_w, df_w)
                            if pro_w: s12_mav_w_macd.append((ticker, tv_link, pro_w, "")); mark_signal_sent(ticker, st_mav_macd)

                # 11. Hassas Dip ve Orta Bant
                if not df_d.empty and len(df_d) >= 180:
                    dip, orta = calculate_rsi_signals(df_d['Close'])
                    if dip:
                        st_dip = "🎯 11. HASSAS DİP"
                        if not signal_already_sent(ticker, st_dip):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s13_hassas_dip.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_dip)
                    if orta:
                        st_orta = "🎯 11. ORTA BANT"
                        if not signal_already_sent(ticker, st_orta):
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s14_hassas_orta.append((ticker, tv_link, pro_d, "")); mark_signal_sent(ticker, st_orta)

        except Exception as e:
            print(f"Batch Hatası: {e}")
            traceback.print_exc()

        time.sleep(DELAY_BETWEEN_BATCHES)

    def report_strategy(title, items):
        if items:
            for item in items:
                ticker, tv_link, pro, badge = item
                send_pro_report(title, ticker, tv_link, pro, badge)
        else:
            msg = f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n📌 <b>Strateji:</b> {title}\n\n❌ <i>Bu taramada koşulu sağlayan hisse yok.</i>"
            telegram_gonder(msg)

    # Raporlama Sıralaması
    report_strategy("1️⃣ RALLİ BAŞLANGIÇ", s1_uzun_ralli)
    report_strategy("2️⃣ RSI-MOST 30", s2_base_30)
    report_strategy("3️⃣ RSI-MOST 50", s3_matrix_wm)
    report_strategy("4️⃣ ÜÇLÜ KESİŞİM", s4_uclu_kesisim)
    report_strategy("5️⃣ LEDA GÜNLÜK", s5_leda_d_sade)
    report_strategy("6️⃣ LEDA GÜNLÜK + MACD", s6_leda_d_macd)
    report_strategy("7️⃣ LEDA HAFTALIK", s7_leda_w_sade)
    report_strategy("8️⃣ LEDA HAFTALIK + MACD", s8_leda_w_macd)
    report_strategy("9️⃣ HU GÜNLÜK", s9_hu_d_sade)
    report_strategy("🔟 HU GÜNLÜK + MACD", s10_hu_d_macd)
    report_strategy("1️⃣1️⃣ MAVİLİM HAFTALIK", s11_mav_w_sade)
    report_strategy("1️⃣2️⃣ MAVİLİM HAFTALIK + MACD", s12_mav_w_macd)
    report_strategy("1️⃣3️⃣ HASSAS DİP", s13_hassas_dip)
    report_strategy("1️⃣4️⃣ ORTA BANT", s14_hassas_orta)

    telegram_gonder("🏁 <b>Pro Tarama ve Kontrol Tamamlandı.</b>")

if __name__ == "__main__":
    run_targeted_screener()

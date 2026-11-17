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

BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 3

BIST_TICKERS = [
    "AEFES", "AGHOL", "AKBNK", "AKSA", "AKSEN", "ALARK", "ALFAS", "ANSGR", "ARCLK", "ASELS",
    "ASTOR", "BERA", "BIMAS", "BRSAN", "BRYAT", "BUCIM", "CCOLA", "CIMSA", "CWENE", "DOAS",
    "DOHOL", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI", "EREGL", "EUPWR", "FENER", "FROTO",
    "GARAN", "GENIL", "GESAN", "GSRAY", "GUBRF", "HALKB", "HEKTS", "ISCTR", "ISMEN", "KCAER",
    "KCHOL", "KONTR", "KRDMD", "MAVI", "MGROS", "MIATK", "MPARK", "ODAS", "OTKAR", "OYAKC",
    "PETKM", "PGSUS", "REEDR", "SAHOL", "SASA", "SISE", "SKBNK", "SMRTG", "SOKM", "TABGD",
    "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUPRS", "ULKER",
    "VAKBN", "VESTL", "YEOTK", "YKBNK", "ZOREN", "AGROT", "AHGAZ", "AKCNS", "AKFYE", "ALBRK",
    "ALKIM", "ARASE", "ARDYZ", "ASUZU", "AYDEM", "AYGAZ", "BAGFS", "BASGZ", "BFREN", "BIENY",
    "BIOEN", "BIZIM", "BORLS", "BOSSA", "BRISA", "BRLSM", "CATES", "CEMTS", "CVKMD", "DEVA",
    "EBEBK", "ECILC", "ECZYT", "EGGUB", "EGSER", "EKOS", "EKSUN", "ENSRI", "ENTRA", "ERBOS",
    "ESEN", "EUREN", "FMIZP", "FORTE", "GEDIK", "GENTS", "GIPTA", "GLYHO", "GOLTS", "GOODY",
    "GWIND", "HATSN", "HEDEF", "HKTM", "HRKET", "HUNER", "INDES", "INFO", "INVEO", "INVES",
    "ISDMR", "IZMDC", "JANTS", "KAREL", "KARSN", "KAYSE", "KBORU", "KFEIN", "KIMMR", "KLKIM",
    "KLMSN", "KLSER", "KMPUR", "KONKA", "KONYA", "KORDS", "KOTON", "KRONT", "LIDER", "LILAK",
    "LOGO", "MAALT", "MEDTR", "MHRGY", "MNDRS", "MOBTL", "MOGAN", "NATEN", "NETAS", "ODINE",
    "ONCSM", "ORGE", "OSMEN", "PASEU", "PATEK", "PENTA", "PETUN", "PNSUT", "POLHO", "PRKME",
    "QUAGR", "RGYAS", "RYSAS", "SDTTR", "SELEC", "SNICA", "SUNTK", "SUWEN", "TARKM", "TATEN",
    "TATGD", "TBORG", "TEZOL", "TKNSA", "TMSN", "TRCAS", "TRGYO", "TSPOR", "TUKAS", "ULUSE",
    "ULUUN", "UNLU", "USAK", "VAKKO", "VBTYZ", "VERTU", "VERUS", "VESBE", "YATAS", "YAYLA",
    "YKSLN", "YUNSA", "CLEBI", "TUREX", "GRSEL", "PARSN", "NTGAZ", "BANVT", "MTRKS", "LINK", "OZKGY", 
    "NUHCM", "BOBET"
]
BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

# ======================================================================
# 💾 PERSISTENT HAFIZA / SQLITE (TEKRAR ÖNLEME)
# ======================================================================
conn = sqlite3.connect('rsi_most_matrix_signals.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS sent_signals (
    ticker TEXT,
    signal_id TEXT,
    close_price REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, signal_id)
)
""")
conn.commit()

def was_sent_before(ticker, signal_id, hours=12):
    cutoff = time.time() - (hours * 3600)
    cursor.execute("""
        SELECT 1 FROM sent_signals
        WHERE ticker = ? AND signal_id = ? AND timestamp > datetime(?, 'unixepoch')
    """, (ticker, signal_id, cutoff))
    return cursor.fetchone() is not None

def save_signal(ticker, signal_id, close_price):
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO sent_signals (ticker, signal_id, close_price)
            VALUES (?, ?, ?)
        """, (ticker, signal_id, close_price))
        conn.commit()
    except Exception as e:
        print(f"Sinyal kaydetme hatası: {e}", file=sys.stderr)

# ======================================================================
# 📩 TELEGRAM GÖNDERİM FONKSİYONU
# ======================================================================
def telegram_gonder(message: str):
    if not BOT_TOKEN or not TELEGRAM_CHAT_IDS or not TELEGRAM_CHAT_IDS[0]:
        print("⚠️ Telegram Token veya Chat ID eksik! Mesaj gönderilemedi.")
        return
    for cid in TELEGRAM_CHAT_IDS:
        if not cid: continue
        try:
            data = {
                "chat_id": cid,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            req.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data, timeout=15)
        except Exception as e:
            print(f"Telegram Gönderim Hatası: {e}")

def make_tv_link(ticker: str, interval: str = "D") -> str:
    url = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval={interval}"
    return f"<a href='{url}'><b>{ticker}</b></a>"

# ======================================================================
# 📊 MATEMATİKSEL İNDİKATÖR FONKSİYONLARI
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
        df["buy"] = (df["AlphaTrend"] > df["TSL"]) & (df["AlphaTrend"].shift(1) <= df["TSL"].shift(1))
        df["sell"] = (df["AlphaTrend"] < df["TSL"]) & (df["AlphaTrend"].shift(1) >= df["TSL"].shift(1))
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
    blue_cross_50 = (mov40.iloc[-1] > 50 and mov40.iloc[-2] <= 50) or (mov40.iloc[-2] > 50 and mov40.iloc[-3] <= 50)
    bm_cross = (mov40.iloc[-1] > mov160.iloc[-1] and mov40.iloc[-2] <= mov160.iloc[-2]) or (mov40.iloc[-2] > mov160.iloc[-2] and mov40.iloc[-3] <= mov160.iloc[-3])
    near_50 = mov40.iloc[-1] >= 48 or mov40.iloc[-2] >= 48
    blue_cross_red_above_50 = bm_cross and near_50
    
    return {
        "base": base, "mov40": mov40, "mov160": mov160,
        "yellow_cross_30": yellow_cross_30,
        "blue_cross_50": blue_cross_50,
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
# 🚀 TEK SEFERLİK MASTER TARAMA MOTORU (Cron-job.org / GitHub Uyumlu)
# ======================================================================
def run_all_11_screeners_once():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 11 Strateji Taraması Başlatıldı...")
    
    s1_uzun_ralli = []
    s2_base_30 = []
    s3_matrix_wm = []
    s4_uclu_kesisim = []
    s5_leda_d_macd = []
    s6_leda_d_sade = []
    s7_leda_w_macd = []
    s8_leda_w_sade = []
    s9_mav_w_macd = []
    s10_mav_w_sade = []
    s11_hassas_dip_orta = []
    s_hourly_sell = []
    
    for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
        batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
        
        try:
            data_1d = yf.download(batch, interval="1d", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            data_1wk = yf.download(batch, interval="1wk", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            data_1h = yf.download(batch, interval="1h", period="60d", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            
            for full_ticker in batch:
                ticker = full_ticker.replace('.IS', '')
                
                try: df_d = data_1d[full_ticker].dropna() if len(batch) > 1 else data_1d.dropna()
                except: df_d = pd.DataFrame()

                try: df_w = data_1wk[full_ticker].dropna() if len(batch) > 1 else data_1wk.dropna()
                except: df_w = pd.DataFrame()

                try: df_h = data_1h[full_ticker].dropna() if len(batch) > 1 else data_1h.dropna()
                except: df_h = pd.DataFrame()
                
                # --- SAATLİK LEDA SAT KONTROLÜ ---
                try:
                    if not df_h.empty and len(df_h) >= 30:
                        res_h = calculate_leda_indicators(df_h)
                        if res_h is not None and "sell" in res_h.columns and res_h["sell"].iloc[-1]:
                            sig_id = f"HOURLY_SELL_{ticker}"
                            if not was_sent_before(ticker, sig_id, hours=12):
                                price_h = df_h['Close'].iloc[-1]
                                s_hourly_sell.append(f"• {make_tv_link(ticker, '60')} ({price_h:.2f}₺)")
                                save_signal(ticker, sig_id, price_h)
                except Exception as e:
                    pass

                # --- GÜNLÜK & HAFTALIK KOŞULLAR ---
                daily_signals_list = []
                weekly_signals_list = []
                
                # 1. Uzun Vadeli Ralli (Günlük)
                ralli_d = False
                if not df_d.empty and len(df_d) >= 180:
                    res_ralli = calculate_rsi_most_matrix(df_d['Close'])
                    if res_ralli["blue_cross_red_above_50"]:
                        ralli_d = True
                        daily_signals_list.append("Uzun Vade Ralli")

                # 2. RSI-MOST Base 30
                base_30_d = False
                if not df_d.empty and len(df_d) >= 30:
                    b_res = calculate_rsi_most_matrix(df_d['Close'])
                    if b_res["yellow_cross_30"]:
                        base_30_d = True
                        daily_signals_list.append("Base 30")

                # 3. Matrix Orta Hat (50) Kesişimi (Haftalık Resample)
                matrix_wm = False
                if not df_d.empty and len(df_d) >= 100:
                    df_w_res = df_d.resample('W').agg({'Close': 'last'}).dropna()
                    if len(df_w_res) >= 50:
                        m_res = calculate_rsi_most_matrix(df_w_res['Close'])
                        if (m_res["mov40"].iloc[-1] > 50 and m_res["mov40"].iloc[-2] <= 50):
                            matrix_wm = True
                            weekly_signals_list.append("Matrix Orta Hat 50")

                # 4. Üçlü Kesişim
                uclu_d = not df_d.empty and check_triple_confluence_signal(df_d)
                uclu_w = not df_w.empty and check_triple_confluence_signal(df_w)
                if uclu_d: daily_signals_list.append("Üçlü Kesişim Günlük")
                if uclu_w: weekly_signals_list.append("Üçlü Kesişim Haftalık")

                # 5 & 6. Leda Günlük Al (+ MACD / Sade)
                leda_d_buy = False
                leda_d_macd_ok = False
                if not df_d.empty and len(df_d) >= 35:
                    res_leda_d = calculate_leda_indicators(df_d)
                    if res_leda_d is not None and res_leda_d["buy"].iloc[-1]:
                        leda_d_buy = True
                        daily_signals_list.append("Leda Günlük")
                        if check_macd_cross(df_d):
                            leda_d_macd_ok = True

                # 7 & 8. Leda Haftalık Al (+ MACD / Sade)
                leda_w_buy = False
                leda_w_macd_ok = False
                if not df_w.empty and len(df_w) >= 35:
                    res_leda_w = calculate_leda_indicators(df_w)
                    if res_leda_w is not None and res_leda_w["buy"].iloc[-1]:
                        leda_w_buy = True
                        weekly_signals_list.append("Leda Haftalık")
                        if check_macd_cross(df_w):
                            leda_w_macd_ok = True

                # 9 & 10. Mavilim Haftalık (+ MACD / Sade)
                mav_w_cross = False
                mav_w_macd_ok = False
                if not df_w.empty and check_mavilim_signal(df_w):
                    mav_w_cross = True
                    weekly_signals_list.append("Mavilim Haftalık")
                    if check_macd_cross(df_w):
                        mav_w_macd_ok = True

                # 11. Hassas Dip ve Orta Bant
                dip_d, orta_d = False, False
                if not df_d.empty and len(df_d) >= 180:
                    dip_d, orta_d = calculate_rsi_signals(df_d['Close'])
                    if dip_d or orta_d:
                        daily_signals_list.append("Hassas Dip/Orta")

                # --- ÇİFT ONAY KONTROLÜ (Günlük & Haftalık Confluence) ---
                is_double = (len(daily_signals_list) > 0) and (len(weekly_signals_list) > 0)
                confluence_badge = f" ⭐ [ÇİFT ONAY: {' + '.join(daily_signals_list)} & {' + '.join(weekly_signals_list)}]" if is_double else ""

                # --- LİSTELERE EKLEME VE HAFIZA KONTROLÜ ---
                price_d = df_d['Close'].iloc[-1] if not df_d.empty else 0
                price_w = df_w['Close'].iloc[-1] if not df_w.empty else price_d

                # 1. Uzun Vade Ralli
                if ralli_d:
                    sig_id = "S1_UZUN_RALLI"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s1_uzun_ralli.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)

                # 2. RSI-MOST Base 30
                if base_30_d:
                    sig_id = "S2_BASE_30"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s2_base_30.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)

                # 3. Matrix Orta Hat 50
                if matrix_wm:
                    sig_id = "S3_MATRIX_WM"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s3_matrix_wm.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 4. Üçlü Kesişim
                if uclu_d:
                    sig_id = "S4_UCLU_D"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s4_uclu_kesisim.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺ - Günlük){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)
                if uclu_w:
                    sig_id = "S4_UCLU_W"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s4_uclu_kesisim.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺ - Haftalık){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 5. Leda Günlük Al + MACD
                if leda_d_buy and leda_d_macd_ok:
                    sig_id = "S5_LEDA_D_MACD"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s5_leda_d_macd.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)

                # 6. Leda Günlük Al Sade
                if leda_d_buy:
                    sig_id = "S6_LEDA_D_SADE"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s6_leda_d_sade.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)

                # 7. Leda Haftalık Al + MACD
                if leda_w_buy and leda_w_macd_ok:
                    sig_id = "S7_LEDA_W_MACD"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s7_leda_w_macd.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 8. Leda Haftalık Al Sade
                if leda_w_buy:
                    sig_id = "S8_LEDA_W_SADE"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s8_leda_w_sade.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 9. Mavilim Haftalık + MACD
                if mav_w_cross and mav_w_macd_ok:
                    sig_id = "S9_MAV_W_MACD"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s9_mav_w_macd.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 10. Mavilim Haftalık Sade
                if mav_w_cross:
                    sig_id = "S10_MAV_W_SADE"
                    if not was_sent_before(ticker, sig_id, hours=48):
                        s10_mav_w_sade.append(f"• {make_tv_link(ticker, 'W')} ({price_w:.2f}₺){confluence_badge}")
                        save_signal(ticker, sig_id, price_w)

                # 11. Hassas Dip ve Orta Bant
                if dip_d:
                    sig_id = "S11_HASSAS_DIP"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s11_hassas_dip_orta.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺ - DİP){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)
                if orta_d:
                    sig_id = "S11_HASSAS_ORTA"
                    if not was_sent_before(ticker, sig_id, hours=24):
                        s11_hassas_dip_orta.append(f"• {make_tv_link(ticker, 'D')} ({price_d:.2f}₺ - ORTA){confluence_badge}")
                        save_signal(ticker, sig_id, price_d)

        except Exception as e:
            print(f"Batch Hatası: {e}")
            traceback.print_exc()
        
        time.sleep(DELAY_BETWEEN_BATCHES)
    
    # --- RAPORLAMA ---
    def report(title, items):
        if items:
            telegram_gonder(f"<b>{title}</b>\n--------------------------------------\n" + "\n".join(items))

    report("⚠️ SAATLİK LEDA SAT SİNYALİ", s_hourly_sell)
    report("💎 1. UZUN VADELİ RALLİ TARAMASI", s1_uzun_ralli)
    report("🟡 2. RSI-MOST BASE 30 KESİŞİMİ", s2_base_30)
    report("📅 3. MATRIX ORTA HAT (50) KESİŞİMİ", s3_matrix_wm)
    report("💥 4. ÜÇLÜ KESİŞİM STRATEJİSİ", s4_uclu_kesisim)
    report("📈 5. LEDA GÜNLÜK AL + MACD", s5_leda_d_macd)
    report("📊 6. LEDA GÜNLÜK AL SADE", s6_leda_d_sade)
    report("📈 7. LEDA HAFTALIK AL + MACD", s7_leda_w_macd)
    report("📊 8. LEDA HAFTALIK AL SADE", s8_leda_w_sade)
    report("🌊 9. MAVİLİM HAFTALIK + MACD", s9_mav_w_macd)
    report("🌊 10. MAVİLİM HAFTALIK SADE", s10_mav_w_sade)
    report("🎯 11. HASSAS DİP VE ORTA BANT TARAMASI", s11_hassas_dip_orta)
    
    print("✅ Tarama başarıyla tamamlandı ve raporlar iletildi.")

if __name__ == "__main__":
    run_all_11_screeners_once()

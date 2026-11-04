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

# ======================================================================
# ⚙️ GENEL AYARLAR VE GÜVENLİ SABİTLER
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []

BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2

# BIST Hisse Listesi (87 Adet)
BIST_TICKERS = [
    # Bankacılık, Finans & Holdingler (17)
    "AKBNK", "GARAN", "ISCTR", "YKBNK", "HALKB", "VAKBN", "TSKB", "KCHOL", "SAHOL",
    "AGHOL", "DOHOL", "ALARK", "BERA", "TAVHL", "ISMEN", "GEDIK", "INFO",
    # Havacılık, Lojistik & Ulaştırma (7)
    "THYAO", "PGSUS", "CLEBI", "DOAS", "TUREX", "RYSAS", "GRSEL",
    # Sanayi, Otomotiv, Beyaz Eşya & Cam (15)
    "FROTO", "TOASO", "OTKAR", "ARCLK", "VESTL", "VESBE", "SISE", "EREGL", "KRDMD",
    "BRSAN", "EGEEN", "JANTS", "PARSN", "BOSSA", "KORDS",
    # Enerji, Petrol & Kimya (16)
    "TUPRS", "PETKM", "AKSA", "ENJSA", "AYDEM", "GWIND", "AKSEN", "CWENE", "ASTOR",
    "GESAN", "KONTR", "YEOTK", "EUPWR", "ALFAS", "AHGAZ", "NTGAZ",
    # Perakende, Gıda & Hızlı Tüketim (10)
    "BIMAS", "MGROS", "SOKM", "CCOLA", "AEFES", "ULKER", "TATGD", "BANVT", "TUKAS", "EKSUN",
    # Telekomünikasyon & Teknoloji (9)
    "TCELL", "TTKOM", "ASELS", "LOGO", "MTRKS", "ARASE", "KFEIN", "LINK", "NETAS",
    # GYO, Çimento & Gayrimenkul Stratejik (8)
    "EKGYO", "TRGYO", "OZKGY", "AKCNS", "CIMSA", "BUCIM", "NUHCM", "BOBET",
    # Sağlık, İlaç & Madencilik (5)
    "MPARK", "GENIL", "DEVA", "ECILC", "TRALT"
]
BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

# ======================================================================
# 💾 SQLITE VERİTABANI (Sinyal Hafızası)
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

# ======================================================================
# 📩 TELEGRAM GÖNDERİM FONKSİYONU
# ======================================================================
def telegram_gonder(message: str):
    for cid in TELEGRAM_CHAT_IDS:
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

# ======================================================================
# 📊 MATEMATİKSEL İNDİKATÖR VE YARDIMCI FONKSİYONLAR (1'den 9'a)
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
        df['mfi'] = 100 - (100 / (1 + (pos_mf / neg_mf)))
        
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
# 📈 10. STRATEJİ: AUTO VWAP2 HESAPLAMA MOTORU
# ======================================================================
def calculate_auto_vwap2(df, tf):
    try:
        if len(df) < 50: return None
        df = df.copy()
        high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']
        hlc3 = (high + low + close) / 3
        
        if tf == "1D":
            prd2, baseAPT2, useAdapt2, volBias2, atrLen2 = 50, 20, True, 10, 50
        elif tf == "1W":
            prd2, baseAPT2, useAdapt2, volBias2, atrLen2 = 30, 40, True, 8, 70
        else:
            prd2, baseAPT2, useAdapt2, volBias2, atrLen2 = 75, 15, False, 10, 40

        # ATR Hesaplama
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr2 = tr.rolling(window=atrLen2).mean()
        atrAvg2 = atr2.ewm(alpha=1/atrLen2, adjust=False).mean()
        
        ratio2 = np.where(atrAvg2 > 0, atr2 / (atrAvg2 + 1e-10), 1.0)
        aptRaw2 = np.where(useAdapt2, baseAPT2 / np.power(ratio2, volBias2), baseAPT2)
        aptClamped2 = np.clip(aptRaw2, 5.0, 300.0)
        aptSeries2 = np.round(aptClamped2)

        vwapP2 = np.zeros(len(df))
        vwapVol2 = np.zeros(len(df))
        
        curr_vwap_p = hlc3.iloc[0] * volume.iloc[0]
        curr_vwap_v = volume.iloc[0]
        
        for i in range(1, len(df)):
            apt = aptSeries2[i]
            decay = np.exp(-np.log(2.0) / max(1.0, apt))
            alpha2 = 1.0 - decay
            
            pxv2 = hlc3.iloc[i] * volume.iloc[i]
            v0_2 = volume.iloc[i]
            
            curr_vwap_p = (1 - alpha2) * curr_vwap_p + alpha2 * pxv2
            curr_vwap_v = (1 - alpha2) * curr_vwap_v + alpha2 * v0_2
            
            vwapP2[i] = curr_vwap_p
            vwapVol2[i] = curr_vwap_v

        df['VAP'] = np.where(vwapVol2 > 0, vwapP2 / vwapVol2, close)
        df['Trend'] = np.where(close > df['VAP'], 'AL', 'SAT')
        return df
    except:
        return None

# ======================================================================
# 🚀 10 AYRI ŞARTI ÇALIŞTIRAN ANA MASTER TARAMA MOTORU
# ======================================================================
def run_all_10_screeners():
    telegram_gonder("🎯 10 FARKLI TARAMA ŞARTI (AUTO VWAP2 DAHİL) BAŞLATILDI! 🎯")
    print("10'lu Master Bot Çalıştırıldı...")
    
    s1_uzun_ralli = []
    s2_base_30 = []
    s3_matrix_wm = []
    s4_uclu_kesisim = []
    s5_leda_d = []
    s6_leda_w = []
    s7_hu_d = []
    s8_mav_w = []
    s9_hassas_dip_orta = []
    s10_auto_vwap = []

    for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
        batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
        
        try:
            data_1d = yf.download(batch, interval="1d", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            data_1wk = yf.download(batch, interval="1wk", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
            
            for full_ticker in batch:
                ticker = full_ticker.replace('.IS', '')
                
                try:
                    df_d = data_1d[full_ticker].dropna() if len(batch) > 1 else data_1d.dropna()
                except: df_d = pd.DataFrame()
                
                try:
                    df_w = data_1wk[full_ticker].dropna() if len(batch) > 1 else data_1wk.dropna()
                except: df_w = pd.DataFrame()
                
                # --- 1. UZUN VADE RALLİ (Günlük) ---
                if not df_d.empty and len(df_d) >= 180:
                    res = calculate_rsi_most_matrix(df_d['Close'])
                    if res["blue_cross_red_above_50"]:
                        s1_uzun_ralli.append(f"• <b>{ticker}</b> ({df_d['Close'].iloc[-1]:.2f}₺)")
                        
                # --- 2. RSI-MOST BASE 30 KESİŞİMİ (Günlük) ---
                if not df_d.empty and len(df_d) >= 30:
                    b_res = calculate_rsi_most_matrix(df_d['Close'])
                    if b_res["yellow_cross_30"]:
                        s2_base_30.append(f"• <b>{ticker}</b> (Günlük)")
                        
                # --- 3. MATRIX HAFTALIK ORTA HAT (50) KESİŞİMİ ---
                if not df_d.empty and len(df_d) >= 100:
                    df_w_res = df_d.resample('W').agg({'Close': 'last'}).dropna()
                    if len(df_w_res) >= 50:
                        m_res = calculate_rsi_most_matrix(df_w_res['Close'])
                        if (m_res["mov40"].iloc[-1] > 50 and m_res["mov40"].iloc[-2] <= 50):
                            s3_matrix_wm.append(f"• <b>{ticker}</b> (Haftalık)")
                            
                # --- 4. ÜÇLÜ KESİŞİM (LEDA + Mavilim + WMA79) ---
                if not df_d.empty and check_triple_confluence_signal(df_d):
                    s4_uclu_kesisim.append(f"• <b>{ticker}</b> (Günlük)")
                if not df_w.empty and check_triple_confluence_signal(df_w):
                    s4_uclu_kesisim.append(f"• <b>{ticker}</b> (Haftalık)")
                    
                # --- 5. LEDA GÜNLÜK + MACD ---
                if not df_d.empty and len(df_d) >= 35:
                    res_d = calculate_leda_indicators(df_d)
                    if res_d is not None and res_d["buy"].iloc[-1] and check_macd_cross(df_d):
                        s5_leda_d.append(f"• <b>{ticker}</b>")
                        
                # --- 6. LEDA HAFTALIK + MACD ---
                if not df_w.empty and len(df_w) >= 35:
                    res_w = calculate_leda_indicators(df_w)
                    if res_w is not None and res_w["buy"].iloc[-1] and check_macd_cross(df_w):
                        s6_leda_w.append(f"• <b>{ticker}</b>")
                        
                # --- 7. HU GÜNLÜK + MACD ---
                if not df_d.empty and check_hu_cross_signal(df_d) and check_macd_cross(df_d):
                    s7_hu_d.append(f"• <b>{ticker}</b>")
                    
                # --- 8. MAVİLİM HAFTALIK + MACD ---
                if not df_w.empty and check_mavilim_signal(df_w) and check_macd_cross(df_w):
                    s8_mav_w.append(f"• <b>{ticker}</b>")
                    
                # --- 9. HASSAS DİP VE ORTA BANT (Günlük) ---
                if not df_d.empty and len(df_d) >= 180:
                    dip, orta = calculate_rsi_signals(df_d['Close'])
                    if dip: s9_hassas_dip_orta.append(f"• <b>{ticker} (DİP)</b>")
                    if orta: s9_hassas_dip_orta.append(f"• <b>{ticker} (ORTA)</b>")

                # --- 10. AUTO VWAP2 (YENİ EKLENEN) ---
                if not df_d.empty and len(df_d) >= 50:
                    df_vwap = calculate_auto_vwap2(df_d, "1D")
                    if df_vwap is not None:
                        son_durum = df_vwap['Trend'].iloc[-1]
                        onceki_durum = df_vwap['Trend'].iloc[-2]
                        if son_durum != onceki_durum:
                            s10_auto_vwap.append(f"• <b>{ticker}</b> ({son_durum})")

        except Exception as e:
            print(f"Batch Hatası: {e}")
        
        time.sleep(DELAY_BETWEEN_BATCHES)

    # 📩 RAPORLAMA FONKSİYONU
    def report(title, items):
        if items:
            telegram_gonder(f"<b>{title}</b>\n--------------------------------------\n" + "\n".join(items))
        else:
            telegram_gonder(f"ℹ️ <b>{title}</b>\n--------------------------------------\n❌ Bu taramada koşulu sağlayan hisse yok.")

    report("💎 1. UZUN VADELİ RALLİ TARAMASI", s1_uzun_ralli)
    report("🟡 2. RSI-MOST BASE 30 KESİŞİMİ", s2_base_30)
    report("📅 3. MATRIX ORTA HAT (50) KESİŞİMİ", s3_matrix_wm)
    report("💥 4. ÜÇLÜ KESİŞİM STRATEJİSİ", s4_uclu_kesisim)
    report("📈 5. LEDA GÜNLÜK + MACD", s5_leda_d)
    report("📈 6. LEDA HAFTALIK + MACD", s6_leda_w)
    report("💎 7. HU GÜNLÜK + MACD", s7_hu_d)
    report("🌊 8. MAVİLİM HAFTALIK + MACD", s8_mav_w)
    report("🎯 9. HASSAS DİP VE ORTA BANT TARAMASI", s9_hassas_dip_orta)
    report("🔵 10. AUTO VWAP2 SİNYAL DEĞİŞİKLİĞİ", s10_auto_vwap)

if __name__ == "__main__":
    run_all_10_screeners()

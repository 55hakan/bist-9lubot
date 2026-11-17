import os
import pandas as pd
import numpy as np
import time
import requests
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ======================================================================
# 🔑 AYARLAR
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2

# 🔧 TARAMA PLANI (GÜNLÜK VE HAFTALIK)
SCAN_PLAN = [
    {"timeframe": "SAATLİK", "yf_interval": "1h", "period": "1mo", "tv_interval": "60"},
    {"timeframe": "GÜNLÜK", "yf_interval": "1d", "period": "2y", "tv_interval": "1D"},
    {"timeframe": "HAFTALIK", "yf_interval": "1wk", "period": "5y", "tv_interval": "1W"}
]

# BIST Listesi
BIST_TICKERS = ["AEFES", "AGHOL", "AKBNK", "AKSA", "AKSEN", "ALARK", "ALFAS", "ANSGR", "ARCLK", "ASELS",
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
    "YKSLN", "YUNSA","CLEBI", "TUREX", "GRSEL", "PARSN", "NTGAZ", "BANVT", "MTRKS", "LINK", "OZKGY", 
    "NUHCM", "BOBET"]

BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

# ======================================================================
# 📊 YARDIMCI HESAPLAMA FONKSİYONLARI (PINE SCRIPT BİREBİR MATEMATİĞİ)
# ======================================================================
def pine_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda weights_slice: np.dot(weights_slice, weights) / weights.sum(), raw=True)

def pine_rma(src, length):
    alpha = 1 / length
    return src.ewm(alpha=alpha, min_periods=length, adjust=False).mean()

def calculate_indicators(df):
    try:
        if len(df) < 450: return None # HU-like için en az 400+ bar gereklidir
        df = df.copy()
        high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']
        hl2 = (high + low) / 2
        hlc3 = (high + low + close) / 3
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        
        # ------------------------------------------------------------------
        # 1. DARVAS BOX HESAPLAMASI
        # ------------------------------------------------------------------
        boxLen = 5
        hhv_ref = high.rolling(boxLen).max()
        
        cond_newh = high > hhv_ref.shift(1)
        newh = high.where(cond_newh).ffill()
        
        llv = low.rolling(boxLen).min()
        box1 = high.rolling(3).max() < high.rolling(4).max()
        bars_since = cond_newh.groupby((cond_newh != cond_newh.shift()).cumsum()).cumcount()
        boxCond = (bars_since == 3) & box1
        
        top_box = newh.where(boxCond).ffill()
        bottom_box = llv.where(boxCond).ffill()
        
        df['Darvas_Top'] = top_box
        df['Darvas_Bottom'] = bottom_box

        # ------------------------------------------------------------------
        # 2. HU-LIKE HESAPLAMASI
        # ------------------------------------------------------------------
        hu_base1 = pine_wma(close, 200)
        hu_base2 = pine_wma(close, 400)
        df['HU'] = pine_wma(2 * hu_base1 - hu_base2, 20)

        # ------------------------------------------------------------------
        # 3. MAVİLİM HESAPLAMASI (K7)
        # ------------------------------------------------------------------
        k2 = pine_wma(close, 3)
        k3 = pine_wma(k2, 5)
        k4 = pine_wma(k3, 8)
        k5 = pine_wma(k4, 13)
        k6 = pine_wma(k5, 21)
        df['Mavilim'] = pine_wma(k6, 34)

        # ------------------------------------------------------------------
        # 4. MOVING AVERAGE 2 (WMA 79)
        # ------------------------------------------------------------------
        df['MA2'] = pine_wma(close, 79)

        # ------------------------------------------------------------------
        # 5. ALPHATREND HESAPLAMASI
        # ------------------------------------------------------------------
        atr_ap = tr.rolling(window=14).mean()
        mf = hlc3 * volume
        upper_mf = mf.where(hlc3 > hlc3.shift(1), 0.0)
        lower_mf = mf.where(hlc3 < hlc3.shift(1), 0.0)
        pos_mf = upper_mf.rolling(window=14).sum()
        neg_mf = lower_mf.rolling(window=14).sum()
        eps = 1e-10
        df['mfi'] = 100 - (100 / (1 + (pos_mf / (neg_mf + eps))))
        
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

        # ------------------------------------------------------------------
        # 6. SUPERTREND (TSL) HESAPLAMASI
        # ------------------------------------------------------------------
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
            if close_vals[i] > trDn[i-1]:
                trend[i] = 1
            elif close_vals[i] < trUp[i-1]:
                trend[i] = -1
            else:
                trend[i] = trend[i-1]
            tsl[i] = trUp[i] if trend[i] == 1 else trDn[i]
        df['TSL'] = tsl

        # ------------------------------------------------------------------
        # 🎯 SİNYAL KONTROLLERİ
        # ------------------------------------------------------------------
        df["leda_buy"] = (df["AlphaTrend"] > df["TSL"]) & (df["AlphaTrend"].shift(1) <= df["TSL"].shift(1))
        
        lines = ['Darvas_Top', 'HU', 'Mavilim', 'MA2']
        crossover_all = (close > df[lines].max(axis=1)) & (close.shift(1) <= df[lines].shift(1).min(axis=1))
        above_all = close > df[lines].max(axis=1)
        
        df["final_signal"] = df["leda_buy"] & (crossover_all | above_all)
        df['price_change'] = ((close - close.shift(1)) / close.shift(1)) * 100

        return df
    except Exception as e:
        return None

# ======================================================================
# 📩 GÖNDERİM
# ======================================================================
def send_telegram(msg):
    for cid in TELEGRAM_CHAT_IDS:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": cid, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
        except: pass

# ======================================================================
# 🚀 TARAMA MOTORU
# ======================================================================
def run_screener():
    print(f"🚀 LEDA + Çizgi Üstü / Kesişim Taraması Başlatıldı...")
    for plan in SCAN_PLAN:
        all_hits = []
        print(f"🔎 {plan['timeframe']} taranıyor...")
        for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
            batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
            try:
                data = yf.download(batch, interval=plan['yf_interval'], period=plan['period'],
                                     progress=False, group_by="ticker", auto_adjust=True, threads=True)
            except Exception as e:
                print(f"Hata: {e}")
                continue
            
            for ticker_full in batch:
                try:
                    if len(batch) > 1:
                        if ticker_full not in data.columns.levels[0]: continue
                        df = data[ticker_full].dropna()
                    else:
                        df = data.dropna()
                    
                    if df.empty or len(df) < 450: continue
                    df = calculate_indicators(df)
                    if df is None: continue
                    
                    if df["final_signal"].iloc[-1]:
                        ticker_clean = ticker_full.replace(".IS", "")
                        last_price = df["Close"].iloc[-1]
                        change_pct = df["price_change"].iloc[-1]
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST:{ticker_clean}&interval={plan['tv_interval']}"
                        all_hits.append(f"🔥 <a href='{tv_link}'><b>{ticker_clean}</b></a> ({last_price:.2f} TL | %{change_pct:.1f})")
                except Exception:
                    continue
            time.sleep(DELAY_BETWEEN_BATCHES)
            
        if all_hits:
            header = f"<b>🟢 {plan['timeframe']} LEDA AL + ÇİZGİ TESPİT SİNYALİ</b>\n\n"
            for j in range(0, len(all_hits), 20):
                send_telegram(header + "\n".join(all_hits[j:j+20]))
        else:
            print(f"[{plan['timeframe']}] Şartları sağlayan hisse bulunamadı.")

if __name__ == "__main__":
    run_screener()

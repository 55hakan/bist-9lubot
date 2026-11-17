import os
import requests
import pandas as pd
import numpy as np
import time
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ======================================================================
# 🔑 GÜVENLİ AYARLAR
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2

# 🔧 TARAMA PLANI
SCAN_PLAN = [
    {"timeframe": "SAATLİK", "yf_interval": "60m", "period": "3mo", "tv_interval": "60"},
    {"timeframe": "GÜNLÜK", "yf_interval": "1d", "period": "max", "tv_interval": "D"},
    {"timeframe": "HAFTALIK", "yf_interval": "1wk", "period": "max", "tv_interval": "W"}
]

# BIST Listesi
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
    "YKSLN", "YUNSA","CLEBI", "TUREX", "GRSEL", "PARSN", "NTGAZ", "BANVT", "MTRKS", "LINK", "OZKGY", 
    "NUHCM", "BOBET"
]

BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

# ======================================================================
# 📊 HASSAS HESAPLAMA (PINE SCRIPT UYUMLU)
# ======================================================================
def pine_rma(src, length):
    alpha = 1 / length
    return src.ewm(alpha=alpha, min_periods=length, adjust=False).mean()

def calculate_indicators(df):
    try:
        if len(df) < 30: return None
        df = df.copy()
        high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']
        hl2 = (high + low) / 2
        hlc3 = (high + low + close) / 3
        
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        
        # --- ALPHATREND ---
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
        
        # --- SUPERTREND ---
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
        df['Trend'] = np.where(df['AlphaTrend'] > df['TSL'], 'AL', 'SAT')
        return df
    except:
        return None

# ======================================================================
# 🚀 TARAMA MOTORU
# ======================================================================
def run_screener():
    print(f"🚀 LEDA Taraması Başlatıldı...")
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
                        
                    if df.empty or len(df) < 30: continue
                    
                    df = calculate_indicators(df)
                    if df is None: continue
                    
                    son_durum = df['Trend'].iloc[-1]
                    onceki_durum = df['Trend'].iloc[-2]
                    
                    if son_durum != onceki_durum:
                        ticker_clean = ticker_full.replace(".IS", "")
                        last_price = df["Close"].iloc[-1]
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST:{ticker_clean}&interval={plan['tv_interval']}"
                        
                        msg_line = f"🔵 <a href='{tv_link}'><b>{ticker_clean}</b></a> ({last_price:.2f} TL) | <b>{son_durum}</b>"
                        all_hits.append(msg_line)
                except Exception:
                    continue
            time.sleep(DELAY_BETWEEN_BATCHES)
            
        # Sinyal olsun veya olmasın her periyot için bilgi raporu gönderilir
        if all_hits:
            header = f"<b>🔥 {plan['timeframe']} SİNYAL DEĞİŞİKLİĞİ</b>\n\n"
            for j in range(0, len(all_hits), 20):
                send_telegram(header + "\n".join(all_hits[j:j+20]))
        else:
            # Değişiklik yoksa sistemin çalıştığını bildiren sakin durum mesajı
            info_msg = f"ℹ️ <b>{plan['timeframe']} TARAMA RAPORU</b>\n--------------------------------------\nHer şey normal, trend devam ediyor. Sinyal değiştiren hisse bulunamadı."
            send_telegram(info_msg)

# ======================================================================
# 📩 GÖNDERİM
# ======================================================================
def send_telegram(msg):
    for cid in TELEGRAM_CHAT_IDS:
        if not cid or not BOT_TOKEN:
            continue
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": cid, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
        except: pass

if __name__ == "__main__":
    run_screener()

import time
import requests
import pandas as pd
import sqlite3
import traceback
import yfinance as yf
import numpy as np
import sys
import os
from typing import List

# ======================================================================
# 🔑 TELEGRAM AYARLARI
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    MAX = 3900
    for i in range(0, len(msg), MAX):
        part = msg[i:i+MAX]
        for chat in TELEGRAM_CHAT_IDS:
            try:
                requests.post(
                    url,
                    data={
                        "chat_id": chat,
                        "text": part,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    },
                    timeout=10
                )
            except:
                pass
        time.sleep(1)

telegram_gonder = send_telegram

# ======================================================================
# 💾 PERSISTENT HAFIZA / SQLITE
# ======================================================================
conn = sqlite3.connect('rsi_most_matrix_signals.db')
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
# 📊 Pine Script RSI-MOST Matrix 1 HESAPLAMA MOTORU
# ======================================================================
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_rsi_most_matrix(series_close: pd.Series, 
                            rsi_len=14, most_sma=3, most_ema=2, 
                            mov_short=5, mov_mid=40, mov_long=160):
    
    # 1. RSI ve MOST (Base/Sarı Çizgi)
    rsi_val = calculate_rsi(series_close, rsi_len)
    sma_rsi = rsi_val.rolling(window=most_sma).mean()
    base = sma_rsi.ewm(span=most_ema, adjust=False).mean() # Sarı (Base)
    
    # 2. Hareketli Ortalamalar
    mov5 = base.ewm(span=mov_short, adjust=False).mean()   # Yeşil (5)
    mov40 = base.ewm(span=mov_mid, adjust=False).mean()    # Mavi (40)
    mov160 = base.ewm(span=mov_long, adjust=False).mean()  # Kırmızı (160)
    
    # --- SON 2 MUM KONTROLLERİ ---
    
    # Şart (YENİ/TEK): Mavi (MOV40) Kırmızı'yı (MOV160) 50 Yakınında/Üstünde YUKARI Kesti (Uzun Vade Ralli)
    bm_cross_last = (mov40.iloc[-1] > mov160.iloc[-1]) and (mov40.iloc[-2] <= mov160.iloc[-2])
    bm_cross_prev = (mov40.iloc[-2] > mov160.iloc[-2]) and (mov40.iloc[-3] <= mov160.iloc[-3])
    
    near_50_last = mov40.iloc[-1] >= 48
    near_50_prev = mov40.iloc[-2] >= 48
    
    blue_cross_red_above_50 = (bm_cross_last and near_50_last) or (bm_cross_prev and near_50_prev)
    
    return {
        "mov40": mov40,
        "mov160": mov160,
        "blue_cross_red_above_50": blue_cross_red_above_50
    }

# ======================================================================
# 🚀 GÜNLÜK TARAMA MOTORU
# ======================================================================
def process_daily_scans(df_symbols: List[str]):
    print(f"    -> Uzun Vade Ralli Taraması başlatılıyor...")
    batch_size = 50
    for i in range(0, len(df_symbols), batch_size):
        batch = [f"{s}.IS" for s in df_symbols[i:i+batch_size]]
        try:
            data = yf.download(batch, period="max", interval="1d", progress=False, group_by='ticker', auto_adjust=True, threads=True)
            
            for ticker_full in batch:
                ticker = ticker_full.replace('.IS', '')
                try:
                    df_daily = data[ticker_full].dropna() if len(batch) > 1 else data.dropna()
                    if df_daily.empty or len(df_daily) < 180: # mov160 için minimum mum şartı
                        continue
                    
                    close_price = df_daily['Close'].iloc[-1]
                    matrix_res = calculate_rsi_most_matrix(df_daily['Close'])
                    
                    date_str = df_daily.index[-1].strftime('%Y-%m-%d')
                    link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                    
                    # TEK ŞART: MAVİ, KIRMIZIYI 50 SEVİYESİ VE ÜSTÜNDE KESTİ (UZUN VADE RALLİ)
                    if matrix_res["blue_cross_red_above_50"]:
                        sig_id = f"RSI_MATRIX_BLUE_RED_50_{date_str}"
                        if not was_sent_before(ticker, sig_id):
                            msg = (
                                f"💎 <b>UZUN VADELİ RALLİ</b>\n"
                                f"🏷️ <b>Sembol:</b> <a href='{link}'><b>{ticker} (Günlük)</b></a>\n"
                                f"💰 <b>Fiyat:</b> {close_price:.2f} TL\n"
                            )
                            telegram_gonder(msg)
                            save_signal(ticker, sig_id, close_price)
                            
                except Exception:
                    continue
                    
        except Exception:
            continue
            
        time.sleep(1)

# ======================================================================
# 🔄 BOT ANA DÖNGÜSÜ
# ======================================================================
def bot_loop(interval=3600):
    telegram_gonder("🎯 UZUN VADE RALLİ TARAYICI BAŞLADI ! 🎯")
    print("Bot Başlatıldı...")
    try:
        while True:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Tarama Başlıyor...")
            process_daily_scans(all_symbols)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Tarama tamamlandı. {interval} sn bekleniyor...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        telegram_gonder("🛑 TARAMA SONA ERDİ.")
        print("Bot durduruldu.")
    except Exception as e:
        error_msg = f"❌ Bot beklenmedik bir hata verdi: {type(e).__name__}: {str(e)}"
        print(error_msg, file=sys.stderr)
        traceback.print_exc()
        telegram_gonder(error_msg)
    finally:
        conn.close()

if __name__ == "__main__":
    all_symbols = [
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
    
    bot_loop(interval=3600)

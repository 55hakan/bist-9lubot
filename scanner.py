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

BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2

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
            resp = req.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data, timeout=15)
            if resp.status_code != 200:
                print(f"Telegram API Hatası ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"Telegram Gönderim Hatası: {e}")

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
    return bool((macd.iloc[-1] > signal.iloc[-1]) and (macd.iloc[-2] <= signal.iloc[-2]))

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
        close, high, low = df_target['Close'], df_target['High'], df_target['Low']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr_value = tr.rolling(window=14).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        stop_loss = current_price - (atr_value * 1.5)
        target_price = current_price + (atr_value * 3.0)
        risk_amt = current_price - stop_loss
        reward_amt = target_price - current_price
        rr_ratio = reward_amt / risk_amt if risk_amt > 0 else 0
        
        rsi_daily = calculate_rsi(close, 14).iloc[-1]
        rsi_weekly = calculate_rsi(df_weekly['Close'], 14).iloc[-1] if df_weekly is not None and len(df_weekly) > 14 else rsi_daily
        
        adx_val, adx_status = calculate_adx(df_target, 14)
        mfi_val = calculate_mfi(df_target, 14)
        money_flow = "PARA GİRİŞİ ✅" if mfi_val > 50 else "PARA ÇIKIŞI ❌"
        
        return {
            "price": current_price, "rsi_d": rsi_daily, "rsi_w": rsi_weekly,
            "adx": adx_val, "adx_status": adx_status, "mfi": mfi_val,
            "money_flow": money_flow, "stop_loss": stop_loss, "target": target_price, "rr": rr_ratio
        }
    except:
        return None

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
        pos_mf = mf.where(hlc3 > hlc3.shift(1), 0.0).rolling(window=14).sum()
        neg_mf = mf.where(hlc3 < hlc3.shift(1), 0.0).rolling(window=14).sum()
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
        trUp, trDn, tsl, trend = np.zeros(len(df)), np.zeros(len(df)), np.zeros(len(df)), np.ones(len(df))
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

def check_mavilim_signal(df: pd.DataFrame) -> bool:
    if len(df) < 55: return False
    df = df.copy()
    k1 = df['Close']
    k2 = wma(k1, 3); k3 = wma(k2, 5); k4 = wma(k3, 8)
    k5 = wma(k4, 13); k6 = wma(k5, 21)
    df['K7'] = wma(k6, 34)
    return bool((df['Close'].iloc[-1] > df['K7'].iloc[-1]) and (df['Close'].iloc[-2] <= df['K7'].iloc[-2]))

def check_hu_cross_signal(df: pd.DataFrame) -> bool:
    if len(df) < 420: return False
    df = df.copy()
    hu_base1 = wma(df['Close'], 200)
    hu_base2 = wma(df['Close'], 400)
    hu_raw = (2 * hu_base1) - hu_base2
    df['HU_Line'] = wma(hu_raw, 20)
    return bool((df['Close'].iloc[-1] > df['HU_Line'].iloc[-1]) and (df['Close'].iloc[-2] <= df['HU_Line'].iloc[-2]))

def calculate_rsi_most_matrix(series_close: pd.Series, rsi_len=14, most_sma=3, most_ema=2, mov_short=5, mov_mid=40, mov_long=160):
    rsi_val = calculate_rsi(series_close, rsi_len)
    sma_rsi = rsi_val.rolling(window=most_sma).mean()
    base = sma_rsi.ewm(span=most_ema, adjust=False).mean()
    mov40 = base.ewm(span=mov_mid, adjust=False).mean()
    mov160 = base.ewm(span=mov_long, adjust=False).mean()
    
    yellow_cross_30 = (base.iloc[-1] > 30 and base.iloc[-2] <= 30)
    bm_cross = (mov40.iloc[-1] > mov160.iloc[-1] and mov40.iloc[-2] <= mov160.iloc[-2])
    near_50 = mov40.iloc[-1] >= 48
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
    
    yellow_cross_green = (base.iloc[-1] > mov5.iloc[-1] and base.iloc[-2] <= mov5.iloc[-2])
    cond_red_near_50 = (mov160.iloc[-1] < 50) and (mov160.iloc[-1] >= 40)
    cond_blue_below_red = mov40.iloc[-1] < mov160.iloc[-1]
    
    yellow_cross_30 = (base.iloc[-1] > 30 and base.iloc[-2] <= 30)
    yellow_bottom = (base.iloc[-1] <= 40)
    dip_signal = (yellow_cross_30 or (yellow_cross_green and yellow_bottom)) and cond_red_near_50 and cond_blue_below_red
    
    yellow_mid = (40 <= base.iloc[-1] <= 45)
    orta_signal = yellow_cross_green and yellow_mid and cond_red_near_50 and cond_blue_below_red
    return dip_signal, orta_signal

# ======================================================================
# 🚀 PRO BÜLTEN KART FORMATLAYICI
# ======================================================================
def send_pro_report(strategy_title, ticker, tv_link, pro, badge=""):
    badge_text = f"\n🔥 <b>{badge}</b>\n" if badge else ""
    msg = (
        f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n"
        f"📌 <b>Strateji:</b> {strategy_title}{badge_text}\n"
        f"🎯 <b>Hisse:</b> <a href='{tv_link}'><b>{ticker}</b></a>\n"
        f"💲 <b>Fiyat:</b> {pro['price']:.2f} ₺\n\n"
        f"📊 <b>Osilatörler</b>\n"
        f"💹 Günlük RSI: <b>{pro['rsi_d']:.2f}</b>\n"
        f"💹 Haftalık RSI: <b>{pro['rsi_w']:.2f}</b>\n"
        f"💪 ADX: <b>{pro['adx']:.2f} ({pro['adx_status']})</b>\n"
        f"💥 <b>{pro['money_flow']}</b> (MFI: {pro['mfi']:.1f})\n\n"
        f"⚔️ <b>RİSK & HEDEF PLANI</b>\n"
        f"🛑 <b>Stop-Loss:</b> <code>{pro['stop_loss']:.2f} ₺</code>\n"
        f"🎯 <b>Hedef (TP1):</b> <code>{pro['target']:.2f} ₺</code>\n\n"
        f"<i>ℹ️ Otomatik Akıllı Sinyal Sistemi</i>"
    )
    telegram_gonder(msg)

# ======================================================================
# 🚀 11 STRATEJİ + SAATLİK SAT - ANA TARAMA MOTORU
# ======================================================================
def run_targeted_screener():
    init_db()
    print(f"🚀 Seçilen Strateji Çalıştırılıyor: {SELECTED_STRATEGY}")
    telegram_gonder(
        f"🎯 <b>Emekli Sinyal Tarama Başlatıldı.</b>\n"
        f"📊 Mod: <b>{SELECTED_STRATEGY}</b>\n"
        f"🤖 Bot için <b>11 Özel Strateji</b> aktif.\n"
        f"🔍 Kendi kullandığınız indikatörler ile kontrol ediniz.\n"
        f"🤖 Bot aktif ve tarama gerçekleştiriliyor...\n"
        f"⚠️ <i>Sinyaller bilgi amaçlıdır, Yatırım Tavsiyesi Değildir.</i>"
    )

    results_log = []
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

    try:
        for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
            batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
            try:
                data_1d = yf.download(batch, interval="1d", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
                data_1wk = yf.download(batch, interval="1wk", period="max", progress=False, group_by='ticker', auto_adjust=True, threads=False)
                data_1h = yf.download(batch, interval="1h", period="60d", progress=False, group_by='ticker', auto_adjust=True, threads=False)

                for full_ticker in batch:
                    ticker = full_ticker.replace('.IS', '')
                    
                    try: 
                        df_d = data_1d[full_ticker].dropna() if len(batch) > 1 else data_1d.dropna()
                        if isinstance(df_d.columns, pd.MultiIndex): df_d = df_d.droplevel(1, axis=1)
                    except: df_d = pd.DataFrame()

                    try: 
                        df_w = data_1wk[full_ticker].dropna() if len(batch) > 1 else data_1wk.dropna()
                        if isinstance(df_w.columns, pd.MultiIndex): df_w = df_w.droplevel(1, axis=1)
                    except: df_w = pd.DataFrame()

                    try: 
                        df_h = data_1h[full_ticker].dropna() if len(batch) > 1 else data_1h.dropna()
                        if isinstance(df_h.columns, pd.MultiIndex): df_h = df_h.droplevel(1, axis=1)
                    except: df_h = pd.DataFrame()

                    # --- SAATLİK LEDA SAT KONTROLÜ (Sadece Kesin Son Mum) ---
                    try:
                        if not df_h.empty and len(df_h) >= 30:
                            res_h = calculate_leda_indicators(df_h)
                            if res_h is not None and "sell" in res_h.columns and bool(res_h["sell"].iloc[-1]):
                                st_name = "⚠️ SAATLİK LEDA SAT SİNYALİ"
                                if not signal_already_sent(ticker, st_name):
                                    tv_link_h = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=60"
                                    pro_h = calculate_pro_metrics(df_h, df_w)
                                    if pro_h:
                                        s_hourly_sell.append((ticker, tv_link_h, pro_h, st_name))
                                        results_log.append({"Hisse": ticker, "Strateji": st_name, "Zaman Dilimi": "1 Saat", "Link": tv_link_h})
                                        mark_signal_sent(ticker, st_name)
                    except: pass

                    daily_signals_list = []
                    weekly_signals_list = []

                    # 1. Uzun Vade Ralli
                    ralli_d = False
                    if not df_d.empty and len(df_d) >= 180:
                        if calculate_rsi_most_matrix(df_d['Close'])["blue_cross_red_above_50"]:
                            ralli_d = True
                            daily_signals_list.append("Ralli")

                    # 2. Base 30
                    base_30_d = False
                    if not df_d.empty and len(df_d) >= 30:
                        if calculate_rsi_most_matrix(df_d['Close'])["yellow_cross_30"]:
                            base_30_d = True
                            daily_signals_list.append("RSI-MOST 30")

                    # 3. Matrix Orta Hat 50
                    matrix_wm = False
                    if not df_d.empty and len(df_d) >= 100:
                        df_w_res = df_d.resample('W').agg({'Close': 'last'}).dropna()
                        if len(df_w_res) >= 50:
                            m_res = calculate_rsi_most_matrix(df_w_res['Close'])
                            if m_res["mov40"].iloc[-1] > 50 and m_res["mov40"].iloc[-2] <= 50:
                                matrix_wm = True
                                weekly_signals_list.append("RSI-MİST 50")

                    # 4. Üçlü Kesişim
                    uclu_d = not df_d.empty and check_hu_cross_signal(df_d)
                    uclu_w = not df_w.empty and check_hu_cross_signal(df_w)
                    if uclu_d: daily_signals_list.append("Üçlü Kesişim")
                    if uclu_w: weekly_signals_list.append("Üçlü Kesişim")

                    # 5 & 6. Leda Günlük
                    leda_d_buy = False
                    leda_d_macd_ok = False
                    if not df_d.empty and len(df_d) >= 35:
                        res_leda_d = calculate_leda_indicators(df_d)
                        if res_leda_d is not None and res_leda_d["buy"].iloc[-1]:
                            leda_d_buy = True
                            daily_signals_list.append("Leda Günlük")
                            if check_macd_cross(df_d): leda_d_macd_ok = True

                    # 7 & 8. Leda Haftalık
                    leda_w_buy = False
                    leda_w_macd_ok = False
                    if not df_w.empty and len(df_w) >= 35:
                        res_leda_w = calculate_leda_indicators(df_w)
                        if res_leda_w is not None and res_leda_w["buy"].iloc[-1]:
                            leda_w_buy = True
                            weekly_signals_list.append("Leda Haftalık")
                            if check_macd_cross(df_w): leda_w_macd_ok = True

                    # 9 & 10. Mavilim Haftalık
                    mav_w_cross = False
                    mav_w_macd_ok = False
                    if not df_w.empty and check_mavilim_signal(df_w):
                        mav_w_cross = True
                        weekly_signals_list.append("Mavilim")
                        if check_macd_cross(df_w): mav_w_macd_ok = True

                    # 11. Hassas Dip ve Orta Bant
                    dip_d, orta_d = False, False
                    if not df_d.empty and len(df_d) >= 180:
                        dip_d, orta_d = calculate_rsi_signals(df_d['Close'])
                        if dip_d or orta_d: daily_signals_list.append("Hassas Dip")

                    # --- ÇİFT ONAY KONTROLÜ ---
                    is_double = (len(daily_signals_list) > 0) and (len(weekly_signals_list) > 0)
                    confluence_badge = f"⭐ ÇİFT ONAY: [{' + '.join(daily_signals_list)}] & [{' + '.join(weekly_signals_list)}]" if is_double else ""

                    def process_signal(st_key, st_name, condition, interval, is_weekly=False):
                        if condition and (SELECTED_STRATEGY in ["Hepsi", st_key]):
                            if not signal_already_sent(ticker, st_name):
                                tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval={interval}"
                                target_df = df_w if is_weekly else df_d
                                pro_m = calculate_pro_metrics(target_df, df_w)
                                if pro_m:
                                    items_list = {
                                        "s1": s1_uzun_ralli, "s2": s2_base_30, "s3": s3_matrix_wm,
                                        "s4": s4_uclu_kesisim, "s5": s5_leda_d_macd, "s6": s6_leda_d_sade,
                                        "s7": s7_leda_w_macd, "s8": s8_leda_w_sade, "s9": s9_mav_w_macd,
                                        "s10": s10_mav_w_sade, "s11": s11_hassas_dip_orta
                                    }.get(st_key)
                                    if items_list is not None:
                                        items_list.append((ticker, tv_link, pro_m, confluence_badge))
                                        results_log.append({"Hisse": ticker, "Strateji": st_name, "Detay": confluence_badge, "Link": tv_link})
                                        mark_signal_sent(ticker, st_name)

                    process_signal("s1", "💎 1. RALLİ", ralli_d, "D")
                    process_signal("s2", "🟡 2. RSI-MOST 30", base_30_d, "D")
                    process_signal("s3", "📅 3. RSI-MİST 50", matrix_wm, "W", is_weekly=True)
                    process_signal("s4", "💥 4. ÜÇLÜ KESİŞİM", uclu_d or uclu_w, "D")
                    process_signal("s5", "📈 5. ÖZEL GÜNLÜK", leda_d_buy and leda_d_macd_ok, "D")
                    process_signal("s6", "📊 6. LEDA GÜNLÜK", leda_d_buy, "D")
                    process_signal("s7", "📈 7. ÖZEL HAFTALIK", leda_w_buy and leda_w_macd_ok, "W", is_weekly=True)
                    process_signal("s8", "📊 8. LEDA HAFTALIK", leda_w_buy, "W", is_weekly=True)
                    process_signal("s9", "🌊 9. MAVİLİM + MACD", mav_w_cross and mav_w_macd_ok, "W", is_weekly=True)
                    process_signal("s10", "🌊 10. MAVİLİM", mav_w_cross, "W", is_weekly=True)
                    process_signal("s11", "🎯 11. HASSAS DİP", dip_d or orta_d, "D")

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
                msg = (
                    f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n"
                    f"📌 <b>Strateji:</b> {title}\n\n"
                    f"❌ <i>Bu taramada koşulu sağlayan hisse yok.</i>\n\n"
                    f"<i>ℹ️ Otomatik Akıllı Sinyal Sistemi</i>"
                )
                telegram_gonder(msg)

        if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk", "Leda Haftalik"]:
            report_strategy("⏰ SAATLİK SAT SİNYALİ", s_hourly_sell)

        report_strategy("💎 1. RALLİ", s1_uzun_ralli)
        report_strategy("🟡 2. RSI-MOST 30", s2_base_30)
        report_strategy("📅 3. RSI-MİST 50", s3_matrix_wm)
        report_strategy("💥 4. ÜÇLÜ KESİŞİM", s4_uclu_kesisim)
        report_strategy("📈 5. ÖZEL GÜNLÜK", s5_leda_d_macd)
        report_strategy("📊 6. LEDA GÜNLÜK", s6_leda_d_sade)
        report_strategy("📈 7. ÖZEL HAFTALIK", s7_leda_w_macd)
        report_strategy("📊 8. LEDA HAFTALIK", s8_leda_w_sade)
        report_strategy("🌊 9. MAVİLİM + MACD", s9_mav_w_macd)
        report_strategy("🌊 10. MAVİLİM", s10_mav_w_sade)
        report_strategy("🎯 11. HASSAS DİP", s11_hassas_dip_orta)

    except Exception as e:
        print(f"Genel Tarama Hatası: {e}")
        traceback.print_exc()
    finally:
        try:
            telegram_gonder("🏁 <b>Pro Tarama ve Kontrol Tamamlandı.</b>")
        except Exception as ex:
            print(f"Bitiş mesajı gönderilemedi: {ex}")

    print("\n" + "="*50)
    print("🏁 TARAMA TAMAMLANDI - SONUÇ ÖZETİ")
    print("="*50)
    if results_log:
        df_results = pd.DataFrame(results_log)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df_results.to_string(index=False))
    else:
        print("❌ Bu taramada herhangi bir yeni strateji sinyali bulunamadı.")
    print("="*50)

if __name__ == "__main__":
    run_targeted_screener()

import os
import requests
import pandas as pd
import numpy as np
import time
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ======================================================================
# 🔑 GÜVENLİ AYARLAR (Çalışan kodunuzdaki TELEGRAM_TOKEN uyumlu)
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")
BATCH_SIZE = 30
DELAY_BETWEEN_BATCHES = 2.0

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
# 📩 TELEGRAM GÖNDERİM FONKSİYONU
# ======================================================================
def telegram_gonder(message: str):
    for cid in TELEGRAM_CHAT_IDS:
        if not cid or not BOT_TOKEN: continue
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
        if df is None or len(df) < (period * 2): return 20.0, "ZAYIF / YATAY ⚖️"
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
            "adx": adx_val, "adx_status": adx_status, "mfi": mfi_val, "money_flow": money_flow,
            "stop_loss": stop_loss, "target": target_price, "rr": rr_ratio,
            "score": 85, "score_durum": "GÜÇLÜ BOĞA 🚀"
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

# ======================================================================
# 🚀 ANA TARAMA MOTORU
# ======================================================================
def run_targeted_screener():
    print(f"🚀 Pro Sinyal Tarama Başlatıldı. Mod: {SELECTED_STRATEGY}")
    telegram_gonder(
        f"🎯 <b>Emekli Pro Tarama Başlatıldı.</b>\n"
        f"📊 Mod: <b>{SELECTED_STRATEGY}</b>\n"
        f"🤖 Sistem aktif ve tarama gerçekleştiriliyor..."
    )

    s1_uzun_ralli, s4_uclu_kesisim = [], []
    s5_leda_d, s6_leda_w, s7_hu_d, s8_mav_w = [], [], [], []
    s9_leda_hourly_sell = []

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
                    df_w = data_1wk[full_ticker].dropna() if len(batch) > 1 else data_1wk.dropna()
                    df_h = data_1h[full_ticker].dropna() if len(batch) > 1 else data_1h.dropna()
                except:
                    continue

                # Saatlik Leda Sat Kontrolü
                if not df_h.empty and len(df_h) >= 30:
                    res_h = calculate_leda_indicators(df_h)
                    if res_h is not None and "sell" in res_h.columns and res_h["sell"].iloc[-1]:
                        tv_link_h = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=60"
                        pro_h = calculate_pro_metrics(df_h, df_w)
                        if pro_h:
                            s9_leda_hourly_sell.append((ticker, tv_link_h, pro_h, "⚠️ SAATLİK LEDA SAT SİNYALİ"))

        except Exception as e:
            print(f"Batch Hatası: {e}")

        time.sleep(DELAY_BETWEEN_BATCHES)

    # Raporlama ve her durumda bilgi mesajı gönderme (Çalışan kod mantığı)
    def report_strategy(title, items):
        if items:
            for item in items:
                ticker, tv_link, pro, badge = item
                badge_text = f"\n🔥 <b>{badge}</b>\n" if badge else ""
                msg = (
                    f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n"
                    f"📌 <b>Strateji:</b> {title}{badge_text}\n"
                    f"🎯 <b>Hisse:</b> <a href='{tv_link}'><b>{ticker}</b></a>\n"
                    f"💲 <b>Fiyat:</b> {pro['price']:.2f} ₺\n"
                    f"⭐ <b>Skor:</b> <b>{pro['score']} / 100 ({pro['score_durum']})</b>\n\n"
                    f"📊 <b>Osilatörler</b>\n"
                    f"💹 Günlük RSI: <b>{pro['rsi_d']:.2f}</b> | Haftalık RSI: <b>{pro['rsi_w']:.2f}</b>\n"
                    f"💪 ADX: <b>{pro['adx']:.2f} ({pro['adx_status']})</b>\n"
                    f"💥 <b>{pro['money_flow']}</b> (MFI: {pro['mfi']:.1f})\n\n"
                    f"⚔️ <b>RİSK & HEDEF PLANI</b>\n"
                    f"🛑 <b>Stop:</b> <code>{pro['stop_loss']:.2f} ₺</code> | 🎯 <b>Hedef:</b> <code>{pro['target']:.2f} ₺</code>"
                )
                telegram_gonder(msg)
        else:
            telegram_gonder(f"ℹ️ <b>Strateji:</b> <b>{title}</b>\nHer şey normal, bu periyotta tetiklenen hisse yok.")

    report_strategy("⏰ SAATLİK LEDA SAT SİNYALİ", s9_leda_hourly_sell)
    telegram_gonder("🏁 Pro Tarama ve Kontrol Tamamlandı.")

if __name__ == "__main__":
    run_targeted_screener()

import os
import time
import traceback
import numpy as np
import pandas as pd
import requests as req
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ======================================================================
# ⚙️ GENEL AYARLAR VE GÜVENLİ SABİTLER
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_CHAT_IDS = [CHAT_ID] if CHAT_ID else []
SELECTED_STRATEGY = os.environ.get("SELECTED_STRATEGY", "Hepsi")
BATCH_SIZE = 30
DELAY_BETWEEN_BATCHES = 1

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
# 📩 TELEGRAM GÖNDERİM FONKSİYONU
# ======================================================================
def telegram_gonder(message: str):
    for cid in TELEGRAM_CHAT_IDS:
        if not cid or not BOT_TOKEN: 
            continue
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
        if df_target is None or len(df_target) < 30: return None
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
    mov40 = base.ewm(span=mov_mid, adjust=False).mean()
    mov160 = base.ewm(span=mov_long, adjust=False).mean()
    bm_cross = (mov40.iloc[-1] > mov160.iloc[-1] and mov40.iloc[-2] <= mov160.iloc[-2]) or (mov40.iloc[-2] > mov160.iloc[-2] and mov40.iloc[-3] <= mov160.iloc[-3])
    near_50 = mov40.iloc[-1] >= 48 or mov40.iloc[-2] >= 48
    blue_cross_red_above_50 = bm_cross and near_50
    return {"blue_cross_red_above_50": blue_cross_red_above_50}

# ======================================================================
# 🚀 PRO BÜLTEN KART FORMATLAYICI
# ======================================================================
def send_pro_report(strategy_title, ticker, tv_link, pro, badge=""):
    badge_text = f"\n🔥 <b>{badge}</b>\n" if badge else ""
    msg = (
        f"💎 <b>EMEKLİ PRO BÜLTEN</b> 💎\n"
        f"📌 <b>Strateji:</b> {strategy_title}{badge_text}\n"
        f"🎯 <b>Hisse:</b> <a href='{tv_link}'><b>{ticker}</b></a>\n"
        f"💲 <b>Fiyat:</b> {pro['price']:.2f} ₺\n"
        f"⭐ <b>Skor:</b> <b>{pro['score']} / 100 ({pro['score_durum']})</b>\n\n"
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
# 🚀 ANA TARAMA MOTORU
# ======================================================================
def run_targeted_screener():
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

    s1_uzun_ralli, s4_uclu_kesisim = [], []
    s5_leda_d, s6_leda_w, s7_hu_d, s8_mav_w = [], [], [], []
    s9_leda_hourly_sell = []

    for i in range(0, len(BIST_STOCK_LIST), BATCH_SIZE):
        batch = BIST_STOCK_LIST[i:i+BATCH_SIZE]
        try:
            data_1d = yf.download(batch, interval="1d", period="1mo", progress=False, group_by='ticker', auto_adjust=True, threads=False)
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

                try:
                    if not df_h.empty and len(df_h) >= 30:
                        res_h = calculate_leda_indicators(df_h)
                        if res_h is not None and "sell" in res_h.columns and res_h["sell"].iloc[-1]:
                            tv_link_h = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=60"
                            pro_h = calculate_pro_metrics(df_h, df_w)
                            if pro_h:
                                s9_leda_hourly_sell.append((ticker, tv_link_h, pro_h, "⚠️ SAATLİK LEDA SAT SİNYALİ"))
                except Exception as e:
                    print(f"Saatli Leda Hatası {ticker}: {e}")

                daily_signals = []
                ralli_d = False
                try:
                    if not df_d.empty and len(df_d) >= 180:
                        res_ralli = calculate_rsi_most_matrix(df_d['Close'])
                        if res_ralli["blue_cross_red_above_50"]:
                            ralli_d = True
                            daily_signals.append("Ralli Başlangıç")
                except: pass

                uclu_d = False
                try:
                    if not df_d.empty and check_triple_confluence_signal(df_d):
                        uclu_d = True
                        daily_signals.append("Üçlü Kesişim")
                except: pass

                leda_d = False
                try:
                    if not df_d.empty and len(df_d) >= 35:
                        res_leda_d = calculate_leda_indicators(df_d)
                        if res_leda_d is not None and res_leda_d["buy"].iloc[-1] and check_macd_cross(df_d):
                            leda_d = True
                            daily_signals.append("Leda Günlük")
                except: pass

                hu_d = False
                try:
                    if not df_d.empty and check_hu_cross_signal(df_d) and check_macd_cross(df_d):
                        hu_d = True
                        daily_signals.append("HU Günlük")
                except: pass

                weekly_signals = []
                uclu_w = False
                try:
                    if not df_w.empty and check_triple_confluence_signal(df_w):
                        uclu_w = True
                        weekly_signals.append("Üçlü Kesişim")
                except: pass

                leda_w = False
                try:
                    if not df_w.empty and len(df_w) >= 35:
                        res_leda_w = calculate_leda_indicators(df_w)
                        if res_leda_w is not None and res_leda_w["buy"].iloc[-1] and check_macd_cross(df_w):
                            leda_w = True
                            weekly_signals.append("Leda Haftalık")
                except: pass

                mav_w = False
                try:
                    if not df_w.empty and check_mavilim_signal(df_w) and check_macd_cross(df_w):
                        mav_w = True
                        weekly_signals.append("Mavilim Haftalık")
                except: pass

                is_double_confluence = len(daily_signals) > 0 and len(weekly_signals) > 0

                if is_double_confluence:
                    tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                    pro_w = calculate_pro_metrics(df_w, df_w)
                    if pro_w:
                        badge_text = f"⭐ ÇİFTE ONAY: ({' + '.join(daily_signals)}) & ({' + '.join(weekly_signals)})"
                        if (SELECTED_STRATEGY in ["Hepsi", "Uzun Vade Ralli"]) and ralli_d:
                            s1_uzun_ralli.append((ticker, tv_link, pro_w, badge_text))
                        if (SELECTED_STRATEGY in ["Hepsi", "Uclu Kesisim"]) and (uclu_d or uclu_w):
                            s4_uclu_kesisim.append((ticker, tv_link, pro_w, badge_text))
                        if (SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk"]) and leda_d:
                            s5_leda_d.append((ticker, tv_link, pro_w, badge_text))
                        if (SELECTED_STRATEGY in ["Hepsi", "Leda Haftalik"]) and leda_w:
                            s6_leda_w.append((ticker, tv_link, pro_w, badge_text))
                        if (SELECTED_STRATEGY in ["Hepsi", "HU Gunluk"]) and hu_d:
                            s7_hu_d.append((ticker, tv_link, pro_w, badge_text))
                        if (SELECTED_STRATEGY in ["Hepsi", "Mavilim Haftalik"]) and mav_w:
                            s8_mav_w.append((ticker, tv_link, pro_w, badge_text))
                else:
                    if SELECTED_STRATEGY in ["Hepsi", "Uzun Vade Ralli"] and ralli_d:
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                        pro_d = calculate_pro_metrics(df_d, df_w)
                        if pro_d: s1_uzun_ralli.append((ticker, tv_link, pro_d, ""))

                    if SELECTED_STRATEGY in ["Hepsi", "Uclu Kesisim"]:
                        if uclu_d:
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                            pro_d = calculate_pro_metrics(df_d, df_w)
                            if pro_d: s4_uclu_kesisim.append((ticker, tv_link, pro_d, ""))
                        elif uclu_w:
                            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                            pro_w = calculate_pro_metrics(df_w, df_w)
                            if pro_w: s4_uclu_kesisim.append((ticker, tv_link, pro_w, ""))

                    if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk"] and leda_d:
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                        pro_d = calculate_pro_metrics(df_d, df_w)
                        if pro_d: s5_leda_d.append((ticker, tv_link, pro_d, ""))

                    if SELECTED_STRATEGY in ["Hepsi", "Leda Haftalik"] and leda_w:
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                        pro_w = calculate_pro_metrics(df_w, df_w)
                        if pro_w: s6_leda_w.append((ticker, tv_link, pro_w, ""))

                    if SELECTED_STRATEGY in ["Hepsi", "HU Gunluk"] and hu_d:
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=D"
                        pro_d = calculate_pro_metrics(df_d, df_w)
                        if pro_d: s7_hu_d.append((ticker, tv_link, pro_d, ""))

                    if SELECTED_STRATEGY in ["Hepsi", "Mavilim Haftalik"] and mav_w:
                        tv_link = f"https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}&interval=W"
                        pro_w = calculate_pro_metrics(df_w, df_w)
                        if pro_w: s8_mav_w.append((ticker, tv_link, pro_w, ""))

        except Exception as e:
            print(f"Batch Hatası: {e}")
            traceback.print_exc()

        time.sleep(DELAY_BETWEEN_BATCHES)

    def report_strategy(title, items):
        if items:
            for item in items:
                try:
                    if len(item) == 4:
                        ticker, tv_link, pro, badge = item
                    else:
                        ticker, tv_link, pro = item[:3]
                        badge = ""
                    send_pro_report(title, ticker, tv_link, pro, badge)
                except Exception as e:
                    print(f"Rapor Gönderim Hatası: {e}")
        else:
            telegram_gonder(f"ℹ️ <b>Strateji:</b> <b>{title}</b>\nHer şey normal, bu periyotta sinyal yok.")

    try:
        if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk", "Leda Haftalik"]:
            report_strategy("⏰ SAATLİK LEDA SAT SİNYALİ", s9_leda_hourly_sell)
            
        if SELECTED_STRATEGY in ["Hepsi", "Uzun Vade Ralli"]: 
            report_strategy("1️⃣ RALLİ BAŞLANGIÇ", s1_uzun_ralli)
            
        if SELECTED_STRATEGY in ["Hepsi", "Uclu Kesisim"]: 
            report_strategy("2️⃣ ÜÇLÜ KESİŞİM", s4_uclu_kesisim)
            
        if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk"]: 
            report_strategy("3️⃣ ÖZEL GÜNLÜK", s5_leda_d)
            
        if SELECTED_STRATEGY in ["Hepsi", "Leda Haftalik"]: 
            report_strategy("4️⃣ ÖZEL HAFTALIK", s6_leda_w)
            
        if SELECTED_STRATEGY in ["Hepsi", "HU Gunluk"]: 
            report_strategy("5️⃣ HU GÜNLÜK", s7_hu_d)
            
        if SELECTED_STRATEGY in ["Hepsi", "Mavilim Haftalik"]: 
            report_strategy("6️⃣ MAVİLİM HAFTALIK", s8_mav_w)
    except Exception as e:
        print(f"Raporlama Döngüsü Hatası: {e}")

    telegram_gonder("🏁 <b>Pro Tarama ve Kontrol Tamamlandı.</b>")

if __name__ == "__main__":
    run_targeted_screener()

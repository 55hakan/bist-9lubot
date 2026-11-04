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
    "YKSLN", "YUNSA"
]
BIST_STOCK_LIST = [f"{t}.IS" for t in BIST_TICKERS]

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

# (Buradaki math/indicator fonksiyonları aynı kalıyor: pine_rma, wma, calculate_rsi, check_macd_cross, calculate_leda_indicators, check_hu_cross_signal, check_mavilim_signal, check_triple_confluence_signal, calculate_rsi_most_matrix, calculate_rsi_signals, calculate_auto_vwap2)
# Not: Önceki mesajdaki tüm indikatör fonksiyonları bu dosyanın içinde eksiksiz yer almalıdır.

def run_targeted_screener():
    print(f"🚀 Seçilen Strateji Çalıştırılıyor: {SELECTED_STRATEGY}")
    
    s1_uzun_ralli, s2_base_30, s3_matrix_wm, s4_uclu_kesisim = [], [], [], []
    s5_leda_d, s6_leda_w, s7_hu_d, s8_mav_w, s9_hassas_dip_orta, s10_auto_vwap = [], [], [], [], [], []

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
                
                # 1. Uzun Vade Ralli
                if SELECTED_STRATEGY in ["Hepsi", "Uzun Vade Ralli"] and not df_d.empty and len(df_d) >= 180:
                    res = calculate_rsi_most_matrix(df_d['Close'])
                    if res["blue_cross_red_above_50"]: s1_uzun_ralli.append(f"• <b>{ticker}</b> ({df_d['Close'].iloc[-1]:.2f}₺)")
                        
                # 2. Base 30
                if SELECTED_STRATEGY in ["Hepsi", "Base 30 Kesisişi"] and not df_d.empty and len(df_d) >= 30:
                    b_res = calculate_rsi_most_matrix(df_d['Close'])
                    if b_res["yellow_cross_30"]: s2_base_30.append(f"• <b>{ticker}</b> (Günlük)")
                        
                # 3. Matrix Orta Hat
                if SELECTED_STRATEGY in ["Hepsi", "Matrix Orta Hat"] and not df_d.empty and len(df_d) >= 100:
                    df_w_res = df_d.resample('W').agg({'Close': 'last'}).dropna()
                    if len(df_w_res) >= 50:
                        m_res = calculate_rsi_most_matrix(df_w_res['Close'])
                        if (m_res["mov40"].iloc[-1] > 50 and m_res["mov40"].iloc[-2] <= 50):
                            s3_matrix_wm.append(f"• <b>{ticker}</b> (Haftalık)")
                            
                # 4. Üçlü Kesişim
                if SELECTED_STRATEGY in ["Hepsi", "Uclu Kesisim"]:
                    if not df_d.empty and check_triple_confluence_signal(df_d): s4_uclu_kesisim.append(f"• <b>{ticker}</b> (Günlük)")
                    if not df_w.empty and check_triple_confluence_signal(df_w): s4_uclu_kesisim.append(f"• <b>{ticker}</b> (Haftalık)")
                    
                # 5. Leda Günlük
                if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk"] and not df_d.empty and len(df_d) >= 35:
                    res_d = calculate_leda_indicators(df_d)
                    if res_d is not None and res_d["buy"].iloc[-1] and check_macd_cross(df_d):
                        s5_leda_d.append(f"• <b>{ticker}</b>")
                        
                # 6. Leda Haftalık
                if SELECTED_STRATEGY in ["Hepsi", "Leda Haftalik"] and not df_w.empty and len(df_w) >= 35:
                    res_w = calculate_leda_indicators(df_w)
                    if res_w is not None and res_w["buy"].iloc[-1] and check_macd_cross(df_w):
                        s6_leda_w.append(f"• <b>{ticker}</b>")
                        
                # 7. HU Günlük
                if SELECTED_STRATEGY in ["Hepsi", "HU Gunluk"] and not df_d.empty and check_hu_cross_signal(df_d) and check_macd_cross(df_d):
                    s7_hu_d.append(f"• <b>{ticker}</b>")
                    
                # 8. Mavilim Haftalık
                if SELECTED_STRATEGY in ["Hepsi", "Mavilim Haftalik"] and not df_w.empty and check_mavilim_signal(df_w) and check_macd_cross(df_w):
                    s8_mav_w.append(f"• <b>{ticker}</b>")
                    
                # 9. Hassas Dip Orta
                if SELECTED_STRATEGY in ["Hepsi", "Hassas Dip Orta"] and not df_d.empty and len(df_d) >= 180:
                    dip, orta = calculate_rsi_signals(df_d['Close'])
                    if dip: s9_hassas_dip_orta.append(f"• <b>{ticker} (DİP)</b>")
                    if orta: s9_hassas_dip_orta.append(f"• <b>{ticker} (ORTA)</b>")

                # 10. Auto VWAP2
                if SELECTED_STRATEGY in ["Hepsi", "Auto VWAP2"] and not df_d.empty and len(df_d) >= 50:
                    df_vwap = calculate_auto_vwap2(df_d, "1D")
                    if df_vwap is not None:
                        if df_vwap['Trend'].iloc[-1] != df_vwap['Trend'].iloc[-2]:
                            s10_auto_vwap.append(f"• <b>{ticker}</b> ({df_vwap['Trend'].iloc[-1]})")

        except Exception as e:
            print(f"Batch Hatası: {e}")
        time.sleep(DELAY_BETWEEN_BATCHES)

    def report(title, items):
        if items: telegram_gonder(f"<b>{title}</b>\n--------------------------------------\n" + "\n".join(items))
        else: telegram_gonder(f"ℹ️ <b>{title}</b>\n--------------------------------------\n❌ Bu taramada koşulu sağlayan hisse yok.")

    if SELECTED_STRATEGY in ["Hepsi", "Uzun Vade Ralli"]: report("💎 1. UZUN VADELİ RALLİ TARAMASI", s1_uzun_ralli)
    if SELECTED_STRATEGY in ["Hepsi", "Base 30 Kesisişi"]: report("🟡 2. RSI-MOST BASE 30 KESİŞİMİ", s2_base_30)
    if SELECTED_STRATEGY in ["Hepsi", "Matrix Orta Hat"]: report("📅 3. MATRIX ORTA HAT (50) KESİŞİMİ", s3_matrix_wm)
    if SELECTED_STRATEGY in ["Hepsi", "Uclu Kesisim"]: report("💥 4. ÜÇLÜ KESİŞİM STRATEJİSİ", s4_uclu_kesisim)
    if SELECTED_STRATEGY in ["Hepsi", "Leda Gunluk"]: report("📈 5. LEDA GÜNLÜK + MACD", s5_leda_d)
    if SELECTED_STRATEGY in ["Hepsi", "Leda Haftalik"]: report("📈 6. LEDA HAFTALIK + MACD", s6_leda_w)
    if SELECTED_STRATEGY in ["Hepsi", "HU Gunluk"]: report("💎 7. HU GÜNLÜK + MACD", s7_hu_d)
    if SELECTED_STRATEGY in ["Hepsi", "Mavilim Haftalik"]: report("🌊 8. MAVİLİM HAFTALIK + MACD", s8_mav_w)
    if SELECTED_STRATEGY in ["Hepsi", "Hassas Dip Orta"]: report("🎯 9. HASSAS DİP VE ORTA BANT TARAMASI", s9_hassas_dip_orta)
    if SELECTED_STRATEGY in ["Hepsi", "Auto VWAP2"]: report("🔵 10. AUTO VWAP2 SİNYAL DEĞİŞİKLİĞİ", s10_auto_vwap)

if __name__ == "__main__":
    run_targeted_screener()

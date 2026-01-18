import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Analizator Predykcji - Michał Olejnik",
    page_icon="⚽",
    layout="wide"
)

# --- LOGIKA WYBORU ŹRÓDŁA DANYCH (HYBRYDOWA) ---
# Sprawdzamy dostępność połączenia z Google Sheets w st.secrets
USE_GSHEETS = "connections" in st.secrets and "gsheets" in st.secrets.connections

# --- FUNKCJE ŁADOWANIA I ZAPISU DANYCH ---
def load_data():
    try:
        if USE_GSHEETS:
            st.info("🔄 Łączenie z Google Sheets...")
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Odczytujemy zakładki zdefiniowane w Google Sheets
            st.info("📥 Pobieranie danych z arkusza 'results'...")
            results = conn.read(worksheet="results")
            st.info("📥 Pobieranie danych z arkusza 'predictions'...")
            preds = conn.read(worksheet="predictions")
            st.success("✅ Dane załadowane pomyślnie!")
        else:
            # Rezerwowe ładowanie lokalne
            results = pd.read_csv('results.csv')
            preds = pd.read_csv('predictions.csv')
    except Exception as e:
        import traceback
        st.error(f"❌ Błąd ładowania danych:")
        st.error(f"**Typ błędu:** {type(e).__name__}")
        st.error(f"**Komunikat:** {str(e)}")
        st.code(traceback.format_exc())
        st.warning("💡 Sprawdź czy:\n"
                   "- Arkusz Google Sheets ma zakładki o nazwach 'results' i 'predictions'\n"
                   "- Service account ma dostęp do arkusza (został dodany przez 'Share')\n"
                   "- Google Sheets API jest włączone w projekcie Google Cloud")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Łączenie danych po match_id 
    df = pd.merge(results, preds, on='match_id')
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df['has_prediction'] = df['pred_home_score'].notna()
    
    # Czyszczenie danych do porównania (standard H/D/A)
    def clean_str(val):
        return str(val).strip().upper() if pd.notna(val) else ""

    if df['has_prediction'].any():
        # Porównanie zwycięzcy 
        df.loc[df['has_prediction'], 'correct_winner'] = (
            df['FTR'].apply(clean_str) == df['pred_winner'].apply(clean_str)
        )
        # Analiza liczbowa pomyłki bramkowej 
        df.loc[df['has_prediction'], 'total_error'] = (
            abs(df['FTHG'] - df['pred_home_score']) + abs(df['FTAG'] - df['pred_away_score'])
        )
    return df, results, preds

def save_data(edited_preds):
    try:
        if USE_GSHEETS:
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet="predictions", data=edited_preds)
            # Wyczyść cache, aby załadować świeże dane
            st.cache_data.clear()
            st.success("Zapisano zmiany w Google Sheets!")
        else:
            edited_preds.to_csv('predictions.csv', index=False)
            st.success("Zapisano zmiany w lokalnym pliku CSV!")
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")

# --- URUCHOMIENIE LOGIKI DANYCH ---
df, raw_results, raw_preds = load_data()
#st.write("Podgląd tabeli results:", raw_results.head())
#st.write("Podgląd tabeli predictions:", raw_preds.head())

if not df.empty:
    st.title("⚽ Analizator predykcji meczów piłkarskich")
    st.caption("Autor: Michał Olejnik 148210 | Projekt: Systemy Mobilne 2025")

    if USE_GSHEETS:
        st.sidebar.success("Tryb: Online (Google Sheets)")
    else:
        st.sidebar.info("Tryb: Lokalny (Pliki CSV)")

    # --- SEKCJA 1: ANALIZA SZCZEGÓŁOWA MECZU ---
    st.header("🔍 Analiza konkretnego spotkania")
    
    # Lista meczów do wyboru 
    df['match_label'] = df['Date'].dt.strftime('%Y-%m-%d') + ": " + df['HomeTeam'] + " vs " + df['AwayTeam']
    selected_match = st.selectbox("Wybierz mecz z listy:", options=df['match_label'].tolist())
    m = df[df['match_label'] == selected_label if 'selected_label' in locals() else df['match_label'] == selected_match].iloc[0]

    if not m['has_prediction']:
        st.warning("⚠️ Ten mecz nie został jeszcze obstawiony. Wprowadź typ w edytorze na dole, aby odblokować wyniki.")
    else:
        # Interaktywna zmiana formy wykresu
        chart_mode = st.radio("Forma wizualizacji:", ["Słupkowy (Klasyczny)", "Radarowy (Profil błędu)"], horizontal=True)
        
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            if chart_mode == "Słupkowy (Klasyczny)":
                fig = go.Figure(data=[
                    go.Bar(name='Faktyczny Wynik', x=[m['HomeTeam'], m['AwayTeam']], y=[m['FTHG'], m['FTAG']], marker_color='#3498db'),
                    go.Bar(name='Twoja Predykcja', x=[m['HomeTeam'], m['AwayTeam']], y=[m['pred_home_score'], m['pred_away_score']], marker_color='#f1c40f')
                ])
                fig.update_layout(barmode='group', title="Zestawienie bramek")
            else:
                fig = go.Figure()
                categories = ['Gole Gospodarzy', 'Gole Gości']
                fig.add_trace(go.Scatterpolar(r=[m['FTHG'], m['FTAG']], theta=categories, fill='toself', name='Fakty', line_color='#3498db'))
                fig.add_trace(go.Scatterpolar(r=[m['pred_home_score'], m['pred_away_score']], theta=categories, fill='toself', name='Predykcja', line_color='#f1c40f'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), title="Radar bramkowy")
            
            st.plotly_chart(fig, use_container_width=True)

        with col_m2:
            st.subheader("Wynik analizy")
            st.write(f"**Prawdziwy wynik:** {int(m['FTHG'])}:{int(m['FTAG'])}")
            st.write(f"**Twoja predykcja:** {int(m['pred_home_score'])}:{int(m['pred_away_score'])}")
            st.metric("Suma błędu", int(m['total_error']))
            if m['correct_winner']: st.success("Trafiony zwycięzca!")
            else: st.error("Nietrafiony zwycięzca")

    st.divider()

    # --- SEKCJA 2: TREND I ZAKRES DAT ---
    st.header("📈 Historia trafności w czasie")
    df_played = df[df['has_prediction']].sort_values('Date').copy()

    if not df_played.empty:
        # Interaktywny zakres dat 
        d_min, d_max = df_played['Date'].min().to_pydatetime(), df_played['Date'].max().to_pydatetime()
        date_range = st.date_input("Zakres czasu:", value=(d_min, d_max), min_value=d_min, max_value=d_max)

        if isinstance(date_range, tuple) and len(date_range) == 2:
            df_filtered = df_played[(df_played['Date'].dt.date >= date_range[0]) & (df_played['Date'].dt.date <= date_range[1])]
            
            if not df_filtered.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Skuteczność (1X2)", f"{df_filtered['correct_winner'].mean()*100:.1f}%")
                c2.metric("Średni błąd", f"{df_filtered['total_error'].mean():.2f}")
                c3.metric("Liczba meczów", len(df_filtered))

                # Wykres trendu
                fig_trend = px.line(df_filtered, x='Date', y='total_error', title="Trend błędu bramkowego")
                fig_trend.add_trace(go.Scatter(
                    x=df_filtered['Date'], y=df_filtered['total_error'], mode='markers',
                    marker=dict(color=['#2ecc71' if c else '#e74c3c' for c in df_filtered['correct_winner']], size=12),
                    name="Trafność zwycięzcy"
                ))
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.warning("Brak danych w wybranym zakresie.")
    else:
        st.info("Obstaw mecze, aby zobaczyć statystyki czasowe.")

    st.divider()

    # --- SEKCJA 3: EDYTOR DANYCH ---
    st.header("📝 Edytor predykcji")
    st.write("Wprowadź swoje typy. System zapisze je w wybranym źródle (CSV lub Google Sheets).")
    
    # Interaktywne środowisko do edycji 
    edit_cols = ['match_id', 'HomeTeam', 'AwayTeam', 'pred_home_score', 'pred_away_score', 'pred_winner']
    new_data = st.data_editor(df[edit_cols], num_rows="fixed")

    if st.button("💾 Zapisz zmiany"):
        save_df = new_data[['match_id', 'pred_home_score', 'pred_away_score', 'pred_winner']]
        save_data(save_df)
        st.rerun()

else:
    st.error("Nie udało się załadować danych aplikacji.")

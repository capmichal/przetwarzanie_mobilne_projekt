import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Konfiguracja strony
st.set_page_config(page_title="Analizator Predykcji", layout="wide")

def load_data():
    # Wczytanie plików
    results = pd.read_csv('results.csv')
    preds = pd.read_csv('predictions.csv')
    
    # Łączenie danych
    df = pd.merge(results, preds, on='match_id')
    
    # Obliczanie błędów tylko tam, gdzie są predykcje (unikamy NaN w statystykach)
    df['has_prediction'] = df['pred_home_score'].notna()
    
    # Logika statystyk (tylko dla obstawionych)
    df.loc[df['has_prediction'], 'error_home'] = abs(df['FTHG'] - df['pred_home_score'])
    df.loc[df['has_prediction'], 'error_away'] = abs(df['FTAG'] - df['pred_away_score'])
    df.loc[df['has_prediction'], 'total_error'] = df['error_home'] + df['error_away']
    df.loc[df['has_prediction'], 'correct_winner'] = df['FTR'] == df['pred_winner']
    
    return df

df = load_data()

st.title("⚽ Analizator predykcji: Tryb Bezpieczny")

# --- SEKCJA 1: ANALIZA KONKRETNEGO MECZU ---
st.header("🔍 Szczegóły wybranego meczu")

df['match_label'] = df['Date'] + ": " + df['HomeTeam'] + " vs " + df['AwayTeam']
selected_match_label = st.selectbox("Wybierz mecz do analizy:", df['match_label'].unique())

# Pobieramy dane dla wybranego meczu
m = df[df['match_label'] == selected_match_label].iloc[0]

# --- LOGIKA BLOKADY (Punkt 1 i 2 Twojej prośby) ---
if not m['has_prediction']:
    st.warning("⚠️ Ten mecz nie został jeszcze przez Ciebie obstawiony!")
    st.info("Przewiń na dół do sekcji **Edytor**, aby wprowadzić swój typ. Wynik rzeczywisty zostanie odblokowany po zapisaniu predykcji.")
    
    # Pokazujemy pusty wykres lub samą informację o drużynach
    col_empty1, col_empty2 = st.columns([2, 1])
    with col_empty1:
        # Wizualizacja zastępcza - same drużyny bez słupków
        fig_placeholder = go.Figure()
        fig_placeholder.update_layout(
            title=f"Mecz: {m['HomeTeam']} vs {m['AwayTeam']} (Oczekiwanie na typ)",
            xaxis=dict(tickvals=[0, 1], ticktext=[m['HomeTeam'], m['AwayTeam']]),
            yaxis=dict(range=[0, 5], title="Bramki"),
            annotations=[dict(text="ZABLOKOWANE: Wprowadź typ", showarrow=False, font_size=20)]
        )
        st.plotly_chart(fig_placeholder, use_container_width=True)
else:
    # JEŻELI OBSTAWIONO - POKAZUJEMY PEŁNĄ ANALIZĘ
    col_m1, col_m2 = st.columns([2, 1])
    
    with col_m1:
        fig_match = go.Figure(data=[
            go.Bar(name='Rzeczywistość', x=[m['HomeTeam'], m['AwayTeam']], y=[m['FTHG'], m['FTAG']], marker_color='#3498db'),
            go.Bar(name='Twoja Predykcja', x=[m['HomeTeam'], m['AwayTeam']], y=[m['pred_home_score'], m['pred_away_score']], marker_color='#f1c40f')
        ])
        fig_match.update_layout(title=f"Porównanie bramek: {m['HomeTeam']} vs {m['AwayTeam']}", barmode='group')
        st.plotly_chart(fig_match, use_container_width=True)

    with col_m2:
        st.subheader("Wynik analizy")
        st.write(f"**Prawdziwy wynik:** {m['FTHG']}:{m['FTAG']}")
        
        # Bezpieczne wyświetlanie predykcji (naprawa błędu ValueError)
        p_home = int(m['pred_home_score'])
        p_away = int(m['pred_away_score'])
        st.write(f"**Twoja predykcja:** {p_home}:{p_away}")
        
        if m['correct_winner']:
            st.success("✅ Trafiłeś zwycięzcę!")
        else:
            st.error("❌ Błędny typ zwycięzcy")
            
        st.metric("Całkowity błąd bramkowy", int(m['total_error']))

st.markdown("---")

# --- SEKCJA 2: GLOBALNE STATYSTYKI (Tylko dla obstawionych) ---
st.header("📈 Twoja ogólna skuteczność")
df_played = df[df['has_prediction']]

if len(df_played) > 0:
    c1, c2, c3 = st.columns(3)
    c1.metric("Skuteczność typów", f"{df_played['correct_winner'].mean()*100:.1f}%")
    c2.metric("Średni błąd", f"{df_played['total_error'].mean():.2f} gola")
    c3.metric("Obstawione mecze", len(df_played))
    
    fig_hist = px.histogram(df_played, x="total_error", title="Rozkład Twoich błędów", nbins=10)
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.write("Brak danych do statystyk. Obstaw pierwszy mecz!")

st.markdown("---")

# --- SEKCJA 3: EDYTOR ---
st.header("📝 Edytor predykcji")
# Wyświetlamy edytor dla wszystkich meczów
edited_df = st.data_editor(df[['match_id', 'HomeTeam', 'AwayTeam', 'pred_home_score', 'pred_away_score', 'pred_winner']])

if st.button("💾 Zapisz i odblokuj analizę"):
    # Zapisujemy tylko te kolumny, które są w predictions.csv
    to_save = edited_df[['match_id', 'pred_home_score', 'pred_away_score', 'pred_winner']]
    to_save.to_csv('predictions.csv', index=False)
    st.success("Predykcje zapisane! Analiza dla tych meczów jest już dostępna.")
    st.rerun()

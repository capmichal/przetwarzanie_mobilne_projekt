import streamlit as st
import pandas as pd
import plotly.express as px

# Konfiguracja strony pod urządzenia mobilne i desktop 
st.set_page_config(page_title="Analizator Predykcji", layout="wide")

# 1. Funkcja wczytywania danych
def load_data():
    results = pd.read_csv('results.csv')
    preds = pd.read_csv('predictions.csv')
    # Łączenie danych po match_id 
    df = pd.merge(results, preds, on='match_id')
    return df

st.title("⚽ Analizator predykcji meczów piłkarskich")
st.markdown("---")

# 2. Sidebar - Filtrowanie danych 
st.sidebar.header("Filtry")
team_filter = st.sidebar.multiselect(
    "Wybierz drużynę (Gospodarz):", 
    options=pd.read_csv('results.csv')['HomeTeam'].unique()
)

# 3. Załadowanie i przygotowanie danych do analizy
df = load_data()

# Logika sprawdzania trafności 
# Trafienie zwycięzcy (H/D/A)
df['correct_winner'] = df['FTR'] == df['pred_winner']
# Trafienie dokładnego wyniku
df['correct_score'] = (df['FTHG'] == df['pred_home_score']) & (df['FTAG'] == df['pred_away_score'])

# Filtrowanie widoku
if team_filter:
    df = df[df['HomeTeam'].isin(team_filter)]

# 4. Dashboard - Główne Statystyki (KPI) 
col1, col2, col3 = st.columns(3)

with col1:
    acc_winner = df['correct_winner'].mean() * 100 if len(df) > 0 else 0
    st.metric("Skuteczność (Zwycięzca)", f"{acc_winner:.1f}%")

with col2:
    acc_score = df['correct_score'].mean() * 100 if len(df) > 0 else 0
    st.metric("Trafione Dokładne Wyniki", f"{acc_score:.1f}%")

with col3:
    # Analiza liczbowa - Średni błąd bramkowy (MAE) 
    # $MAE = \frac{1}{n} \sum |Wynik - Predykcja|$
    mae = (abs(df['FTHG'] - df['pred_home_score']) + abs(df['FTAG'] - df['pred_away_score'])).mean()
    st.metric("Średni błąd bramkowy", f"{mae:.2f}" if not pd.isna(mae) else "0")

st.markdown("---")

# 5. Graficzne przedstawienie zestawienia - Wykresy 
st.subheader("📊 Analiza graficzna")
c1, c2 = st.columns(2)

with c1:
    # Wykres kołowy trafności zwycięzcy
    fig_winner = px.pie(df, names='correct_winner', title="Trafność typu (Zwycięzca/Remis)",
                 color='correct_winner', color_discrete_map={True: '#2ecc71', False: '#e74c3c'})
    st.plotly_chart(fig_winner, use_container_width=True)

with c2:
    # Wykres błędu w czasie (kolejne mecze)
    df['total_error'] = abs(df['FTHG'] - df['pred_home_score']) + abs(df['FTAG'] - df['pred_away_score'])
    fig_error = px.line(df, x='match_id', y='total_error', title="Błąd bramkowy w kolejnych meczach",
                        labels={'total_error': 'Suma błędu goli', 'match_id': 'ID Meczu'})
    st.plotly_chart(fig_error, use_container_width=True)

st.markdown("---")

# 6. Interaktywne środowisko - Edytor danych 
st.subheader("📝 Zarządzaj swoimi predykcjami")
st.info("Możesz tutaj dopisywać nowe predykcje lub edytować istniejące bezpośrednio w tabeli.")

# Wyświetlamy tylko kolumny do edycji, ale łączymy z wynikami żeby widzieć kogo typujemy
display_cols = ['match_id', 'HomeTeam', 'AwayTeam', 'pred_home_score', 'pred_away_score', 'pred_winner']
edited_df = st.data_editor(df[display_cols], num_rows="dynamic")

if st.button("💾 Zapisz predykcje do pliku"):
    # Przygotowanie danych do zapisu (tylko kolumny z pliku predictions.csv)
    to_save = edited_df[['match_id', 'pred_home_score', 'pred_away_score', 'pred_winner']]
    to_save.to_csv('predictions.csv', index=False)
    st.success("Zmiany zostały zapisane w pliku predictions.csv!")
    st.rerun()

# 7. Tabela szczegółowa 
st.subheader("📋 Zestawienie szczegółowe")
st.dataframe(df[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'pred_home_score', 'pred_away_score', 'correct_winner']])

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Analizator Predykcji Piłkarskich",
    page_icon="⚽",
    layout="wide"
)

# --- FUNKCJA ŁADOWANIA DANYCH ---
def load_data():
    try:
        results = pd.read_csv('results.csv')
        preds = pd.read_csv('predictions.csv')
    except Exception:
        st.error("Błąd ładowania plików CSV. Upewnij się, że results.csv i predictions.csv są w folderze.")
        return pd.DataFrame()

    df = pd.merge(results, preds, on='match_id')
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df['has_prediction'] = df['pred_home_score'].notna()
    
    def clean_str(val):
        return str(val).strip().upper() if pd.notna(val) else ""

    if df['has_prediction'].any():
        df.loc[df['has_prediction'], 'correct_winner'] = (
            df['FTR'].apply(clean_str) == df['pred_winner'].apply(clean_str)
        )
        df.loc[df['has_prediction'], 'total_error'] = (
            abs(df['FTHG'] - df['pred_home_score']) + abs(df['FTAG'] - df['pred_away_score'])
        )
    return df

df = load_data()

if not df.empty:
    st.title("⚽ Interaktywny Analizator Predykcji")
    
    # --- SEKCJA 1: ANALIZA SZCZEGÓŁOWA MECZU ---
    st.header("🔍 Szczegóły meczu")
    
    # Przygotowanie listy meczów
    df['match_label'] = df['Date'].dt.strftime('%Y-%m-%d') + ": " + df['HomeTeam'] + " vs " + df['AwayTeam']
    match_labels = df['match_label'].tolist()
    
    selected_label = st.selectbox("Wybierz mecz z listy:", options=match_labels)
    m = df[df['match_label'] == selected_label].iloc[0]

    if not m['has_prediction']:
        st.warning("⚠️ Brak Twojej predykcji dla tego meczu.")
    else:
        # NOWOŚĆ: Wybór typu wykresu dla konkretnego meczu
        chart_type = st.radio(
            "Wybierz formę przedstawienia danych:",
            ["Słupkowy (Porównanie)", "Radarowy (Profil meczu)"],
            horizontal=True
        )

        c_m1, c_m2 = st.columns([2, 1])
        with c_m1:
            if chart_type == "Słupkowy (Porównanie)":
                fig_match = go.Figure(data=[
                    go.Bar(name='Faktyczny Wynik', x=[m['HomeTeam'], m['AwayTeam']], y=[m['FTHG'], m['FTAG']], marker_color='#3498db'),
                    go.Bar(name='Twoja Predykcja', x=[m['HomeTeam'], m['AwayTeam']], y=[m['pred_home_score'], m['pred_away_score']], marker_color='#f1c40f')
                ])
                fig_match.update_layout(barmode='group', height=350, title="Zestawienie bramek: Fakty vs Predykcja")
            
            else: # Wykres Radarowy
                categories = ['Gole Gospodarzy', 'Gole Gości']
                fig_match = go.Figure()
                fig_match.add_trace(go.Scatterpolar(
                    r=[m['FTHG'], m['FTAG']],
                    theta=categories,
                    fill='toself',
                    name='Faktyczny Wynik',
                    line_color='#3498db'
                ))
                fig_match.add_trace(go.Scatterpolar(
                    r=[m['pred_home_score'], m['pred_away_score']],
                    theta=categories,
                    fill='toself',
                    name='Twoja Predykcja',
                    line_color='#f1c40f'
                ))
                fig_match.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, max(5, m['FTHG'], m['FTAG'], m['pred_home_score'], m['pred_away_score'])])),
                    showlegend=True,
                    height=350,
                    title="Radar porównawczy"
                )
            
            st.plotly_chart(fig_match, use_container_width=True)

        with c_m2:
            st.subheader("Werdykt")
            st.write(f"**Data:** {m['Date'].strftime('%Y-%m-%d')}")
            st.write(f"**Wynik:** {int(m['FTHG'])}:{int(m['FTAG'])}")
            st.write(f"**Twoja predykcja:** {int(m['pred_home_score'])}:{int(m['pred_away_score'])}")
            st.metric("Błąd goli", int(m['total_error']))
            if m['correct_winner']: st.success("Trafiony zwycięzca!")
            else: st.error("Nietrafiony zwycięzca")

    st.divider()

    # --- SEKCJA 2: TREND I ZAKRES DAT ---
    st.header("📈 Historia trafności w czasie")
    
    df_played = df[df['has_prediction']].sort_values('Date').copy()

    if not df_played.empty:
        # NOWOŚĆ: Interaktywny wybór zakresu dat
        st.subheader("Filtruj historię")
        min_date = df_played['Date'].min().to_pydatetime()
        max_date = df_played['Date'].max().to_pydatetime()
        
        date_range = st.date_input(
            "Wybierz zakres dat do analizy:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Filtrowanie danych na podstawie wybranego zakresu
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df_played['Date'].dt.date >= start_date) & (df_played['Date'].dt.date <= end_date)
            df_filtered = df_played.loc[mask]
        else:
            df_filtered = df_played

        if not df_filtered.empty:
            # Metryki dla wybranego zakresu
            col1, col2, col3 = st.columns(3)
            col1.metric("Skuteczność (wybrany zakres)", f"{df_filtered['correct_winner'].mean()*100:.1f}%")
            col2.metric("Średni błąd (wybrany zakres)", f"{df_filtered['total_error'].mean():.2f}")
            col3.metric("Liczba meczów", len(df_filtered))

            # Wykres trendu
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=df_filtered['Date'], y=df_filtered['total_error'],
                mode='lines+markers',
                line=dict(color='lightgrey', width=1),
                marker=dict(
                    color=['#2ecc71' if c else '#e74c3c' for c in df_filtered['correct_winner']],
                    size=12,
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                customdata=df_filtered['match_label'],
                hovertemplate="<b>%{customdata}</b><br>Błąd: %{y} goli<br>Data: %{x}<extra></extra>"
            ))

            fig_trend.update_layout(
                xaxis_title="Data meczu",
                yaxis_title="Suma błędu bramkowego",
                height=450,
                title="Trend trafności (Zielony = trafiony zwycięzca, Czerwony = błąd)"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("Brak meczów w wybranym zakresie dat.")
    else:
        st.info("Obstaw mecze w edytorze poniżej, aby zobaczyć statystyki historyczne.")

    st.divider()

    # --- SEKCJA 3: EDYTOR DANYCH ---
    st.header("📝 Edytor Twoich predykcji")
    cols_to_edit = ['match_id', 'HomeTeam', 'AwayTeam', 'pred_home_score', 'pred_away_score', 'pred_winner']
    edited_df = st.data_editor(df[cols_to_edit], num_rows="fixed", key="data_editor")

    if st.button("💾 Zapisz zmiany do pliku"):
        save_df = edited_df[['match_id', 'pred_home_score', 'pred_away_score', 'pred_winner']]
        save_df.to_csv('predictions.csv', index=False)
        st.success("Zapisano pomyślnie!")
        st.rerun()

else:
    st.warning("Nie udało się załadować danych.")

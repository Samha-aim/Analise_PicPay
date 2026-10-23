import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard PicPay", page_icon="💳", layout="wide"
)

st.title("💳 Análise Detalhada do Extrato PicPay")

uploaded_file = st.file_uploader(
    "Escolha o ficheiro CSV do extrato", type=["csv"]
)

if uploaded_file is not None:
  # 1. Leitura robusta com deteção automática de separador
  try:
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8")
  except Exception:
    try:
      uploaded_file.seek(0)
      df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
    except Exception:
      uploaded_file.seek(0)
      df = pd.read_csv(uploaded_file, sep=",", encoding="latin1")

  # Normaliza os nomes das colunas para minúsculas
  df.columns = [c.strip().lower() for c in df.columns]

  if len(df.columns) < 2:
    st.error(
        "O ficheiro foi lido como tendo apenas uma coluna. Verifique o"
        " separador."
    )
    st.stop()

  # 2. Mapeamento baseado nas colunas reais do PicPay
  coluna_valor = "valor" if "valor" in df.columns else df.columns[4]
  coluna_desc = (
      "origem / destino"
      if "origem / destino" in df.columns
      else df.columns[3]
  )
  coluna_data = "data" if "data" in df.columns else df.columns[0]

  # Limpeza avançada de valores
  df["Valor_Limpo"] = (
      df[coluna_valor]
      .astype(str)
      .str.replace("R$", "", regex=False)
      .str.replace("−", "-", regex=False)
      .str.replace("\xa0", "", regex=False)
      .str.replace(" ", "", regex=False)
      .str.replace(".", "", regex=False)
      .str.replace(",", ".", regex=False)
  )
  df["Valor_Limpo"] = pd.to_numeric(df["Valor_Limpo"], errors="coerce")

  # Trata as datas
  if coluna_data in df.columns:
    df["Data_Limpa"] = pd.to_datetime(df[coluna_data], errors="coerce")

  # Separação entre Gastos (negativos) e Ganhos (positivos)
  df_gastos = df[df["Valor_Limpo"] < 0].copy()
  df_gastos["Valor_Absoluto"] = df_gastos["Valor_Limpo"].abs()

  df_ganhos = df[df["Valor_Limpo"] > 0].copy()

  st.success("Dados processados com sucesso!")

  # ==========================================
  # GRÁFICO CRUZADO GERAL (Ganhos vs Gastos)
  # ==========================================
  st.subheader("📈 Evolução Temporal: Ganhos vs Gastos")

  # Prepara os dados diários
  df_g_tempo = (
      df_ganhos.groupby("Data_Limpa")["Valor_Limpo"].sum().reset_index()
  )
  df_g_tempo.rename(columns={"Valor_Limpo": "Ganhos"}, inplace=True)

  df_d_tempo = (
      df_gastos.groupby("Data_Limpa")["Valor_Absoluto"].sum().reset_index()
  )
  df_d_tempo.rename(columns={"Valor_Absoluto": "Gastos"}, inplace=True)

  # Junta os dois num único DataFrame por data
  df_evolucao = pd.merge(
      df_g_tempo, df_d_tempo, on="Data_Limpa", how="outer"
  ).fillna(0)
  df_evolucao = df_evolucao.sort_values("Data_Limpa")

  if not df_evolucao.empty:
    # Cria o gráfico de linhas cruzadas com Plotly
    fig = px.line(
        df_evolucao,
        x="Data_Limpa",
        y=["Ganhos", "Gastos"],
        labels={
            "value": "Valor (R$)",
            "Data_Limpa": "Data",
            "variable": "Tipo",
        },
        color_discrete_map={
            "Ganhos": "#0066cc",
            "Gastos": "#ff3333",
        },  # Azul para Ganhos, Vermelho para Gastos
    )
    fig.update_layout(legend_title_text="Legenda", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.info("Sem dados temporais suficientes para exibir o gráfico.")

  st.markdown("---")

  # Criando Abas para detalhar as análises individuais
  aba_gastos, aba_ganhos = st.tabs(
      ["📉 Detalhes de Despesas / Gastos", "📈 Detalhes de Ganhos / Entradas"]
  )

  # ==========================================
  # ABA 1: GASTOS (Despesas)
  # ==========================================
  with aba_gastos:
    total_gasto = df_gastos["Valor_Absoluto"].sum()
    st.metric("Total em Gastos/Despesas", f"R$ {total_gasto:,.2f}")

    st.markdown("---")
    st.subheader("📍 Locais / Descrições com Maiores Gastos")

    maiores_gastos = (
        df_gastos.groupby(coluna_desc)["Valor_Absoluto"]
        .sum()
        .reset_index()
        .sort_values(by="Valor_Absoluto", ascending=False)
    )

    col_chart1, col_table1 = st.columns([2, 1])
    with col_chart1:
      top_10_g = maiores_gastos.head(10).set_index(coluna_desc)
      st.bar_chart(top_10_g["Valor_Absoluto"])
    with col_table1:
      st.dataframe(
          maiores_gastos.rename(
              columns={
                  coluna_desc: "Local / Descrição",
                  "Valor_Absoluto": "Total (R$)",
              }
          ),
          hide_index=True,
      )

    st.markdown("---")
    st.subheader("🔄 Gastos Mais Recorrentes (Frequência)")

    recorrencia_g = (
        df_gastos.groupby(coluna_desc)
        .agg(
            Quantidade=("Valor_Absoluto", "count"),
            Total_Gasto=("Valor_Absoluto", "sum"),
            Valor_Medio=("Valor_Absoluto", "mean"),
        )
        .reset_index()
        .sort_values(by="Quantidade", ascending=False)
    )

    col_chart2, col_table2 = st.columns([2, 1])
    with col_chart2:
      top_rec_g = recorrencia_g.head(10).set_index(coluna_desc)
      st.bar_chart(top_rec_g["Quantidade"])
    with col_table2:
      st.dataframe(
          recorrencia_g.rename(
              columns={
                  coluna_desc: "Descrição",
                  "Quantidade": "Qtd Vezes",
                  "Total_Gasto": "Total (R$)",
                  "Valor_Medio": "Média (R$)",
              }
          ),
          hide_index=True,
      )

  # ==========================================
  # ABA 2: GANHOS (Entradas)
  # ==========================================
  with aba_ganhos:
    total_ganho = df_ganhos["Valor_Limpo"].sum()
    st.metric("Total em Ganhos / Entradas", f"R$ {total_ganho:,.2f}")

    st.markdown("---")
    st.subheader("💰 Origens com Maiores Ganhos")

    maiores_ganhos = (
        df_ganhos.groupby(coluna_desc)["Valor_Limpo"]
        .sum()
        .reset_index()
        .sort_values(by="Valor_Limpo", ascending=False)
    )

    col_chart3, col_table3 = st.columns([2, 1])
    with col_chart3:
      top_10_inc = maiores_ganhos.head(10).set_index(coluna_desc)
      st.bar_chart(top_10_inc["Valor_Limpo"])
    with col_table3:
      st.dataframe(
          maiores_ganhos.rename(
              columns={
                  coluna_desc: "Origem / Descrição",
                  "Valor_Limpo": "Total (R$)",
              }
          ),
          hide_index=True,
      )

    st.markdown("---")
    st.subheader("🔄 Ganhos Mais Recorrentes (Frequência)")

    recorrencia_inc = (
        df_ganhos.groupby(coluna_desc)
        .agg(
            Quantidade=("Valor_Limpo", "count"),
            Total_Ganho=("Valor_Limpo", "sum"),
            Valor_Medio=("Valor_Limpo", "mean"),
        )
        .reset_index()
        .sort_values(by="Quantidade", ascending=False)
    )

    col_chart4, col_table4 = st.columns([2, 1])
    with col_chart4:
      top_rec_inc = recorrencia_inc.head(10).set_index(coluna_desc)
      st.bar_chart(top_rec_inc["Quantidade"])
    with col_table4:
      st.dataframe(
          recorrencia_inc.rename(
              columns={
                  coluna_desc: "Descrição",
                  "Quantidade": "Qtd Vezes",
                  "Total_Ganho": "Total (R$)",
                  "Valor_Medio": "Média (R$)",
              }
          ),
          hide_index=True,
      )

else:
  st.info("Faça o upload do seu ficheiro CSV para visualizar as análises.")
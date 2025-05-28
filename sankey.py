import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="Gráfico Sankey Interativo")

uploaded_file = st.sidebar.file_uploader("Upload do arquivo CSV", type="csv")

if uploaded_file:
    try:
        raw = pd.read_csv(uploaded_file, sep=';', encoding='ISO-8859-1', dtype=str)
        for col in raw.columns:
            raw[col] = raw[col].str.replace(',', '.', regex=False)

        colunas_valores_idx = [5, 9, 10, 11] + list(range(13, 25))
        colunas_valores = [raw.columns[i] for i in colunas_valores_idx if i < len(raw.columns)]
        for col in colunas_valores:
            raw[col] = pd.to_numeric(raw[col], errors='coerce')

        colunas_categoria_idx = [0, 1, 2, 6, 7, 8]
        colunas_categoria = [raw.columns[i] for i in colunas_categoria_idx if i < len(raw.columns)]

        aba_sankey, aba_barras, aba_dados = st.tabs(["📊 Gráfico Sankey", "📈 Gráficos de Barras", "📁 Dados Importados"])

        # ------------------ ABA SANKEY ------------------
        with aba_sankey:
            st.subheader("Gráfico Sankey")

            # Aplicar estilo CSS para remover sombra dos rótulos
            st.markdown(
                """
                <style>
                .node-label-text-path, text {
                    fill: black !important;
                    text-shadow: none !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            flux_cols = st.multiselect(
                "Selecione a ordem do fluxo (mínimo 2 colunas categóricas)",
                options=colunas_categoria,
                default=colunas_categoria[:3]
            )
            value_col = st.selectbox("Coluna de valor para o Sankey", colunas_valores, index=0)

            if len(flux_cols) >= 2 and value_col:
                df_clean = raw[flux_cols + [value_col]].dropna()
                df_clean = df_clean[df_clean[value_col] > 0]

                all_nodes = pd.unique(df_clean[flux_cols].values.ravel()).tolist()
                node_map = {node: idx for idx, node in enumerate(all_nodes)}
                node_colors = px.colors.qualitative.Plotly
                color_map = [node_colors[i % len(node_colors)] for i in range(len(all_nodes))]

                source, target, value = [], [], []
                for i in range(len(flux_cols) - 1):
                    grouped = (
                        df_clean
                        .groupby([flux_cols[i], flux_cols[i + 1]])[value_col]
                        .sum()
                        .reset_index()
                    )
                    for _, row in grouped.iterrows():
                        s_idx = node_map[row[flux_cols[i]]]
                        t_idx = node_map[row[flux_cols[i + 1]]]
                        v_val = row[value_col]
                        if v_val > 0:
                            source.append(s_idx)
                            target.append(t_idx)
                            value.append(v_val)

                if not value:
                    st.warning("Não há conexões com valores positivos.")
                else:
                    fig = go.Figure(data=[go.Sankey(
                        node=dict(
                            label=all_nodes,
                            pad=15,
                            thickness=20,
                            color=color_map,
                            line=dict(width=0)
                        ),
                        link=dict(source=source, target=target, value=value)
                    )])

                    fig.update_layout(
                        title_text="Gráfico Sankey",
                        font=dict(size=14, color='black', family='Arial'),
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("Selecione pelo menos duas colunas categóricas e uma de valor.")


        # ------------------ ABA BARRAS ------------------
        with aba_barras:
            st.subheader("Gráficos de Barras")
            eixo_x = st.selectbox("Eixo X (categórico)", options=colunas_categoria, index=0)
            eixo_y = st.selectbox("Eixo Y (valor numérico)", options=colunas_valores, index=0)
            agregacao = st.radio("Tipo de agregação", ["Soma", "Média"])

            df_bar = raw[[eixo_x, eixo_y]].dropna()
            df_bar[eixo_y] = pd.to_numeric(df_bar[eixo_y], errors='coerce')
            df_bar = df_bar.dropna()

            if agregacao == "Soma":
                df_agg = df_bar.groupby(eixo_x)[eixo_y].sum().reset_index()
            else:
                df_agg = df_bar.groupby(eixo_x)[eixo_y].mean().reset_index()

            fig_bar = px.bar(df_agg, x=eixo_x, y=eixo_y, color=eixo_x, text_auto='.2s')
            fig_bar.update_layout(
                title=f"{agregacao} de {eixo_y} por {eixo_x}",
                xaxis_title=eixo_x,
                yaxis_title=eixo_y,
                font=dict(size=13, color='black'),
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ------------------ ABA DADOS ------------------
        with aba_dados:
            st.subheader("Prévia dos Dados Importados")
            st.dataframe(raw.head(100))

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Faça o upload de um arquivo CSV na barra lateral para começar.")

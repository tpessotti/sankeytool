import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="Gráfico Sankey Interativo")

uploaded_file = st.sidebar.file_uploader("Upload do arquivo Excel (.xlsx)", type="xlsx")

if uploaded_file:
    try:
        import openpyxl

        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_names = xls.sheet_names

        st.sidebar.markdown("### Opções de Importação")
        sheet = st.sidebar.selectbox("Selecione a planilha", sheet_names)
        header_row = st.sidebar.number_input("Número da linha do cabeçalho", min_value=1, value=1, step=1)
        start_row = st.sidebar.number_input("Linha de início dos dados", min_value=1, value=header_row + 1, step=1)
        end_row = st.sidebar.number_input("Linha final dos dados", min_value=start_row, value=start_row + 20, step=1)

        nrows = end_row - start_row + 1
        skiprows = list(range(start_row - 1))

        df_range = pd.read_excel(
            uploaded_file,
            sheet_name=sheet,
            header=header_row - 1,
            skiprows=skiprows,
            nrows=nrows,
            engine='openpyxl'
        )

        raw = df_range.astype(str)
        for col in raw.columns:
            raw[col] = raw[col].str.replace(',', '.', regex=False)

        st.success("Planilha carregada com sucesso!")

        with st.expander("📌 Classificação das Colunas", expanded=True):
            tipo_colunas = {}
            for col in raw.columns:
                tipo = st.selectbox(
                    f"Tipo da variável '{col}'",
                    ["Ignorar", "Categórica", "Valor numérico"],
                    index=1 if col.lower() in ["etapa", "unidade", "consumivel", "produto"] else 0
                )
                tipo_colunas[col] = tipo

        if st.button("✅ Confirmar e carregar dados"):
            st.session_state["dados_confirmados"] = True
            st.session_state["df"] = raw.copy()
            st.session_state["colunas_categoria"] = [col for col, tipo in tipo_colunas.items() if tipo == "Categórica"]
            st.session_state["colunas_valores"] = [col for col, tipo in tipo_colunas.items() if tipo == "Valor numérico"]
            for col in st.session_state["colunas_valores"]:
                st.session_state["df"][col] = pd.to_numeric(st.session_state["df"][col], errors='coerce')
            st.success("Dados carregados na memória. Você pode acessar as abas de visualização abaixo.")

    except Exception as e:
        st.error(f"Erro ao processar o Excel: {e}")

# --- Abas interativas após confirmação ---
if "dados_confirmados" in st.session_state and st.session_state["dados_confirmados"]:
    df = st.session_state["df"]
    colunas_categoria = st.session_state["colunas_categoria"]
    colunas_valores = st.session_state["colunas_valores"]

    aba_sankey, aba_barras, aba_dados = st.tabs(["📊 Gráfico Sankey", "📈 Gráficos de Barras", "📁 Dados Importados"])

    with aba_sankey:
        st.subheader("Gráfico Sankey")
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
            default=colunas_categoria[:3] if len(colunas_categoria) >= 3 else colunas_categoria
        )
        value_col = st.selectbox("Coluna de valor para o Sankey", colunas_valores, index=0)

        if len(flux_cols) >= 2 and value_col:
            df_clean = df[flux_cols + [value_col]].dropna()
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

    with aba_barras:
        st.subheader("Gráficos de Barras")
        eixo_x = st.selectbox("Eixo X (categórico)", options=colunas_categoria, index=0)
        eixo_y = st.selectbox("Eixo Y (valor numérico)", options=colunas_valores, index=0)
        agregacao = st.radio("Tipo de agregação", ["Soma", "Média"])

        df_bar = df[[eixo_x, eixo_y]].dropna()
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

    with aba_dados:
        st.subheader("Prévia dos Dados Confirmados")
        st.dataframe(df.head(100))
else:
    st.info("Faça o upload, configure e confirme os dados para liberar as visualizações.")

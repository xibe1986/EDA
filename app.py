from io import BytesIO
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EDA Universal",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {font-size: 2.35rem; font-weight: 800; margin-bottom: 0.2rem;}
    .subtitle {color: #5f6368; font-size: 1.05rem; margin-bottom: 1rem;}
    .block-note {background:#f6f8fa; border:1px solid #e5e7eb; border-radius:12px; padding:1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">EDA Universal para cualquier dataset</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Carga un archivo CSV o Excel y genera un análisis exploratorio inicial: estructura, calidad, estadística y visualizaciones.</div>',
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner=False)
def load_demo():
    return pd.read_csv("data/dataset_demo.csv", parse_dates=["fecha"])

@st.cache_data(show_spinner=False)
def load_file(uploaded_file, decimal, separator):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        if separator == "Automático":
            try:
                return pd.read_csv(uploaded_file, sep=None, engine="python", decimal=decimal)
            except Exception:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, decimal=decimal)
        return pd.read_csv(uploaded_file, sep=separator, decimal=decimal)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Formato no soportado. Usa CSV, XLSX o XLS.")

def try_parse_dates(df):
    result = df.copy()
    for col in result.columns:
        if result[col].dtype == "object":
            converted = pd.to_datetime(result[col], errors="coerce", dayfirst=True)
            if converted.notna().mean() >= 0.75:
                result[col] = converted
    return result

def memory_mb(df):
    return df.memory_usage(deep=True).sum() / (1024 ** 2)

def missing_report(df):
    rep = pd.DataFrame({
        "columna": df.columns,
        "tipo": [str(df[c].dtype) for c in df.columns],
        "nulos": [df[c].isna().sum() for c in df.columns],
        "porcentaje_nulos": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "valores_unicos": [df[c].nunique(dropna=True) for c in df.columns],
    })
    return rep.sort_values("porcentaje_nulos", ascending=False)

with st.sidebar:
    st.header("Carga de datos")
    uploaded = st.file_uploader("Sube un dataset", type=["csv", "xlsx", "xls"])
    usar_demo = st.checkbox("Usar dataset demo", value=uploaded is None)
    separator = st.selectbox("Separador CSV", ["Automático", ",", ";", "|", "\\t"])
    decimal = st.selectbox("Decimal", [".", ","], index=0)
    parse_dates = st.checkbox("Intentar detectar fechas", value=True)
    max_rows_plot = st.slider("Máximo de filas para gráficos", 500, 20000, 5000, 500)

try:
    if uploaded is not None:
        df = load_file(uploaded, decimal=decimal, separator=separator)
    elif usar_demo:
        df = load_demo()
    else:
        st.warning("Carga un archivo o activa el dataset demo.")
        st.stop()
except Exception as e:
    st.error(f"No se pudo cargar el archivo: {e}")
    st.stop()

if parse_dates:
    df = try_parse_dates(df)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Resumen",
    "2. Calidad",
    "3. Estadística",
    "4. Visualización",
    "5. Exportar",
])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas", f"{df.shape[0]:,}")
    c2.metric("Columnas", f"{df.shape[1]:,}")
    c3.metric("Duplicados", f"{df.duplicated().sum():,}")
    c4.metric("Memoria", f"{memory_mb(df):.2f} MB")

    st.markdown("### Vista previa")
    st.dataframe(df.head(100), use_container_width=True)

    st.markdown("### Tipos de datos")
    tipos = pd.DataFrame({
        "columna": df.columns,
        "tipo": [str(df[c].dtype) for c in df.columns],
        "valores_unicos": [df[c].nunique(dropna=True) for c in df.columns],
    })
    st.dataframe(tipos, use_container_width=True)

with tab2:
    st.markdown("### Reporte de valores nulos")
    miss = missing_report(df)
    st.dataframe(miss, use_container_width=True)

    if miss["nulos"].sum() > 0:
        fig = px.bar(
            miss[miss["nulos"] > 0],
            x="columna",
            y="porcentaje_nulos",
            title="Porcentaje de valores nulos por columna",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No se detectaron valores nulos.")

    st.markdown("### Duplicados")
    st.write(f"Filas duplicadas detectadas: **{df.duplicated().sum():,}**")

with tab3:
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()

    st.markdown("### Variables numéricas")
    if numeric_cols:
        st.dataframe(df[numeric_cols].describe().T, use_container_width=True)
    else:
        st.info("No se detectaron columnas numéricas.")

    st.markdown("### Variables categóricas")
    if cat_cols:
        cat_summary = pd.DataFrame({
            "columna": cat_cols,
            "valores_unicos": [df[c].nunique(dropna=True) for c in cat_cols],
            "valor_mas_frecuente": [df[c].mode(dropna=True).iloc[0] if not df[c].mode(dropna=True).empty else None for c in cat_cols],
        })
        st.dataframe(cat_summary, use_container_width=True)
    else:
        st.info("No se detectaron columnas categóricas.")

    st.markdown("### Variables de fecha")
    if date_cols:
        date_summary = pd.DataFrame({
            "columna": date_cols,
            "fecha_min": [df[c].min() for c in date_cols],
            "fecha_max": [df[c].max() for c in date_cols],
        })
        st.dataframe(date_summary, use_container_width=True)
    else:
        st.info("No se detectaron columnas de fecha.")

with tab4:
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    all_cols = df.columns.tolist()

    if len(df) > max_rows_plot:
        plot_df = df.sample(max_rows_plot, random_state=42)
        st.caption(f"Se está graficando una muestra de {max_rows_plot:,} filas para mejorar el rendimiento.")
    else:
        plot_df = df.copy()

    chart_type = st.selectbox(
        "Tipo de gráfico",
        ["Histograma", "Barras", "Dispersión", "Caja", "Línea", "Correlación"],
    )

    if chart_type == "Histograma":
        if numeric_cols:
            x = st.selectbox("Variable numérica", numeric_cols)
            fig = px.histogram(plot_df, x=x, nbins=30, title=f"Distribución de {x}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requiere al menos una variable numérica.")

    elif chart_type == "Barras":
        x = st.selectbox("Variable categórica o discreta", all_cols)
        y_options = ["Conteo"] + numeric_cols
        y = st.selectbox("Métrica", y_options)
        if y == "Conteo":
            grouped = plot_df[x].astype(str).value_counts().head(25).reset_index()
            grouped.columns = [x, "conteo"]
            fig = px.bar(grouped, x=x, y="conteo", title=f"Conteo por {x}")
        else:
            grouped = plot_df.groupby(x, dropna=False)[y].mean().sort_values(ascending=False).head(25).reset_index()
            fig = px.bar(grouped, x=x, y=y, title=f"Promedio de {y} por {x}")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Dispersión":
        if len(numeric_cols) >= 2:
            x = st.selectbox("Eje X", numeric_cols)
            y = st.selectbox("Eje Y", numeric_cols, index=1)
            color = st.selectbox("Color opcional", ["Ninguno"] + all_cols)
            fig = px.scatter(
                plot_df,
                x=x,
                y=y,
                color=None if color == "Ninguno" else color,
                title=f"{y} vs {x}",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requieren al menos dos variables numéricas.")

    elif chart_type == "Caja":
        if numeric_cols:
            y = st.selectbox("Variable numérica", numeric_cols)
            x = st.selectbox("Agrupar por", ["Ninguno"] + all_cols)
            fig = px.box(
                plot_df,
                x=None if x == "Ninguno" else x,
                y=y,
                title=f"Boxplot de {y}",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requiere al menos una variable numérica.")

    elif chart_type == "Línea":
        x = st.selectbox("Eje X", all_cols)
        if numeric_cols:
            y = st.selectbox("Eje Y", numeric_cols)
            temp = plot_df.sort_values(x)
            fig = px.line(temp, x=x, y=y, title=f"Evolución de {y} según {x}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requiere al menos una variable numérica.")

    elif chart_type == "Correlación":
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr(numeric_only=True)
            fig = px.imshow(corr, text_auto=True, title="Matriz de correlación")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requieren al menos dos variables numéricas.")

with tab5:
    st.markdown("### Exportar reportes generados")
    miss = missing_report(df)
    st.download_button(
        "Descargar reporte de calidad CSV",
        data=miss.to_csv(index=False).encode("utf-8"),
        file_name="reporte_calidad_datos.csv",
        mime="text/csv",
    )

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if numeric_cols:
        stats = df[numeric_cols].describe().T
        st.download_button(
            "Descargar estadística descriptiva CSV",
            data=stats.to_csv().encode("utf-8"),
            file_name="estadistica_descriptiva.csv",
            mime="text/csv",
        )

    st.markdown(
        """
        <div class="block-note">
        <b>Reto sugerido:</b> agregar una sección de limpieza de datos que permita eliminar duplicados,
        reemplazar nulos y descargar el dataset limpio.
        </div>
        """,
        unsafe_allow_html=True,
    )

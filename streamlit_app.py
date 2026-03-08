import streamlit as st
import ee
import geemap.foliumap as geemap # Versão otimizada para Streamlit
import pandas as pd
import matplotlib.pyplot as plt
import json

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

# Carrega o dicionário completo da chave
credentials_info = st.secrets["earth_engine_key"]

# Inicializa com as credenciais da Service Account
credentials = ee.ServiceAccountCredentials(
    credentials_info["client_email"], 
    key_data=credentials_info["private_key"]
)
ee.Initialize(credentials, project="ee-passeionamatamapas")


# --- AUTENTICAÇÃO SEGURA ---
# No Streamlit Cloud, você coloca o conteúdo do JSON em "Secrets"
#def authenticate_ee():
#    if 'EE_KEYS' in st.secrets:
#        gee_json = json.loads(st.secrets['EE_KEYS'])
#        credentials = ee.ServiceAccountCredentials(gee_json['client_email'], key_data=gee_json['private_key'])
#        ee.Initialize(credentials, project=gee_json['project_id'])
#    else:
        # Para rodar localmente com sua conta pessoal
#        ee.Initialize(project="ee-passeionamatamapas")

#authenticate_ee()

st.set_page_config(layout="wide")
st.title("Monitoramento de Uso do Solo - Campinas")

# --- DADOS ---
mapbiomas = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1')
limite = ee.FeatureCollection("projects/ee-rogergodoytest/assets/limite_municipal")

de = [1, 2, 3, 4, 5, 49, 10, 11, 12, 32, 29, 13, 14, 15, 18, 19, 39, 20, 40, 62, 21, 24, 33, 31]
para = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4, 4]
palette = ['#FFFFFF', '#006400', '#FFFFB2', '#EA3C53', '#0000FF']
nomes_legenda = ['Outros', 'Floresta', 'Rural', 'Urbana', 'Água']

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    st.header("Configurações")
    modo = st.radio("Selecione o Modo:", ["Série Temporal", "Comparação (Split)"])
    
    anos = [str(a) for a in range(2024, 1984, -1)]
    
    if modo == "Série Temporal":
        ano_selecionado = st.selectbox("Escolha o Ano:", anos)
    else:
        col1, col2 = st.columns(2)
        ano_esq = col1.selectbox("Esquerda:", anos, index=len(anos)-1)
        ano_dir = col2.selectbox("Direita:", anos, index=0)

# --- PROCESSAMENTO ---
def get_reclassed_image(ano):
    banda = f'classification_{ano}'
    return mapbiomas.select(banda).clip(limite).remap(de, para, 0).uint8()

# --- MAPA ---
m = geemap.Map()
m.centerObject(limite, 12)

if modo == "Série Temporal":
    img = get_reclassed_image(ano_selecionado)
    m.add_layer(img, {'min': 0, 'max': 4, 'palette': palette}, f"Uso {ano_selecionado}")
    
    # Cálculo de Áreas para o gráfico
    area_img = ee.Image.pixelArea().addBands(img)
    stats = area_img.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName='classe'),
        geometry=limite.geometry(),
        scale=30,
        maxPixels=1e13
    ).getInfo()
    
    # Gerar Gráfico na Sidebar
    if 'groups' in stats:
        df = pd.DataFrame([{'Classe': nomes_legenda[int(g['classe'])], 'Hectares': g['sum']/10000} for g in stats['groups']])
        st.sidebar.write(df)
        fig, ax = plt.subplots()
        df.plot(kind='bar', x='Classe', y='Hectares', ax=ax, color=palette[1:])
        st.sidebar.pyplot(fig)

else:
    left_layer = geemap.ee_tile_layer(get_reclassed_image(ano_esq), {'min': 0, 'max': 4, 'palette': palette}, "Esq")
    right_layer = geemap.ee_tile_layer(get_reclassed_image(ano_dir), {'min': 0, 'max': 4, 'palette': palette}, "Dir")
    m.split_map(left_layer, right_layer)

m.to_streamlit(height=700)

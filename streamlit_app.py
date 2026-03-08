import streamlit as st
import ee
import geemap
import pandas as pd
import matplotlib.pyplot as plt
import json

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MapBiomas Campinas", layout="wide")

# --- 2. DEFINIÇÃO DE VARIÁVEIS GLOBAIS (FORA DE QUALQUER BLOCO) ---
# Definir aqui para que 'anos_lista' esteja disponível em todo o script
anos_lista = [str(a) for a in range(2024, 1984, -1)]
nomes_legenda = ['Outros', 'Floresta', 'Rural', 'Urbana', 'Água']
palette = ['#FFFFFF', '#006400', '#FFFFB2', '#EA3C53', '#0000FF']

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

# --- 4. DADOS ---
mapbiomas = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1')
limite = ee.FeatureCollection("projects/ee-rogergodoytest/assets/limite_municipal")

# Reclassificação
de = [1, 2, 3, 4, 5, 49, 10, 11, 12, 32, 29, 13, 14, 15, 18, 19, 39, 20, 40, 62, 21, 24, 33, 31]
para = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4, 4]

# --- 5. FUNÇÕES ---
def formatar_imagem(ano):
    banda = f'classification_{ano}'
    return mapbiomas.select(banda).clip(limite).remap(de, para, 0).uint8()

@st.cache_data
def carregar_dados_area(ano):
    img = formatar_imagem(ano)
    area_img = ee.Image.pixelArea().addBands(img)
    stats = area_img.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName='classe'),
        geometry=limite.geometry(),
        scale=30,
        maxPixels=1e13
    ).getInfo()
    
    res = []
    if 'groups' in stats:
        for g in stats['groups']:
            idx = int(g['classe'])
            if idx < len(nomes_legenda):
                res.append({'Classe': nomes_legenda[idx], 'Hectares': round(g['sum']/10000, 2)})
    return pd.DataFrame(res)

# --- 6. INTERFACE (SIDEBAR) ---
st.sidebar.header("⚙️ Painel de Controle")
modo = st.sidebar.radio("Selecione o modo:", ["Análise Temporal", "Comparação Lado a Lado"])

# --- 7. CONSTRUÇÃO DO MAPA ---
st.title("🛰️ Monitoramento de Uso do Solo - Campinas")

m = geemap.Map(basemap="HYBRID")
m.centerObject(limite, 12)

if modo == "Análise Temporal":
    ano_sel = st.sidebar.selectbox("Escolha o ano:", anos_lista)
    img = formatar_imagem(ano_sel)
    m.add_layer(img, {'min': 0, 'max': 4, 'palette': palette}, f"Uso {ano_sel}")
    
    # Estatísticas na Sidebar
    df_area = carregar_dados_area(ano_sel)
    st.sidebar.subheader(f"Estatísticas - {ano_sel}")
    st.sidebar.dataframe(df_area, hide_index=True)
    
    fig, ax = plt.subplots(figsize=(5, 3))
    df_plot = df_area[df_area['Classe'] != 'Outros']
    ax.bar(df_plot['Classe'], df_plot['Hectares'], color=palette[1:])
    plt.xticks(rotation=45)
    st.sidebar.pyplot(fig)

else:
    # MODO COMPARATIVO (Split Map)
    col1, col2 = st.sidebar.columns(2)
    ano_esq = col1.selectbox("Esquerda:", anos_lista, index=len(anos_lista)-1)
    ano_dir = col2.selectbox("Direita:", anos_lista, index=0)
    
    # 1. Criamos as camadas de Tile do Earth Engine
    # Note que usamos 'vis_params' separados para clareza
    vis_params = {'min': 0, 'max': 4, 'palette': palette}
    
    left_layer = geemap.ee_tile_layer(formatar_imagem(ano_esq), vis_params, f"Uso {ano_esq}")
    right_layer = geemap.ee_tile_layer(formatar_imagem(ano_dir), vis_params, f"Uso {ano_dir}")
    
    # 2. Adicionamos as camadas ao mapa MANUALMENTE antes do split
    m.add_layer(left_layer)
    m.add_layer(right_layer)
    
    # 3. Chamamos o split_map passando as camadas EXATAS que acabamos de adicionar
    # No geemap.foliumap, isso ativa o SideBySideControl do Folium
    m.split_map(left_layer=left_layer, right_layer=right_layer)

# Exibe o mapa
m.to_streamlit(height=700)

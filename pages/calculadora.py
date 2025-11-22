import streamlit as st
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# --- CONFIGURAÇÃO VISUAL (ACESSIBILIDADE) ---
st.set_page_config(page_title="Calc NeuroDiv", page_icon="➗", layout="centered")

st.markdown("""
<style>
    /* Fonte Amigável e Grande */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; font-size: 18px; }
    
    /* Fundo Escuro Suave */
    .stApp { background-color: #2E3035; color: #FFFFFF; }
    
    /* Input Gigante */
    .stTextInput input {
        font-size: 24px; padding: 15px; border-radius: 10px;
        background-color: #1F2126; color: white; border: 2px solid #0078D4;
    }
    
    /* Botão de Calcular em Destaque */
    div.stButton > button {
        width: 100%;
        background-color: #0078D4; color: white; 
        font-size: 20px; font-weight: bold; padding: 15px;
        border-radius: 10px; border: none; margin-top: 10px;
    }
    div.stButton > button:hover { background-color: #005A9E; }
    
    /* Caixa de Resultado */
    .resultado-box {
        background-color: #1F2126; padding: 25px; 
        border-radius: 15px; border-left: 10px solid #00D47E;
        margin-top: 20px; font-size: 20px; line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- TÍTULO ---
st.title("➗ Calculadora Neurodiv")
st.markdown("Resolvemos a conta passo a passo.")

# --- CONFIGURAÇÃO DAS CHAVES ---
try:
    endpoint = st.secrets["AZURE_ENDPOINT"]
    key = st.secrets["AZURE_KEY"]
    model_name = "Phi-4" # Ou o nome do seu deploy
except:
    with st.sidebar:
        st.warning("Chaves não encontradas.")
        endpoint = st.text_input("Endpoint Azure:")
        key = st.text_input("Chave API:", type="password")
        model_name = "Phi-4"

# --- INTERFACE DE CÁLCULO ---

# Botões de Exemplo (Ajudam quem tem dificuldade de digitar)
col1, col2, col3 = st.columns(3)
exemplo = ""
if col1.button("639 ÷ 3"): exemplo = "639 dividido por 3"
if col2.button("480 ÷ 4"): exemplo = "480 dividido por 4"
if col3.button("125 + 48"): exemplo = "125 mais 48"

# Campo de Entrada
conta_usuario = st.text_input("Que conta vamos fazer?", value=exemplo, placeholder="Ex: 248 dividido por 2")

if st.button("Calcular Agora"):
    if not key or not endpoint:
        st.error("Preciso das chaves de acesso para calcular.")
        st.stop()
        
    if not conta_usuario:
        st.warning("Digite uma conta primeiro.")
        st.stop()

    # --- O CÉREBRO (PROMPT DE DECOMPOSIÇÃO) ---
    try:
        client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
            api_version="2024-05-01-preview"
        )

        system_prompt = """
        ### PERFIL ###
        Você é um Tutor de Matemática Especializado em Discalculia.
        Sua missão é resolver contas usando EXCLUSIVAMENTE o "Método da Decomposição".
        NUNCA use o método da chave tradicional.
        
        ### O MÉTODO (PASSO A PASSO) ###
        1. DECOMPOR: Separe o número falando em voz alta ("Eu tenho 600, tenho 30...").
        2. OPERAR: Faça a conta com cada pedaço separadamente.
        3. JUNTAR: Some os resultados parciais.
        4. MOSTRAR RESULTADO: Em destaque.

        ### REGRAS VISUAIS ###
        - Use listas com marcadores (•) para organizar.
        - Use negrito para números importantes.
        - Seja muito didático e paciente.
        - Se for divisão, explique como se estivesse dividindo dinheiro ou objetos.
        """

        with st.spinner("Desmontando os números..."):
            response = client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=f"Resolva: {conta_usuario}")
                ],
                model=model_name,
                temperature=0.1, # Baixa criatividade para não errar conta
                max_tokens=500
            )

            # Exibe o resultado formatado
            resultado = response.choices[0].message.content
            st.markdown(f"<div class='resultado-box'>{resultado}</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao calcular: {e}")

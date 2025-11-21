import streamlit as st
import os
import json
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NeuroDiv JSON", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
    .stApp { background-color: #2E3035; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #E0E0E0 !important; }
    div.stButton > button { background-color: #0078D4 !important; color: white !important; border: none; font-weight: bold; }
    
    /* Caixas de Resposta */
    .item-box {
        background-color: #1F2126; 
        padding: 10px 15px; 
        border-radius: 8px; 
        border-left: 4px solid #00D47E; 
        margin-bottom: 8px;
        font-size: 16px;
    }
    .source-tag { font-size: 11px; color: #888; margin-top: 10px; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- 2. CARREGAR DOCUMENTOS ---
@st.cache_resource
def carregar_base():
    texto = ""
    if os.path.exists("docs"):
        for f in os.listdir("docs"):
            if f.endswith(".txt"):
                try:
                    with open(os.path.join("docs", f), "r", encoding="utf-8") as file:
                        texto += f"\n--- ARQUIVO: {f} ---\n{file.read()}\n"
                except: pass
    return texto

base_conhecimento = carregar_base()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Sistema")
    if base_conhecimento:
        st.success("Arquivos Carregados")
        with st.expander("Ver conteúdo lido (Debug)"):
            st.text(base_conhecimento)
    else:
        st.error("❌ ERRO: Pasta 'docs' vazia.")
        
    if st.button("Limpar Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 4. CHATBOT ---
st.title("🛡️ Protocolos NeuroDiv")

# Conexão
try:
    client = ChatCompletionsClient(
        endpoint=st.secrets["AZURE_ENDPOINT"],
        credential=AzureKeyCredential(st.secrets["AZURE_KEY"]),
        api_version="2024-05-01-preview"
    )
except:
    st.error("Configure as chaves.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Qual o problema escolar?"})

# Exibe chat
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        # 
        st.chat_message("assistant").markdown(msg["content"], unsafe_allow_html=True)

# --- 5. LÓGICA: JSON MODE ---
if prompt := st.chat_input("Ex: Adaptação prova TDAH"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    if not base_conhecimento:
        st.error("Sem documentos.")
        st.stop()

    with st.spinner("Extraindo dados estruturados..."):
        try:
            prompt_usuario = st.session_state.messages[-1]["content"]
            
            # PROMPT QUE OBRIGA JSON
            # Isso impede a IA de conversar. Ela só pode gerar dados.
            system_instruction = f"""
            VOCÊ É UMA API DE EXTRAÇÃO DE DADOS.
            
            CONTEXTO (DOCUMENTOS):
            {base_conhecimento}
            
            SUA TAREFA:
            Buscar a solução para "{prompt_usuario}" nos documentos e retornar um JSON.
            
            FORMATO JSON OBRIGATÓRIO:
            {{
                "encontrou": true,
                "lista_acoes": [
                    "Ação 1 (copiada do texto)",
                    "Ação 2 (copiada do texto)",
                    "Ação 3 (copiada do texto)"
                ]
            }}
            
            REGRAS:
            1. Se não achar no texto, retorne {{"encontrou": false, "lista_acoes": []}}.
            2. NÃO invente. Copie do texto.
            3. Responda APENAS o JSON. Nada de "Aqui está".
            """
            
            # Movemos tudo para a mensagem do usuário para dar mais peso (Atenção)
            msgs = [
                SystemMessage(content="Você é um gerador de JSON."),
                UserMessage(content=system_instruction)
            ]
            
            response = client.complete(
                messages=msgs,
                model="Phi-4", # Ou o nome do seu modelo
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"} # Força modo JSON se suportado
            )
            
            resposta_json = response.choices[0].message.content
            
            # PROCESSAMENTO DO PYTHON 
            try:
                dados = json.loads(resposta_json)
                
                if dados.get("encontrou") and dados.get("lista_acoes"):
                    html_final = ""
                    for acao in dados["lista_acoes"]:
                        html_final += f"<div class='item-box'>✅ {acao}</div>"
                    html_final += "<div class='source-tag'>Fonte: Documentos Internos</div>"
                else:
                    html_final = "<div class='item-box'>⚠️ Informação não consta nos documentos carregados.</div>"
                    
            except json.JSONDecodeError:
                # Fallback caso a IA falhe no JSON (raro com temperatura 0)
                html_final = f"Erro de formatação da IA. Resposta bruta:\n{resposta_json}"

            st.session_state.messages.append({"role": "assistant", "content": html_final})
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro: {e}")

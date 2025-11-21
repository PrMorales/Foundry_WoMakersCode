import streamlit as st
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NeuroDiv Chat", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
    .stApp { background-color: #2E3035; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #E0E0E0 !important; }
    .stChatMessage { background-color: #1F2126; border: 1px solid #444; }
    div.stButton > button { background-color: #0078D4 !important; color: white !important; border: none; font-weight: 600; }
    .source-footer { font-size: 11px; color: #888; margin-top: 10px; border-top: 1px solid #444; padding-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CARREGAR DOCUMENTOS ---
@st.cache_resource
def carregar_documentos():
    texto_total = ""
    pasta = "docs"
    if not os.path.exists(pasta): return ""
    
    # Lê arquivos .txt
    for arq in os.listdir(pasta):
        if arq.endswith(".txt"):
            try:
                caminho = os.path.join(pasta, arq)
                with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                    # Adiciona delimitadores claros para ajudar a IA
                    texto_total += f"\n--- INÍCIO DO ARQUIVO: {arq} ---\n{f.read()}\n--- FIM DO ARQUIVO ---\n"
            except: pass
    return texto_total

base_conhecimento = carregar_documentos()

# --- 3. INTERFACE ---
with st.sidebar:
    st.title("📂 Status do Sistema")
    if base_conhecimento:
        st.success(f"Base Carregada ({len(base_conhecimento)} caracteres)")
        # Lista arquivos para conferência
        if os.path.exists("docs"):
            for f in os.listdir("docs"):
                if f.endswith(".txt"): st.caption(f"📄 {f}")
    else:
        st.error("⚠️ Pasta 'docs' vazia!")
    
    if st.button("🧹 Limpar Chat"):
        st.session_state.messages = []
        st.rerun()

st.title("💬 NEUROdiv")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Qual o problema do aluno?"})

# Conexão
try:
    client = ChatCompletionsClient(
        endpoint=st.secrets["AZURE_ENDPOINT"],
        credential=AzureKeyCredential(st.secrets["AZURE_KEY"]),
        api_version="2024-05-01-preview"
    )
except:
    st.error("Erro de Chaves.")
    st.stop()

# Histórico
for msg in st.session_state.messages:
    role_style = "background-color: #0078D4;" if msg["role"] == "user" else "background-color: #1F2126;"
    st.markdown(f"<div style='{role_style}; padding: 15px; border-radius: 10px; margin-bottom: 10px;'>{msg['content']}</div>", unsafe_allow_html=True)

# --- 4. LÓGICA DE ENVIO ---
if prompt := st.chat_input("Ex: Adaptação para TDAH"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    if not base_conhecimento:
        st.error("Sem documentos para ler.")
        st.stop()

    with st.spinner("Analisando..."):
        try:
            prompt_usuario = st.session_state.messages[-1]["content"]
            
            # --- CORREÇÃO NO PROMPT ---
            # Adicionamos lógica de EXCLUSÃO MÚTUA (Ou um Ou outro)
            system_instruction = f"""
            VOCÊ É UM ROBÔ EXTRATOR DE DADOS.
            
            === BANCO DE DADOS ===
            {base_conhecimento}
            ======================
            
            SUA TAREFA:
            Verificar se existe resposta para "{prompt_usuario}" no banco de dados acima.
            
            LÓGICA DE DECISÃO (SIGA ESTRITAMENTE):
            CASO 1: A informação EXISTE no texto.
               -> AÇÃO: Copie a lista de estratégias exatamente como está no texto.
               -> FINALIZAÇÃO: Pare de escrever imediatamente após o último item. NÃO escreva avisos de erro.
            
            CASO 2: A informação NÃO EXISTE no texto.
               -> AÇÃO: Escreva APENAS: "Informação não consta nos protocolos."
               -> FINALIZAÇÃO: Pare.
            
            REGRAS DE FORMATAÇÃO:
            - Use apenas lista com marcadores (•).
            - Sem introduções ("Aqui está", "Olá").
            - Sem conclusões.
            """
            
            msgs = [
                SystemMessage(content=system_instruction),
                UserMessage(content=prompt_usuario)
            ]
            
            response = client.complete(
                messages=msgs, 
                model="Phi-4-mini-instruct", # Confirme se o nome é esse ou "Phi-4"
                temperature=0.1, 
                max_tokens=400
            )
            
            resposta = response.choices[0].message.content
            
            # Rodapé
            resposta_final = f"{resposta}\n\n<div class='source-footer'>Fonte: Documentos Internos</div>"
            
            st.session_state.messages.append({"role": "assistant", "content": resposta_final})
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro: {e}")

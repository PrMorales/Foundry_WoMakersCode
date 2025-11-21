import streamlit as st
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# ==========================================
# 1. CONFIGURAÇÃO VISUAL
# ==========================================
st.set_page_config(page_title="NeuroDiv Phi-4", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
    .stApp { background-color: #2E3035; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #E0E0E0 !important; }
    .stChatMessage { background-color: #1F2126; border: 1px solid #444; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessageAvatarUser"] { background-color: #0078D4; }
    div.stButton > button { background-color: #0078D4 !important; color: white !important; border: none; font-weight: 600; }
    .source-box { font-size: 11px; color: #00D47E; margin-top: 8px; border-top: 1px solid #444; padding-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARREGAR DOCUMENTOS (RAG)
# ==========================================
@st.cache_resource
def carregar_documentos():
    texto_total = ""
    pasta = "docs"
    
    if not os.path.exists(pasta): return ""
    
    for arq in os.listdir(pasta):
        if arq.endswith(".txt"):
            try:
                caminho = os.path.join(pasta, arq)
                with open(caminho, "r", encoding="utf-8") as f:
                    # Adiciona tags para o modelo saber onde começa e termina cada arquivo
                    texto_total += f"\n=== ARQUIVO: {arq} ===\n{f.read()}\n"
            except: pass
    return texto_total

base_conhecimento = carregar_documentos()

# ==========================================
# 3. BARRA LATERAL
# ==========================================
with st.sidebar:
    st.title("📂 Base de Dados (Phi-4)")
    if base_conhecimento:
        st.success("Docs Carregados")
        with st.expander("Ver arquivos lidos"):
            if os.path.exists("docs"):
                for f in os.listdir("docs"):
                    if f.endswith(".txt"): st.write(f"📄 {f}")
    else:
        st.error("⚠️ Pasta 'docs' vazia!")
    
    if st.button("🧹 Limpar Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. CHATBOT
# ==========================================
st.title("🛡️ NEUROdiv ")
st.caption(" Auxiliar de Inclusão e Acessibilidade na Escola.")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Em que posso ajudar?"
    })

# Conexão
try:
    client = ChatCompletionsClient(
        endpoint=st.secrets["AZURE_ENDPOINT"],
        credential=AzureKeyCredential(st.secrets["AZURE_KEY"]),
        api_version="2024-05-01-preview"
    )
    # ATENÇÃO AQUI: Atualizado para o modelo correto
    MODEL_NAME = "Phi-4" 
except:
    st.error("Erro nas chaves.")
    st.stop()

# Exibe histórico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE INTELIGÊNCIA
# ==========================================
if prompt := st.chat_input("Ex: Como adaptar prova para TDAH?"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    # Trava de segurança
    if not base_conhecimento:
        st.session_state.messages.append({"role": "assistant", "content": "🚫 ERRO: Sem documentos para ler."})
        st.rerun()

    with st.spinner("Processando com Phi-4..."):
        try:
            prompt_usuario = st.session_state.messages[-1]["content"]
            
            # PROMPT OTIMIZADO PARA PHI-4 (Ele entende instruções complexas melhor)
            system_instruction = f"""
            VOCÊ É UM ANALISTA TÉCNICO DE DOCUMENTOS ESCOLARES.
            
            === SUA BASE DE DADOS (LEIA TUDO) ===
            {base_conhecimento}
            =====================================
            
            SUA TAREFA:
            Responder à pergunta "{prompt_usuario}" usando ESTRITAMENTE o conteúdo da Base de Dados acima.
            
            REGRAS RÍGIDAS:
            1. Identifique o arquivo correto (ex: se a pergunta é TDAH, use o texto do TDAH).
            2. COPIE as estratégias do texto. Não parafraseie se não precisar.
            3. Formate como lista (bullets).
            4. NÃO invente.
            5. Seja direto. Sem "Olá" ou "Espero ter ajudado".
            """
            
            msgs = [
                SystemMessage(content=system_instruction),
                UserMessage(content=prompt_usuario)
            ]
            
            response = client.complete(
                messages=msgs, 
                model=MODEL_NAME, # Usando a variável atualizada
                temperature=0.1,  
                max_tokens=500    
            )
            
            resposta = response.choices[0].message.content
            
            # Adiciona rodapé
            resposta_final = f"{resposta}\n\n<div class='source-box'>Gerado por Phi-4 | Fonte: Docs Internos</div>"
            
            st.session_state.messages.append({"role": "assistant", "content": resposta_final})
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro na conexão: {e}")


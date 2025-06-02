# app.py
import streamlit as st

# --- Configuração de Usuários Válidos (SOMENTE PARA FINS DIDÁTICOS) ---
USUARIOS_VALIDOS = {
    "admin": "admin123",
    "joao": "senha123",
    "edu": "abc",
    "roger": "xyz"
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "nome_usuario" not in st.session_state:
    st.session_state.nome_usuario = None

def mostrar_formulario_login():
    st.title("Login - Sistema da Academia")
    st.write("Por favor, insira suas credenciais para continuar.")

    with st.form("login_form_simples"):
        usuario_digitado = st.text_input("Nome de Usuário")
        senha_digitada = st.text_input("Senha", type="password")
        botao_login = st.form_submit_button("Entrar")

        if botao_login:
            if usuario_digitado in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario_digitado] == senha_digitada:
                st.session_state.autenticado = True
                st.session_state.nome_usuario = usuario_digitado
                st.success(f"Login bem-sucedido como {usuario_digitado}!")
                st.rerun() 
            else:
                st.error("Nome de usuário ou senha inválidos.")

def mostrar_botao_logout():
    # Garante que nome_usuario existe antes de tentar usá-lo no botão
    nome_display = st.session_state.get("nome_usuario", "Usuário") 
    if st.sidebar.button(f"Sair ({nome_display})"): # Modificado para incluir o nome
        st.session_state.autenticado = False
        st.session_state.nome_usuario = None
        st.info("Você saiu do sistema.")
        st.rerun()

if not st.session_state.autenticado:
    mostrar_formulario_login()
else:
    mostrar_botao_logout()

    st.sidebar.markdown("---")
    st.sidebar.header("Menu Principal")

    st.title("Painel Principal - Sistema da Academia")
    st.header(f"Bem-vindo(a), {st.session_state.nome_usuario}!")
    st.markdown("Você está logado e pode acessar as funcionalidades do sistema.")
    st.markdown("Use o menu na barra lateral para navegar pelas diferentes seções (se houver páginas definidas).")

    if st.session_state.nome_usuario == "admin":
        st.subheader("Área Administrativa")
        st.write("Você tem acesso de administrador.")
    else:
        st.subheader("Área do Usuário Padrão")
        st.write("Funcionalidades padrão para usuários.")
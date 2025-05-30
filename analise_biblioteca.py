import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

conn = sqlite3.connect("biblioteca.db")
cursor = conn.cursor()

# Criação das tabelas (executado sempre que o app roda)
cursor.execute('''CREATE TABLE IF NOT EXISTS autores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS livros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    autor_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    quantidade_disponivel INTEGER,
    FOREIGN KEY (autor_id) REFERENCES autores (id),
    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS emprestimos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    livro_id INTEGER NOT NULL,
    data_emprestimo DATE NOT NULL,
    devolvido BOOLEAN NOT NULL,
    FOREIGN KEY (livro_id) REFERENCES livros (id)
)''')

conn.commit()

# Inserção de dados apenas se a tabela estiver vazia
if cursor.execute("SELECT COUNT(*) FROM autores").fetchone()[0] == 0:
    autores_data = [
        ("Machado de Assis",), ("Clarice Lispector",), ("Jorge Amado",),
        ("Cecília Meireles",), ("Carlos Drummond de Andrade",), ("Graciliano Ramos",),
        ("Monteiro Lobato",), ("Guimarães Rosa",), ("Rachel de Queiroz",), ("Lygia Fagundes Telles",)
    ]
    cursor.executemany("INSERT INTO autores (nome) VALUES (?)", autores_data)
    conn.commit()

if cursor.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 0:
    categorias_data = [
        ("Romance",), ("Ficção Científica",), ("Fantasia",), ("Poesia",), ("Conto",),
        ("Infantil",), ("Suspense",), ("Crônica",), ("Biografia",), ("Literatura Brasileira",)
    ]
    cursor.executemany("INSERT INTO categorias (nome) VALUES (?)", categorias_data)
    conn.commit()

# Mapeia autores e categorias por nome
autores_map = {nome: id for id, nome in cursor.execute("SELECT id, nome FROM autores")}
categorias_map = {nome: id for id, nome in cursor.execute("SELECT id, nome FROM categorias")}

# Inserir livros apenas se ainda não existirem
if cursor.execute("SELECT COUNT(*) FROM livros").fetchone()[0] == 0:
    livros_data = [
        ("Dom Casmurro", autores_map["Machado de Assis"], categorias_map["Romance"], 1899, 5),
        ("A Hora da Estrela", autores_map["Clarice Lispector"], categorias_map["Romance"], 1977, 3),
        ("Capitães da Areia", autores_map["Jorge Amado"], categorias_map["Romance"], 1937, 7),
        ("Ou Isto ou Aquilo", autores_map["Cecília Meireles"], categorias_map["Poesia"], 1964, 4),
        ("Sentimento do Mundo", autores_map["Carlos Drummond de Andrade"], categorias_map["Poesia"], 1940, 6),
        ("Vidas Secas", autores_map["Graciliano Ramos"], categorias_map["Romance"], 1938, 2),
        ("Reinações de Narizinho", autores_map["Monteiro Lobato"], categorias_map["Infantil"], 1931, 10),
        ("Grande Sertão: Veredas", autores_map["Guimarães Rosa"], categorias_map["Romance"], 1956, 3),
        ("Memórias Póstumas de Brás Cubas", autores_map["Machado de Assis"], categorias_map["Romance"], 1881, 5),
        ("O Quinze", autores_map["Rachel de Queiroz"], categorias_map["Romance"], 1930, 4),
    ]
    cursor.executemany("INSERT INTO livros (titulo, autor_id, categoria_id, ano, quantidade_disponivel) VALUES (?, ?, ?, ?, ?)", livros_data)
    conn.commit()

# --------- VISUALIZAÇÕES ---------
st.title("📚 Biblioteca")

st.subheader("📋 Livros com autores e categorias")
df_livros = pd.read_sql_query("""
SELECT l.titulo AS 'Título', a.nome AS 'Autor', c.nome AS 'Categoria'
FROM livros l
JOIN autores a ON l.autor_id = a.id
JOIN categorias c ON l.categoria_id = c.id
ORDER BY l.titulo
""", conn)
st.dataframe(df_livros, use_container_width=True)

st.subheader("🔍 Filtro por ano de publicação")
ano_min = st.slider("Ano mínimo", 1800, 2000, value=1900)
df_filtrado = pd.read_sql_query("SELECT * FROM livros WHERE ano > ?", conn, params=(ano_min,))
st.dataframe(df_filtrado)

st.subheader("📊 Resumo de Estoque e Empréstimos")
df_resumo = pd.read_sql_query('''
SELECT
    (SELECT SUM(quantidade_disponivel) FROM livros) AS "Total em Estoque",
    (SELECT COUNT(*) FROM emprestimos) AS "Total de Empréstimos",
    (SELECT COUNT(*) FROM emprestimos WHERE devolvido = 1) AS "Devolvidos"
''', conn)
st.dataframe(df_resumo)

st.subheader("📚 Número de livros por categoria")
df_por_categoria = pd.read_sql_query('''
SELECT c.nome AS "Categoria", COUNT(l.id) AS "Quantidade de Livros"
FROM livros l
JOIN categorias c ON l.categoria_id = c.id
GROUP BY c.nome
ORDER BY COUNT(l.id) DESC
''', conn)
st.dataframe(df_por_categoria)

# --------- INSERIR NOVO LIVRO ---------
st.header("📘 Registrar novo livro")
with st.form("form_livro"):
    titulo = st.text_input("Título")
    autor_nome = st.selectbox("Autor", list(autores_map.keys()))
    categoria_nome = st.selectbox("Categoria", list(categorias_map.keys()))
    ano = st.number_input("Ano de Publicação", min_value=1000)
    qtd = st.number_input("Quantidade em Estoque", min_value=1, step=1)
    inserir = st.form_submit_button("Inserir Livro")

    if inserir:
        cursor.execute("INSERT INTO livros (titulo, autor_id, categoria_id, ano, quantidade_disponivel) VALUES (?, ?, ?, ?, ?)",
                       (titulo, autores_map[autor_nome], categorias_map[categoria_nome], ano, qtd))
        conn.commit()
        st.success("Livro inserido com sucesso!")
        st.rerun()

# --------- REGISTRAR EMPRÉSTIMO ---------
st.header("📖 Registrar novo empréstimo")
livros_disponiveis = cursor.execute("SELECT id, titulo, quantidade_disponivel FROM livros WHERE quantidade_disponivel > 0").fetchall()
mapa_livro = {f"{l[1]} (Estoque: {l[2]})": l[0] for l in livros_disponiveis}

with st.form("form_emprestimo"):
    livro_fmt = st.selectbox("Livro disponível", list(mapa_livro.keys()))
    data_emp = st.date_input("Data do Empréstimo", value=date.today())
    registrar = st.form_submit_button("Registrar Empréstimo")

    if registrar:
        livro_id = mapa_livro[livro_fmt]
        cursor.execute("INSERT INTO emprestimos (livro_id, data_emprestimo, devolvido) VALUES (?, ?, ?)", (livro_id, data_emp.isoformat(), 0))
        cursor.execute("UPDATE livros SET quantidade_disponivel = quantidade_disponivel - 1 WHERE id = ?", (livro_id,))
        conn.commit()
        st.success("Empréstimo registrado com sucesso!")

# --------- EDITAR AUTOR ---------
st.header("✏️ Editar autor")
autores_lista = cursor.execute("SELECT id, nome FROM autores").fetchall()
autor_opcao = st.selectbox("Selecione um autor para editar", autores_lista, format_func=lambda x: x[1])

if st.button("Carregar autor"):
    st.session_state.autor_id_para_editar = autor_opcao[0]
    st.session_state.autor_nome_atual_para_editar = autor_opcao[1]
    st.rerun()

if "autor_id_para_editar" in st.session_state:
    with st.form("form_editar_autor"):
        novo_nome = st.text_input("Novo nome do autor", value=st.session_state.autor_nome_atual_para_editar)
        salvar = st.form_submit_button("Salvar Alterações")
        if salvar:
            cursor.execute("UPDATE autores SET nome = ? WHERE id = ?", (novo_nome, st.session_state.autor_id_para_editar))
            conn.commit()
            st.success("Autor atualizado com sucesso!")
            st.rerun()

# --------- EDITAR LIVRO ---------
st.header("📕 Editar Livro")

livros_lista = cursor.execute('''
    SELECT l.id, l.titulo, a.nome, c.nome, l.quantidade_disponivel
    FROM livros l
    JOIN autores a ON l.autor_id = a.id
    JOIN categorias c ON l.categoria_id = c.id
''').fetchall()

livros_map = {f"{titulo} - {autor} - {categoria} (Qtd: {qtd})": id for id, titulo, autor, categoria, qtd in livros_lista}
livro_selecionado = st.selectbox("Selecione um livro para editar", list(livros_map.keys()))

if st.button("Carregar livro"):
    livro_id = livros_map[livro_selecionado]
    livro = cursor.execute('''
        SELECT titulo, autor_id, categoria_id, quantidade_disponivel
        FROM livros WHERE id = ?
    ''', (livro_id,)).fetchone()

    st.session_state['livro_id_para_editar'] = livro_id
    st.session_state['livro_titulo_para_editar'] = livro[0]
    st.session_state['livro_autor_id_para_editar'] = livro[1]
    st.session_state['livro_categoria_id_para_editar'] = livro[2]
    st.session_state['livro_qtd_para_editar'] = livro[3]

    # Recarrega a página pra atualizar o form com os dados do livro
    # Se não funcionar st.experimental_rerun(), peça para atualizar manualmente
    try:
        st.experimental_rerun()
    except AttributeError:
        st.warning("Atualize a página para carregar os dados do livro.")

if "livro_id_para_editar" in st.session_state:
    with st.form("form_editar_livro"):
        novo_titulo = st.text_input("Título", value=st.session_state['livro_titulo_para_editar'])

        autor_id_atual = st.session_state['livro_autor_id_para_editar']
        autor_nome_atual = cursor.execute("SELECT nome FROM autores WHERE id = ?", (autor_id_atual,)).fetchone()[0]
        novo_autor = st.selectbox("Autor", list(autores_map.keys()), index=list(autores_map.keys()).index(autor_nome_atual))

        categoria_id_atual = st.session_state['livro_categoria_id_para_editar']
        categoria_nome_atual = cursor.execute("SELECT nome FROM categorias WHERE id = ?", (categoria_id_atual,)).fetchone()[0]
        nova_categoria = st.selectbox("Categoria", list(categorias_map.keys()), index=list(categorias_map.keys()).index(categoria_nome_atual))

        nova_qtd = st.number_input("Quantidade disponível", min_value=0, value=st.session_state['livro_qtd_para_editar'], step=1)

        salvar = st.form_submit_button("Salvar alterações")

        if salvar:
            cursor.execute('''
                UPDATE livros SET titulo = ?, autor_id = ?, categoria_id = ?, quantidade_disponivel = ?
                WHERE id = ?
            ''', (novo_titulo, autores_map[novo_autor], categorias_map[nova_categoria], nova_qtd, st.session_state['livro_id_para_editar']))
            conn.commit()
            st.success("Livro atualizado com sucesso!")

            # Limpa o session_state e atualiza a página
            for chave in ['livro_id_para_editar', 'livro_titulo_para_editar', 'livro_autor_id_para_editar', 'livro_categoria_id_para_editar', 'livro_qtd_para_editar']:
                st.session_state.pop(chave, None)

            try:
                st.experimental_rerun()
            except AttributeError:
                st.warning("Atualize a página para ver as alterações.")
                

# --------- DELETAR LIVRO OU AUTOR ---------
st.header("📕 Deletar Livro")

# Busca os livros com informações para exibir no selectbox
livros_lista = cursor.execute('''
    SELECT l.id, l.titulo, a.nome, c.nome, l.quantidade_disponivel
    FROM livros l
    JOIN autores a ON l.autor_id = a.id
    JOIN categorias c ON l.categoria_id = c.id
''').fetchall()

# Mapeia texto para id do livro
livros_map = {f"{titulo} - {autor} - {categoria} (Qtd: {qtd})": id for id, titulo, autor, categoria, qtd in livros_lista}

# Selectbox para escolher o livro para deletar
livro_para_deletar = st.selectbox("Selecione um livro para deletar", list(livros_map.keys()))

if st.button("Deletar livro selecionado"):
    livro_id = livros_map[livro_para_deletar]
    
    # Confirmação extra para evitar deletar sem querer
    confirmar = st.checkbox("Confirmo que desejo deletar este livro")
    
    if confirmar:
        cursor.execute("DELETE FROM livros WHERE id = ?", (livro_id,))
        conn.commit()
        st.success(f"Livro '{livro_para_deletar}' deletado com sucesso!")
        
        # Opcional: atualiza a página para refletir a mudança
        try:
            st.experimental_rerun()
        except AttributeError:
            st.warning("Atualize a página para ver a lista atualizada.")
    else:
        st.warning("Por favor, confirme a exclusão marcando a caixa de seleção.")

conn.close()

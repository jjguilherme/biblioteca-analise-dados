import sqlite3
import pandas as pd
import os
import traceback # Importar para o traceback detalhado

# --- DEFINIÇÃO ROBUSTA DE CAMINHOS ---
# Diretório onde este script (setup_database.py) está localizado
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Diretório raiz do projeto (um nível acima da pasta 'scripts')
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Caminho para o arquivo do banco de dados na raiz do projeto
DB_NAME = os.path.join(PROJECT_ROOT, 'academia.db') # Nome do BD com caminho completo

# Caminho para a pasta 'data' na raiz do projeto
DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')
# --- FIM DA DEFINIÇÃO ROBUSTA DE CAMINHOS ---

def conectar_bd():
    """Conecta ao banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME) # Usa o DB_NAME com caminho completo
    return conn

def criar_tabelas(conn):
    """Cria as tabelas no banco de dados."""
    cursor = conn.cursor()

    # Tabela clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        telefone TEXT,
        data_nascimento DATE
    )
    """)
    print("Tabela 'clientes' criada ou já existente.")

    # Tabela instrutores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS instrutores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        especialidade TEXT
    )
    """)
    print("Tabela 'instrutores' criada ou já existente.")

    # Tabela planos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        preco_mensal REAL NOT NULL,
        duracao_meses INTEGER NOT NULL
    )
    """)
    print("Tabela 'planos' criada ou já existente.")

    # Tabela exercicios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exercicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        grupo_muscular TEXT
    )
    """)
    print("Tabela 'exercicios' criada ou já existente.")

    # Tabela treinos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS treinos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        instrutor_id INTEGER NOT NULL,
        plano_id INTEGER NOT NULL,
        data_inicio DATE NOT NULL,
        data_fim DATE,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
        FOREIGN KEY (instrutor_id) REFERENCES instrutores (id) ON DELETE SET NULL,
        FOREIGN KEY (plano_id) REFERENCES planos (id) ON DELETE RESTRICT
    )
    """)
    print("Tabela 'treinos' criada ou já existente.")

    # Tabela treino_exercicio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS treino_exercicio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        treino_id INTEGER NOT NULL,
        exercicio_id INTEGER NOT NULL,
        series INTEGER,
        repeticoes TEXT,
        FOREIGN KEY (treino_id) REFERENCES treinos (id) ON DELETE CASCADE,
        FOREIGN KEY (exercicio_id) REFERENCES exercicios (id) ON DELETE CASCADE
    )
    """)
    print("Tabela 'treino_exercicio' criada ou já existente.")

    # Tabela pagamentos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        data_pagamento DATE NOT NULL,
        valor REAL NOT NULL,
        pago BOOLEAN NOT NULL DEFAULT 0,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
    )
    """)
    print("Tabela 'pagamentos' criada ou já existente.")

    conn.commit()
    print("Criação/verificação de tabelas concluída.")


def popular_tabela_csv(conn, nome_tabela, nome_arquivo_csv):
    """Popula uma tabela com dados de um arquivo CSV."""
    caminho_csv = os.path.join(DATA_FOLDER, nome_arquivo_csv)

    print(f"\n--- Processando Tabela: {nome_tabela}, Arquivo: {nome_arquivo_csv} ---")
    print(f"Caminho absoluto do CSV sendo verificado: {os.path.abspath(caminho_csv)}")

    if not os.path.exists(caminho_csv): # Verificação inicial da existência do arquivo
        print(f"AVISO: Arquivo CSV '{os.path.abspath(caminho_csv)}' NÃO ENCONTRADO. Tabela '{nome_tabela}' não populada.")
        return
    else:
        print(f"INFO: Arquivo CSV '{os.path.abspath(caminho_csv)}' encontrado.")

    try:
        date_columns = []
        if nome_tabela == 'clientes':
            date_columns = ['data_nascimento']
        elif nome_tabela == 'pagamentos':
            date_columns = ['data_pagamento']
        
        print(f"1. Tentando ler o CSV '{caminho_csv}'...")
        df = pd.read_csv(caminho_csv, parse_dates=date_columns)

        # ---- INÍCIO DOS PRINTS DE DEPURAÇÃO ADICIONAIS (LOCAL CORRETO) ----
        print(f"DEBUG: Para o arquivo '{nome_arquivo_csv}':")
        if df.empty:
            print("DEBUG: O DataFrame (df) está VAZIO após a leitura do CSV.")
            print(f"AVISO: DataFrame vazio após ler '{caminho_csv}'. Tabela '{nome_tabela}' não será populada com dados deste arquivo.")
            return # Sair se o df estiver vazio
        else:
            print(f"DEBUG: O DataFrame (df) tem {len(df)} linhas e {len(df.columns)} colunas.")
            print("DEBUG: Primeiras 3 linhas do DataFrame (df.head(3)):")
            print(df.head(3))
            # Para uma depuração ainda mais profunda dos tipos de dados lidos pelo Pandas:
            # print("DEBUG: Informações do DataFrame (df.info()):")
            # df.info()
        # ---- FIM DOS PRINTS DE DEPURAÇÃO ADICIONAIS ----

        if nome_tabela == 'pagamentos' and 'pago' in df.columns:
            print("DEBUG: Processando coluna 'pago' para a tabela de pagamentos...")
            map_bool = {'True': 1, 'False': 0, 'sim': 1, 'nao': 0, '1': 1, '0': 0, 1: 1, 0: 0,
                        'TRUE': 1, 'FALSE': 0, 'Sim': 1, 'Nao': 0, 'SIM': 1, 'NAO': 0}
            df['pago'] = df['pago'].astype(str).map(map_bool).fillna(0).astype(int)
            print("DEBUG: Coluna 'pago' processada. df.head(3) após 'pago':")
            print(df.head(3))

        if 'id' in df.columns:
            print("DEBUG: Removendo coluna 'id' do DataFrame...")
            df = df.drop(columns=['id'])
            print(f"DEBUG: Coluna 'id' removida. df.head(3) após remover 'id':")
            print(df.head(3))

        print(f"DEBUG: Tentando inserir {len(df)} linhas na tabela SQL '{nome_tabela}'...")
        df.to_sql(nome_tabela, conn, if_exists='append', index=False)
        
        print(f"SUCESSO: Dados do arquivo '{nome_arquivo_csv}' inseridos na tabela '{nome_tabela}' com sucesso.")

    except pd.errors.EmptyDataError:
        print(f"AVISO PANDAS: O arquivo CSV '{caminho_csv}' parece estar completamente vazio (EmptyDataError). Tabela '{nome_tabela}' não populada.")
    except FileNotFoundError:
        print(f"ERRO SISTEMA: Arquivo CSV '{caminho_csv}' não encontrado (FileNotFoundError) - Isso não deveria acontecer se o check inicial os.path.exists funcionou.")
    except Exception as e:
        print(f"!!!!!!!!!! OCORREU UM ERRO DETALHADO AO PROCESSAR TABELA '{nome_tabela}' com arquivo '{nome_arquivo_csv}' !!!!!!!!!!")
        print(f"Tipo de Erro: {type(e).__name__}")
        print(f"Mensagem de Erro: {e}")
        print("Traceback completo:")
        traceback.print_exc()
        if 'df' in locals() and isinstance(df, pd.DataFrame): # Verifica se df é um DataFrame
             print("DEBUG: DataFrame no momento do erro (df.head(3)):")
             print(df.head(3))
        else:
             print("DEBUG: DataFrame (df) não foi criado ou não é um DataFrame devido a um erro anterior.")


if __name__ == '__main__':
    print(f"--- Iniciando script setup_database.py ---")
    print(f"Localização deste script (setup_database.py): {os.path.abspath(__file__)}")
    print(f"Diretório Raiz do Projeto (PROJECT_ROOT) calculado: {PROJECT_ROOT}")
    print(f"Pasta de Dados (DATA_FOLDER) calculada: {DATA_FOLDER}")
    print(f"Caminho do Banco de Dados (DB_NAME) calculado: {DB_NAME}")
    print(f"--------------------------------------------")

    conn = None
    try:
        conn = conectar_bd()
        print(f"Conectado ao banco de dados '{DB_NAME}' com sucesso.")

        criar_tabelas(conn)

        print("\nIniciando povoamento das tabelas a partir de arquivos CSV...")
        # Certifique-se de que os nomes dos arquivos CSV aqui correspondem EXATAMENTE
        # aos nomes dos arquivos na sua pasta 'data/'
        popular_tabela_csv(conn, 'clientes', 'clientes_academia.csv')
        popular_tabela_csv(conn, 'instrutores', 'instrutores.csv')
        popular_tabela_csv(conn, 'planos', 'planos.csv')
        popular_tabela_csv(conn, 'exercicios', 'exercicios.csv')
        popular_tabela_csv(conn, 'pagamentos', 'pagamentos.csv')
        
        print("\nPovoamento de tabelas concluído.")

    except sqlite3.Error as e:
        print(f"Ocorreu um erro com o SQLite: {e}")
    except Exception as e:
        print(f"Ocorreu um erro geral: {e}")
    finally:
        if conn:
            conn.close()
            print(f"\nConexão com o banco de dados '{DB_NAME}' fechada.")
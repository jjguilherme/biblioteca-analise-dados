import sqlite3

DB_NAME = 'academia.db'

def conectar_bd():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Para acessar colunas pelo nome
    return conn

def _fetch_all(query, params=None):
    """Executa uma query e retorna todos os resultados."""
    conn = conectar_bd()
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def _fetch_one(query, params=None):
    """Executa uma query e retorna um único resultado."""
    conn = conectar_bd()
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def _execute_query(query, params=None):
    """Executa uma query de modificação (INSERT, UPDATE, DELETE)."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.lastrowid # Útil para INSERTs com autoincrement
    except sqlite3.Error as e:
        print(f"Erro ao executar query: {e}")
        conn.rollback() # Desfaz alterações em caso de erro
        return None
    finally:
        conn.close()

def get_all_clients():
    """Retorna todos os clientes."""
    query = "SELECT id, nome, email, telefone, data_nascimento FROM clientes ORDER BY nome;"
    return _fetch_all(query)

def get_all_plans():
    """Retorna todos os planos."""
    query = "SELECT id, nome, preco_mensal, duracao_meses FROM planos ORDER BY nome;"
    return _fetch_all(query)

def get_all_exercises():
    """Retorna todos os exercícios."""
    query = "SELECT id, nome, grupo_muscular FROM exercicios ORDER BY nome;"
    return _fetch_all(query)

def get_pagamentos_by_client_id(cliente_id):
    """Retorna todos os pagamentos de um cliente específico."""
    query = """
        SELECT p.id, p.cliente_id, c.nome as cliente_nome, p.data_pagamento, p.valor, p.pago
        FROM pagamentos p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.cliente_id = ?
        ORDER BY p.data_pagamento DESC;
    """
    return _fetch_all(query, (cliente_id,))

def get_clients_with_current_plan_info():
    #lista todos clientes e tenta encontrar seus planos
    query = """
    SELECT
        c.id AS cliente_id,
        c.nome AS cliente_nome,
        c.email AS cliente_email,
        p.nome AS plano_nome,
        p.preco_mensal AS plano_preco,
        t.data_inicio AS treino_data_inicio,
        t.data_fim AS treino_data_fim
    FROM clientes c
    LEFT JOIN (
        SELECT 
            cliente_id, 
            plano_id, 
            data_inicio, 
            data_fim,
            ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY data_inicio DESC) as rn
        FROM treinos
    ) t ON c.id = t.cliente_id AND t.rn = 1 -- Pega o treino mais recente por cliente
    LEFT JOIN planos p ON t.plano_id = p.id
    ORDER BY c.nome;
    """
    return _fetch_all(query)

def get_workouts_with_exercises(cliente_id=None, instrutor_id=None):
    """
    Filtra e mostra treinos e seus exercícios.
    Retorna uma lista de treinos, onde cada treino contém uma lista de seus exercícios.
    """
    base_query_treinos = """
        SELECT
            t.id AS treino_id,
            t.data_inicio,
            t.data_fim,
            c.id AS cliente_id,
            c.nome AS cliente_nome,
            i.id AS instrutor_id,
            i.nome AS instrutor_nome,
            p.id AS plano_id,
            p.nome AS plano_nome
        FROM treinos t
        JOIN clientes c ON t.cliente_id = c.id
        JOIN instrutores i ON t.instrutor_id = i.id
        JOIN planos p ON t.plano_id = p.id
    """
    conditions = []
    params = []

    if cliente_id:
        conditions.append("t.cliente_id = ?")
        params.append(cliente_id)
    if instrutor_id:
        conditions.append("t.instrutor_id = ?")
        params.append(instrutor_id)
    
    if conditions:
        base_query_treinos += " WHERE " + " AND ".join(conditions)
    
    base_query_treinos += " ORDER BY t.data_inicio DESC, t.id DESC;"

    treinos = _fetch_all(base_query_treinos, tuple(params))

    query_exercicios_treino = """
        SELECT
            te.id,
            e.nome AS exercicio_nome,
            e.grupo_muscular,
            te.series,
            te.repeticoes
        FROM treino_exercicio te
        JOIN exercicios e ON te.exercicio_id = e.id
        WHERE te.treino_id = ?;
    """
    
    # Para cada treino, busca seus exercícios
    conn_exercicios = conectar_bd() # Abrir uma conexão para buscar os exercícios
    for treino in treinos:
        cursor = conn_exercicios.cursor()
        cursor.execute(query_exercicios_treino, (treino['treino_id'],))
        exercicios_do_treino = [dict(row) for row in cursor.fetchall()]
        treino['exercicios'] = exercicios_do_treino
    conn_exercicios.close() # Fechar a conexão após buscar todos os exercícios

    return treinos

def get_payment_stats_for_client(cliente_id):
    """Retorna o total de pagamentos e o último pagamento de um cliente."""
    query_total = """
        SELECT SUM(valor) as total_pago
        FROM pagamentos
        WHERE cliente_id = ? AND pago = 1;
    """
    total_pago_result = _fetch_one(query_total, (cliente_id,))
    total_pago = total_pago_result['total_pago'] if total_pago_result and total_pago_result['total_pago'] is not None else 0.0

    query_last_payment = """
        SELECT data_pagamento, valor
        FROM pagamentos
        WHERE cliente_id = ? AND pago = 1
        ORDER BY data_pagamento DESC
        LIMIT 1;
    """
    last_payment = _fetch_one(query_last_payment, (cliente_id,))

    return {
        "cliente_id": cliente_id,
        "total_pago": total_pago,
        "ultimo_pagamento_data": last_payment['data_pagamento'] if last_payment else None,
        "ultimo_pagamento_valor": last_payment['valor'] if last_payment else None
    }

def get_active_client_count_per_instructor():
    """
    Retorna quantos clientes distintos cada instrutor atende.
    Considera "ativo" se o treino não tem data_fim ou data_fim é no futuro (ajustar lógica se necessário).
    Alternativamente, pode-se contar todos os clientes que já tiveram treino com o instrutor.
    """
    # Esta query conta clientes distintos por instrutor baseado em treinos que não tem data_fim
    # ou cuja data_fim ainda não passou (considerando 'now' como data atual).
    query = """
    SELECT
        i.id AS instrutor_id,
        i.nome AS instrutor_nome,
        COUNT(DISTINCT t.cliente_id) AS numero_clientes_ativos
    FROM instrutores i
    LEFT JOIN treinos t ON i.id = t.instrutor_id 
                       AND (t.data_fim IS NULL OR t.data_fim >= date('now'))
    GROUP BY i.id, i.nome
    ORDER BY numero_clientes_ativos DESC, i.nome;
    """
    # Se quiser contar todos os clientes, independentemente de o treino ser "ativo":
    # query = """
    # SELECT
    #     i.id AS instrutor_id,
    #     i.nome AS instrutor_nome,
    #     COUNT(DISTINCT t.cliente_id) AS numero_clientes
    # FROM instrutores i
    # LEFT JOIN treinos t ON i.id = t.instrutor_id
    # GROUP BY i.id, i.nome
    # ORDER BY numero_clientes DESC, i.nome;
    # """
    return _fetch_all(query)


if __name__ == '__main__':
    # Testes rápidos (descomente para testar individualmente após popular o banco)
    print("Executando testes do database.py...")

    print("\n--- Testando get_all_clients() ---")
    todos_os_clientes = get_all_clients()
    for cliente in todos_os_clientes:
        print(cliente)
    else:
        print("Nenhum cliente encontrado ou a tabela está vazia.")
    
   # print("\nTodos os Planos:")
    #print(get_all_plans())

    # print("\nTodos os Instrutores:")
    # print(get_all_instructors())

    # print("\nTodos os Exercícios:")
    # print(get_all_exercises())

    print("\nPagamentos do cliente 1:")
    #print(get_pagamentos_by_client_id(1))

    #print("\nClientes com info de plano atual:")
    #print(get_clients_with_current_plan_info())
    
    print("\nTreinos e exercícios (todos):")
    # treinos_todos = get_workouts_with_exercises()
    # for treino in treinos_todos:
    #     print(f"Treino ID: {treino['treino_id']}, Cliente: {treino['cliente_nome']}")
    #     for ex in treino['exercicios']:
    #         print(f"  - {ex['exercicio_nome']} ({ex['series']}x{ex['repeticoes']})")

    # print("\nTreinos e exercícios (cliente ID 1):")
    # treinos_cliente1 = get_workouts_with_exercises(cliente_id=1)
    # for treino in treinos_cliente1:
    #     print(f"Treino ID: {treino['treino_id']}, Cliente: {treino['cliente_nome']}")
    #     for ex in treino['exercicios']:
    #         print(f"  - {ex['exercicio_nome']} ({ex['series']}x{ex['repeticoes']})")


    # print("\nEstatísticas de pagamento para cliente 1:")
    # print(get_payment_stats_for_client(1))

    # print("\nContagem de clientes ativos por instrutor:")
    # print(get_active_client_count_per_instructor())
    
    print("\nTestes concluídos.")
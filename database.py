```
import sqlite3
import pandas as pd
from datetime import datetime
import        query = """
            SELECT 
                f.descricao,
                f.valor,
                f.vencimento,
                julianday(?) - julianday(f.vencimento) as dias_atraso
            FROM financeiro f
            WHERE f.tipo = 'Entrada'
            AND f.status_pagamento = 'Pendente'
            AND f.vencimento < ?
            ORDER BY f.vencimento ASC
        """
        # julianday é específico do SQLite. Postgres usa data - data.
        # Precisamos adaptar a query se for Postgres.
        if is_postgres():
             query = """
                SELECT 
                    f.descricao,
                    f.valor,
                    f.vencimento,
                    DATE_PART('day', ?::timestamp - f.vencimento::timestamp) as dias_atraso
                FROM financeiro f
                WHERE f.tipo = 'Entrada'
                AND f.status_pagamento = 'Pendente'
                AND f.vencimento < ?
                ORDER BY f.vencimento ASC
            """
        
        return pd.read_sql_query(prepare_query(query), conn, params=(hoje, hoje))
```
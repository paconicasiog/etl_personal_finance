import logging

import pandas as pd
from google.cloud import bigquery

from acceso.bq_client import execute_query, get_bigquery_client

logger = logging.getLogger(__name__)

# Definición de consultas SQL fuente
SQL_QUERIES = {
    "budget_movements": "SELECT * FROM `fincasio_v2.budget_movements`",
    "budget_payments": "SELECT * FROM `fincasio_v2.budget_payments`",
    "categories": "SELECT * FROM `fincasio_v2.categories`",
    "subcategories": "SELECT * FROM `fincasio_v2.subcategories`",
    "payment_methods": "SELECT * FROM `fincasio_v2.payment_methods`",
}

def extract_raw_tables(
    client: bigquery.Client | None = None,
    key_path: str | None = None
) -> dict[str, pd.DataFrame]:
    """
    Ejecuta las consultas SQL hacia BigQuery y retorna un diccionario
    con los DataFrames crudos de cada tabla.
    """
    if client is None:
        client = get_bigquery_client(key_path=key_path)

    raw_tables: dict[str, pd.DataFrame] = {}

    for table_name, query in SQL_QUERIES.items():
        logger.debug(f"Extrayendo tabla '{table_name}'...")
        df = execute_query(query, client=client)
        raw_tables[table_name] = df
        logger.debug(f"Tabla '{table_name}' extraída ({df.shape[0]} filas).")

    return raw_tables

import logging

from google.cloud import bigquery
import pandas as pd

from acceso.bq_client import get_bigquery_client

logger = logging.getLogger(__name__)

# Mapeo de DataFrames a nombres de tablas en BigQuery
DEFAULT_TABLE_MAPPING = {
    "movements": "ft_budget_movements",
    "payments": "ft_budget_payments",
    "subcategories": "dim_budget_subcategories",
}

DEFAULT_DATASET_ID = "finance_silver_layer"


def load_dataframe_to_table(
    df: pd.DataFrame,
    table_name: str,
    client: bigquery.Client,
    dataset_id: str = DEFAULT_DATASET_ID,
    write_disposition: str = "WRITE_TRUNCATE"
) -> bigquery.job.LoadJob:
    """
    Sube un DataFrame a una tabla específica en BigQuery.
    """
    full_table_id = f"{client.project}.{dataset_id}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        autodetect=True
    )

    logger.debug(f"Iniciando carga a BigQuery: {full_table_id} ({df.shape[0]} registros)...")
    job = client.load_table_from_dataframe(df, full_table_id, job_config=job_config)
    job.result()  # Espera a que termine la carga
    logger.debug(f"Carga finalizada con éxito para: {full_table_id}")
    return job


def load_dataframes_to_bigquery(
    df_movements: pd.DataFrame,
    df_payments: pd.DataFrame,
    df_subcategories: pd.DataFrame,
    client: bigquery.Client | None = None,
    dataset_id: str = DEFAULT_DATASET_ID,
    write_disposition: str = "WRITE_TRUNCATE",
    key_path: str | None = None
) -> dict[str, str]:
    """
    Sube los tres DataFrames transformados a BigQuery en el dataset especificado:
      - df_movements     -> ft_budget_movements
      - df_payments      -> ft_budget_payments
      - df_subcategories -> dim_budget_subcategories

    Args:
        df_movements: DataFrame de movimientos presupuestados.
        df_payments: DataFrame del calendario de pagos (1:N).
        df_subcategories: DataFrame del catálogo de subcategorías con categorías.
        client: Cliente de BigQuery opcional.
        dataset_id: Nombre del dataset destino (por defecto 'finance_silver_layer').
        write_disposition: 'WRITE_TRUNCATE' para sobreescribir o 'WRITE_APPEND' para agregar.
        key_path: Ruta opcional a service_account.json.

    Returns:
        dict[str, str]: Mapeo de tabla destino y estado de carga.
    """
    if client is None:
        client = get_bigquery_client(key_path=key_path)

    # Asegurar que el dataset existe
    dataset_ref = f"{client.project}.{dataset_id}"
    client.create_dataset(bigquery.Dataset(dataset_ref), exists_ok=True)

    tables_to_upload = [
        ("ft_budget_movements", df_movements),
        ("ft_budget_payments", df_payments),
        ("dim_budget_subcategories", df_subcategories),
    ]

    results = {}
    for idx, (tbl_name, df) in enumerate(tables_to_upload, start=1):
        logger.info(f"[{idx}/3] Cargando '{tbl_name}' a {dataset_id} ({df.shape[0]} registros)...")
        load_dataframe_to_table(
            df=df,
            table_name=tbl_name,
            client=client,
            dataset_id=dataset_id,
            write_disposition=write_disposition
        )
        results[tbl_name] = f"{client.project}.{dataset_id}.{tbl_name}"

    logger.info(f"✓ Carga completa: 3 tablas actualizadas en dataset '{dataset_id}'.")
    return results

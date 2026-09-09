#!/usr/bin/env python3
"""
ETL Personal Finance Pipeline
Orquestador principal que extrae datos de BigQuery (respaldados por Google Sheets),
aplica transformaciones y unificaciones de datos, y carga a BigQuery (Silver Layer):
1. movements     -> `finance_silver_layer.ft_budget_movements`
2. payments      -> `finance_silver_layer.ft_budget_payments`
3. subcategories -> `finance_silver_layer.dim_budget_subcategories`
"""
import logging
import sys

import pandas as pd

from acceso.bq_client import get_bigquery_client
from apps.extractor import extract_raw_tables
from apps.loader import load_dataframes_to_bigquery
from apps.transformer import transform_budget_data

# Configuración de logging limpio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_PersonalFinance")


def run_pipeline(
    upload_to_bq: bool = True,
    dataset_id: str = "finance_silver_layer",
    key_path: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str] | None]:
    """
    Ejecuta el pipeline completo de ETL:
      1. Conexión a BigQuery / Google Sheets
      2. Extracción de tablas fuente
      3. Transformación y unificación
      4. Carga a BigQuery (dataset Silver Layer) si upload_to_bq=True

    Args:
        upload_to_bq: Si es True, sube las tablas a BigQuery.
        dataset_id: Nombre del dataset destino en BigQuery.
        key_path: Ruta opcional al archivo service_account.json.

    Returns:
        tuple: (df_movements, df_payments, df_subcategories, uploaded_tables)
    """
    logger.info("Iniciando Pipeline ETL de Presupuesto Personal...")

    # Etapa 1: Autenticación y Conexión
    logger.info("[1/4] Conectando con BigQuery / Google Sheets...")
    bq_client = get_bigquery_client(key_path=key_path)

    # Etapa 2: Extracción
    logger.info("[2/4] Extrayendo tablas fuente desde BigQuery...")
    raw_tables = extract_raw_tables(client=bq_client)

    # Etapa 3: Transformación y Unificación
    logger.info("[3/4] Limpiando, enriqueciendo y unificando datos...")
    df_movements, df_payments, df_subcategories = transform_budget_data(raw_tables)

    # Etapa 4: Carga a BigQuery
    uploaded_tables = None
    if upload_to_bq:
        logger.info(f"[4/4] Cargando tablas a BigQuery (Dataset: '{dataset_id}')...")
        uploaded_tables = load_dataframes_to_bigquery(
            df_movements=df_movements,
            df_payments=df_payments,
            df_subcategories=df_subcategories,
            client=bq_client,
            dataset_id=dataset_id,
            write_disposition="WRITE_TRUNCATE"
        )
    else:
        logger.info("[4/4] Carga a BigQuery omitida (modo solo lectura).")

    logger.info("Pipeline completado exitosamente.")
    return df_movements, df_payments, df_subcategories, uploaded_tables


def get_budget_dataframes(
    key_path: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta la extracción y transformación retornando los DataFrames en memoria sin subir a BQ.
    Ideal para importar en Jupyter Notebooks o análisis exploratorio (EDA).
    """
    df_movements, df_payments, df_subcategories, _ = run_pipeline(
        upload_to_bq=False,
        key_path=key_path
    )
    return df_movements, df_payments, df_subcategories


def print_summary(
    df_movements: pd.DataFrame,
    df_payments: pd.DataFrame,
    df_subcategories: pd.DataFrame,
    uploaded_tables: dict[str, str] | None = None
) -> None:
    """
    Imprime un resumen visual ejecutivo del resultado de los DataFrames generados y cargados.
    """
    mov_total = df_movements['movement_amount'].sum() if 'movement_amount' in df_movements.columns else 0.0
    mov_min_date = df_movements['movement_date'].min().strftime('%Y-%m-%d') if 'movement_date' in df_movements.columns and not df_movements['movement_date'].dropna().empty else "N/A"
    mov_max_date = df_movements['movement_date'].max().strftime('%Y-%m-%d') if 'movement_date' in df_movements.columns and not df_movements['movement_date'].dropna().empty else "N/A"

    pay_total = df_payments['payment_amount'].sum() if 'payment_amount' in df_payments.columns else 0.0
    pay_min_date = df_payments['payment_date'].min().strftime('%Y-%m-%d') if 'payment_date' in df_payments.columns and not df_payments['payment_date'].dropna().empty else "N/A"
    pay_max_date = df_payments['payment_date'].max().strftime('%Y-%m-%d') if 'payment_date' in df_payments.columns and not df_payments['payment_date'].dropna().empty else "N/A"

    active_subcats = df_subcategories['subcategory_is_active'].sum() if 'subcategory_is_active' in df_subcategories.columns else len(df_subcategories)

    print("\n" + "=" * 65)
    print("        RESULTADOS DEL PROCESO ETL - BUDGET PERSONAL")
    print("=" * 65)
    print("  [1] TABLA MOVEMENTS (Movimientos Presupuestados)")
    print(f"      • Registros procesados : {df_movements.shape[0]:,}")
    print(f"      • Columnas generadas   : {df_movements.shape[1]}")
    print(f"      • Monto total          : ${mov_total:,.2f}")
    print(f"      • Periodo de fechas    : {mov_min_date} al {mov_max_date}")
    print("-" * 65)
    print("  [2] TABLA PAYMENTS (Calendario de Pagos 1:N)")
    print(f"      • Registros procesados : {df_payments.shape[0]:,}")
    print(f"      • Columnas generadas   : {df_payments.shape[1]}")
    print(f"      • Monto total          : ${pay_total:,.2f}")
    print(f"      • Periodo de pagos     : {pay_min_date} al {pay_max_date}")
    print("-" * 65)
    print("  [3] TABLA SUBCATEGORIES (Subcategorías con Categorías)")
    print(f"      • Registros procesados : {df_subcategories.shape[0]:,}")
    print(f"      • Columnas generadas   : {df_subcategories.shape[1]}")
    print(f"      • Subcategorías activas: {active_subcats}")

    if uploaded_tables:
        print("=" * 65)
        print("  ✓ Tablas actualizadas en BigQuery (Silver Layer):")
        for tbl_name, full_path in uploaded_tables.items():
            print(f"      • {tbl_name:<25} ──► `{full_path}`")

    print("=" * 65 + "\n")


def main():
    try:
        df_movements, df_payments, df_subcategories, uploaded_tables = run_pipeline(upload_to_bq=True)
        print_summary(df_movements, df_payments, df_subcategories, uploaded_tables)
    except Exception:
        logger.exception("Error durante la ejecución del pipeline")
        sys.exit(1)


if __name__ == "__main__":
    main()

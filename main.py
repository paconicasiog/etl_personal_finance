#!/usr/bin/env python3
"""
ETL Personal Finance Pipeline
Orquestador principal que extrae datos de BigQuery (respaldados por Google Sheets),
aplica transformaciones y unificaciones de datos, y genera los DataFrames:
1. movements: Movimientos presupuestados enriquecidos con categorías y métodos de pago.
2. payments: Calendario de pagos (relación 1:N) enriquecido con el contexto completo del movimiento.
"""
import sys
import logging
from typing import Tuple, Optional
import pandas as pd

from acceso.bq_client import get_bigquery_client
from apps.extractor import extract_raw_tables
from apps.transformer import transform_budget_data

# Configuración de logging limpio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_PersonalFinance")


def get_budget_dataframes(
    key_path: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta el pipeline completo de ETL y retorna la tupla de DataFrames (movements, payments).

    Args:
        key_path: Ruta opcional al archivo service_account.json.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (df_movements, df_payments)
    """
    logger.info("Iniciando Pipeline ETL...")

    # Etapa 1: Autenticación y Conexión
    logger.info("[1/3] Conectando con BigQuery / Google Sheets...")
    bq_client = get_bigquery_client(key_path=key_path)

    # Etapa 2: Extracción
    logger.info("[2/3] Extrayendo tablas fuente desde BigQuery...")
    raw_tables = extract_raw_tables(client=bq_client)

    # Etapa 3: Transformación y Unificación
    logger.info("[3/3] Limpiando, enriqueciendo y unificando datos...")
    df_movements, df_payments = transform_budget_data(raw_tables)

    logger.info("Pipeline completado exitosamente.")
    return df_movements, df_payments


def print_summary(df_movements: pd.DataFrame, df_payments: pd.DataFrame) -> None:
    """
    Imprime un resumen visual ejecutivo del resultado de los DataFrames generados.
    """
    mov_total = df_movements['movement_amount'].sum() if 'movement_amount' in df_movements.columns else 0.0
    mov_min_date = df_movements['movement_date'].min().strftime('%Y-%m-%d') if 'movement_date' in df_movements.columns and not df_movements['movement_date'].dropna().empty else "N/A"
    mov_max_date = df_movements['movement_date'].max().strftime('%Y-%m-%d') if 'movement_date' in df_movements.columns and not df_movements['movement_date'].dropna().empty else "N/A"

    pay_total = df_payments['payment_amount'].sum() if 'payment_amount' in df_payments.columns else 0.0
    pay_min_date = df_payments['payment_date'].min().strftime('%Y-%m-%d') if 'payment_date' in df_payments.columns and not df_payments['payment_date'].dropna().empty else "N/A"
    pay_max_date = df_payments['payment_date'].max().strftime('%Y-%m-%d') if 'payment_date' in df_payments.columns and not df_payments['payment_date'].dropna().empty else "N/A"

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
    print("=" * 65)
    print("  ✓ DataFrames listos en memoria para análisis exploratorio (EDA).\n")


def main():
    try:
        df_movements, df_payments = get_budget_dataframes()
        print_summary(df_movements, df_payments)
    except Exception as e:
        logger.error(f"Error durante la ejecución del pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

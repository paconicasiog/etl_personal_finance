#!/usr/bin/env python3
"""
Script para ejecutar el pipeline ETL y cargar los DataFrames resultantes a BigQuery:
  - df_movements     -> `finance_silver_layer.ft_budget_movements`
  - df_payments      -> `finance_silver_layer.ft_budget_payments`
  - df_subcategories -> `finance_silver_layer.dim_budget_subcategories`
"""
import sys
import logging
from main import get_budget_dataframes
from apps.loader import load_dataframes_to_bigquery

# Configuración de logging limpio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_Upload_Silver")


def main():
    try:
        logger.info("=== Iniciando Proceso de Extracción y Transformación ===")
        df_movements, df_payments, df_subcategories = get_budget_dataframes()

        logger.info("\n=== Iniciando Carga a BigQuery (Silver Layer) ===")
        uploaded_tables = load_dataframes_to_bigquery(
            df_movements=df_movements,
            df_payments=df_payments,
            df_subcategories=df_subcategories,
            dataset_id="finance_silver_layer",
            write_disposition="WRITE_TRUNCATE"
        )

        print("\n" + "=" * 65)
        print("   RESUMEN DE CARGA EN BIGQUERY - SILVER LAYER")
        print("=" * 65)
        print("  ✓ Tablas actualizadas exitosamente:")
        for tbl_name, full_path in uploaded_tables.items():
            print(f"      • {tbl_name:<25} ──► `{full_path}`")
        print("=" * 65 + "\n")

    except Exception as e:
        logger.error(f"Error durante la carga a BigQuery: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

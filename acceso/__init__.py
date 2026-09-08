"""
Módulo de acceso y autenticación a servicios de Google Cloud / BigQuery.
"""
from .bq_client import execute_query, get_bigquery_client

__all__ = ["execute_query", "get_bigquery_client"]

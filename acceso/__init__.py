"""
Módulo de acceso y autenticación a servicios de Google Cloud / BigQuery.
"""
from .bq_client import get_bigquery_client, execute_query

__all__ = ["get_bigquery_client", "execute_query"]

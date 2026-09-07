import os
import logging
from typing import Optional, List
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Scopes requeridos para BigQuery y tablas externas respaldadas en Google Drive / Google Sheets
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

def resolve_key_path(key_path: Optional[str] = None) -> str:
    """
    Resuelve la ruta absoluta al archivo de credenciales de Service Account.
    """
    if key_path and os.path.exists(key_path):
        return os.path.abspath(key_path)

    # Intenta buscar en el directorio actual o en la raíz del proyecto
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    candidates = [
        os.path.join(project_root, "service_account.json"),
        os.path.join(os.getcwd(), "service_account.json"),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(
        f"No se encontró el archivo 'service_account.json'. Rutas buscadas: {candidates}"
    )

def get_bigquery_client(
    key_path: Optional[str] = None,
    scopes: Optional[List[str]] = None
) -> bigquery.Client:
    """
    Crea y retorna un cliente de BigQuery autenticado con Service Account y los scopes necesarios.
    """
    path = resolve_key_path(key_path)
    target_scopes = scopes or DEFAULT_SCOPES

    logger.debug(f"Cargando credenciales de Service Account desde: {path}")
    credentials = service_account.Credentials.from_service_account_file(
        path,
        scopes=target_scopes
    )

    client = bigquery.Client(
        credentials=credentials,
        project=credentials.project_id
    )
    return client

def execute_query(
    query: str,
    client: Optional[bigquery.Client] = None,
    key_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Ejecuta una consulta SQL en BigQuery y retorna el resultado como un DataFrame de Pandas.
    """
    if client is None:
        client = get_bigquery_client(key_path=key_path)

    logger.debug(f"Ejecutando SQL en BigQuery: {query.strip()}")
    query_job = client.query(query)
    df = query_job.to_dataframe()
    return df

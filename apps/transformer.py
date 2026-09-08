import logging
from typing import Dict, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def clean_categories(df_categories: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla de categorías, filtrando filas vacías de Google Sheets.
    """
    df = df_categories.copy()
    # Filtrar registros nulos o vacíos
    df = df[df["id"].notna() & (df["id"].astype(str).str.strip() != "") & (df["id"].astype(str).str.strip().str.lower() != "none")].copy()
    df["id"] = df["id"].astype(str).str.strip()

    rename_cols = {
        "id": "category_id",
        "name": "category_name",
        "type": "category_type",
        "is_active": "category_is_active"
    }
    df = df.rename(columns={col: rename_cols[col] for col in df.columns if col in rename_cols})
    return df

def clean_subcategories(df_subcategories: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla de subcategorías, filtrando filas vacías de Google Sheets.
    """
    df = df_subcategories.copy()
    # Filtrar registros nulos o vacíos
    df = df[df["id"].notna() & (df["id"].astype(str).str.strip() != "") & (df["id"].astype(str).str.strip().str.lower() != "none")].copy()
    df["id"] = df["id"].astype(str).str.strip()
    if "category_id" in df.columns:
        df["category_id"] = df["category_id"].astype(str).str.strip()

    rename_cols = {
        "id": "subcategory_id",
        "name": "subcategory_name",
        "descripcion": "subcategory_description",
        "is_active": "subcategory_is_active"
    }
    df = df.rename(columns={col: rename_cols[col] for col in df.columns if col in rename_cols})
    return df

def clean_payment_methods(df_pm: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla de métodos de pago, filtrando filas vacías de Google Sheets.
    """
    df = df_pm.copy()
    # Filtrar registros nulos o vacíos
    df = df[df["id"].notna() & (df["id"].astype(str).str.strip() != "") & (df["id"].astype(str).str.strip().str.lower() != "none")].copy()
    df["id"] = df["id"].astype(str).str.strip()

    rename_cols = {
        "id": "payment_method_id",
        "name": "payment_method_name",
        "same_date": "payment_method_type",
        "status": "payment_method_is_active"
    }
    df = df.rename(columns={col: rename_cols[col] for col in df.columns if col in rename_cols})

    for col in ["day_period_cut", "payment_day"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def create_movements_df(
    df_raw_movements: pd.DataFrame,
    df_categories: pd.DataFrame,
    df_subcategories: pd.DataFrame,
    df_payment_methods: pd.DataFrame
) -> pd.DataFrame:
    """
    Transforma y unifica los movimientos presupuestados con sus dimensiones
    (categorías, subcategorías y métodos de pago).
    """
    logger.debug("Transformando tabla de movimientos presupuestados (movements)...")
    mov = df_raw_movements.copy()

    # Filtrar filas vacías de Google Sheets
    mov = mov[mov["id"].notna() & (mov["id"].astype(str).str.strip() != "") & (mov["id"].astype(str).str.strip().str.lower() != "none")].copy()

    # Estandarización de identificadores para joins
    mov["id"] = mov["id"].astype(str).str.strip()
    mov["category_id"] = mov["category_id"].astype(str).str.strip()
    mov["subcategory_id"] = mov["subcategory_id"].astype(str).str.strip()
    mov["payment_method_uid"] = mov["payment_method_uid"].astype(str).str.strip()

    # Formateo de tipos de datos
    mov["amount"] = pd.to_numeric(mov["amount"], errors="coerce").fillna(0.0)
    mov["installments"] = pd.to_numeric(mov["installments"], errors="coerce").fillna(1).astype(int)
    mov["movement_date"] = pd.to_datetime(mov["budget_movement_date"], errors="coerce")

    # Preparar dimensiones limpias
    cat_clean = clean_categories(df_categories)
    subcat_clean = clean_subcategories(df_subcategories)
    pm_clean = clean_payment_methods(df_payment_methods)

    # Merges
    # 1. Merge con Categories
    mov = mov.merge(
        cat_clean[["category_id", "category_name"]],
        on="category_id",
        how="left"
    )

    # 2. Merge con Subcategories
    mov = mov.merge(
        subcat_clean[["subcategory_id", "subcategory_name"]],
        on="subcategory_id",
        how="left"
    )

    # 3. Merge con Payment Methods
    mov = mov.merge(
        pm_clean[["payment_method_id", "payment_method_name"]],
        left_on="payment_method_uid",
        right_on="payment_method_id",
        how="left"
    )

    # Renombrar y seleccionar columnas ordenadas
    mov = mov.rename(columns={
        "id": "movement_id",
        "type": "movement_type",
        "movement_description": "movement_description",
        "amount": "movement_amount"
    })

    cols_order = [
        "movement_id",
        "movement_type",
        "movement_date",
        "movement_description",
        "movement_amount",
        "installments",
        "category_id",
        "category_name",
        "subcategory_id",
        "subcategory_name",
        "payment_method_id",
        "payment_method_name"
    ]

    existing_cols = [c for c in cols_order if c in mov.columns]
    df_result = mov[existing_cols].copy()
    logger.debug(f"Tabla 'movements' creada: {df_result.shape[0]} filas, {df_result.shape[1]} columnas.")
    return df_result

def create_payments_df(
    df_raw_payments: pd.DataFrame,
    df_movements: pd.DataFrame
) -> pd.DataFrame:
    """
    Transforma y unifica el calendario de pagos (payments) con la información enriquecida
    del movimiento presupuestado origen (relación 1:N).
    """
    logger.debug("Transformando tabla de calendario de pagos (payments)...")
    pay = df_raw_payments.copy()

    # Filtrar filas vacías de Google Sheets
    pay = pay[pay["id"].notna() & (pay["id"].astype(str).str.strip() != "") & (pay["id"].astype(str).str.strip().str.lower() != "none")].copy()

    # Estandarización de identificadores
    pay["id"] = pay["id"].astype(str).str.strip()
    pay["budget_movement_id"] = pay["budget_movement_id"].astype(str).str.strip()

    # Formateo de tipos de datos
    pay["payment_amount"] = pd.to_numeric(pay["amount"], errors="coerce").fillna(0.0)
    pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")

    pay = pay.rename(columns={
        "id": "payment_id",
        "description": "payment_description"
    })

    # Merge con la tabla de movimientos
    mov_cols_to_merge = [
        "movement_id",
        "movement_type",
        "movement_date",
        "category_id",
        "category_name",
        "subcategory_id",
        "subcategory_name",
        "payment_method_id",
        "payment_method_name"
    ]
    mov_cols_present = [c for c in mov_cols_to_merge if c in df_movements.columns]

    df_merged = pay.merge(
        df_movements[mov_cols_present],
        left_on="budget_movement_id",
        right_on="movement_id",
        how="left"
    )

    # Ordenamiento lógico de columnas
    cols_order = [
        "payment_id",
        "budget_movement_id",
        "payment_date",
        "payment_amount",
        "payment_description",
        "movement_type",
        "movement_date",
        "category_id",
        "category_name",
        "subcategory_id",
        "subcategory_name",
        "payment_method_id",
        "payment_method_name"
    ]

    existing_cols = [c for c in cols_order if c in df_merged.columns]
    df_result = df_merged[existing_cols].copy()

    # Ordenar por fecha de pago y movimiento
    if "payment_date" in df_result.columns:
        df_result = df_result.sort_values(by=["payment_date", "budget_movement_id"]).reset_index(drop=True)

    logger.debug(f"Tabla 'payments' creada: {df_result.shape[0]} filas, {df_result.shape[1]} columnas.")
    return df_result

def create_subcategories_df(
    df_raw_subcategories: pd.DataFrame,
    df_raw_categories: pd.DataFrame
) -> pd.DataFrame:
    """
    Transforma y unifica las subcategorías con la información de sus categorías correspondientes.
    """
    logger.debug("Transformando tabla de subcategorías con categorías...")
    subcat_clean = clean_subcategories(df_raw_subcategories)
    cat_clean = clean_categories(df_raw_categories)

    df_merged = subcat_clean.merge(
        cat_clean,
        on="category_id",
        how="left"
    )

    cols_order = [
        "subcategory_id",
        "subcategory_name",
        "subcategory_description",
        "subcategory_is_active",
        "category_id",
        "category_name",
        "category_type",
        "category_is_active"
    ]
    existing_cols = [c for c in cols_order if c in df_merged.columns]
    remaining_cols = [c for c in df_merged.columns if c not in existing_cols]

    df_result = df_merged[existing_cols + remaining_cols].copy()
    
    # Ordenar por categoría y subcategoría
    if "category_id" in df_result.columns and "subcategory_id" in df_result.columns:
        df_result = df_result.sort_values(by=["category_id", "subcategory_id"]).reset_index(drop=True)

    logger.debug(f"Tabla 'subcategories' creada: {df_result.shape[0]} filas, {df_result.shape[1]} columnas.")
    return df_result

def transform_budget_data(raw_tables: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Función orquestadora de transformación.
    Recibe el diccionario de tablas crudas y retorna la tupla:
    (df_movements, df_payments, df_subcategories)
    """
    df_movements = create_movements_df(
        df_raw_movements=raw_tables["budget_movements"],
        df_categories=raw_tables["categories"],
        df_subcategories=raw_tables["subcategories"],
        df_payment_methods=raw_tables["payment_methods"]
    )

    df_payments = create_payments_df(
        df_raw_payments=raw_tables["budget_payments"],
        df_movements=df_movements
    )

    df_subcategories = create_subcategories_df(
        df_raw_subcategories=raw_tables["subcategories"],
        df_raw_categories=raw_tables["categories"]
    )

    return df_movements, df_payments, df_subcategories

import unittest
import pandas as pd

from apps.transformer import (
    transform_budget_data,
    create_movements_df,
    create_payments_df,
    create_subcategories_df
)
from apps.extractor import SQL_QUERIES


class TestBudgetPipelineTransformations(unittest.TestCase):
    """
    Pruebas unitarias para validar las transformaciones, selección de columnas
    y la relación 1:N utilizando datos simulados.
    """

    def setUp(self):
        # Mock dataset
        self.mock_categories = pd.DataFrame([
            {"id": "1", "type": "Ingreso", "name": "Trabajo", "is_active": True},
            {"id": "2", "type": "Gasto", "name": "Vivienda", "is_active": True},
        ])

        self.mock_subcategories = pd.DataFrame([
            {"id": "1", "category_id": "1", "name": "Salario", "descripcion": "Salario fijo", "is_active": True},
            {"id": "2", "category_id": "2", "name": "Renta", "descripcion": "Pago mensual", "is_active": True},
        ])

        self.mock_payment_methods = pd.DataFrame([
            {"id": "1", "name": "HSBC Debito", "same_date": "debit", "status": True, "day_period_cut": 1, "payment_day": 1},
            {"id": "2", "name": "HSBC 2Now", "same_date": "credit", "status": True, "day_period_cut": 11, "payment_day": 19},
        ])

        # 1 movimiento de 1 cuota (salario) y 1 movimiento de 3 cuotas (compra a meses)
        self.mock_movements = pd.DataFrame([
            {
                "id": "MOV001",
                "type": "Ingreso",
                "category_id": "1",
                "subcategory_id": "1",
                "movement_description": "Salario Quincenal",
                "budget_movement_date": "2026-09-01",
                "amount": 30000.0,
                "installments": 1,
                "payment_method_uid": "1"
            },
            {
                "id": "MOV002",
                "type": "Gasto",
                "category_id": "2",
                "subcategory_id": "2",
                "movement_description": "Mueble 3 MSI",
                "budget_movement_date": "2026-09-10",
                "amount": 6000.0,
                "installments": 3,
                "payment_method_uid": "2"
            }
        ])

        self.mock_payments = pd.DataFrame([
            {"id": "PAY001", "budget_movement_id": "MOV001", "description": "Salario Sep", "payment_date": "2026-09-01", "amount": 30000.0},
            {"id": "PAY002", "budget_movement_id": "MOV002", "description": "Mueble 1/3", "payment_date": "2026-09-19", "amount": 2000.0},
            {"id": "PAY003", "budget_movement_id": "MOV002", "description": "Mueble 2/3", "payment_date": "2026-10-19", "amount": 2000.0},
            {"id": "PAY004", "budget_movement_id": "MOV002", "description": "Mueble 3/3", "payment_date": "2026-11-19", "amount": 2000.0},
        ])

        self.mock_raw_tables = {
            "budget_movements": self.mock_movements,
            "budget_payments": self.mock_payments,
            "categories": self.mock_categories,
            "subcategories": self.mock_subcategories,
            "payment_methods": self.mock_payment_methods
        }

    def test_movements_enrichment_and_columns(self):
        """Valida que movements tenga las columnas requeridas y no las eliminadas."""
        df_movements = create_movements_df(
            self.mock_movements,
            self.mock_categories,
            self.mock_subcategories,
            self.mock_payment_methods
        )
        self.assertEqual(len(df_movements), 2)

        expected_cols = [
            "movement_id", "movement_type", "movement_date", "movement_description",
            "movement_amount", "installments", "category_id", "category_name",
            "subcategory_id", "subcategory_name", "payment_method_id", "payment_method_name"
        ]
        self.assertEqual(list(df_movements.columns), expected_cols)

        # Validar que los campos eliminados no estén presentes
        excluded_cols = [
            "movement_year_month", "movement_year", "movement_month",
            "subcategory_description", "payment_method_type", "day_period_cut",
            "payment_day", "category_is_active", "subcategory_is_active", "payment_method_is_active"
        ]
        for col in excluded_cols:
            self.assertNotIn(col, df_movements.columns)

        salario_row = df_movements[df_movements["movement_id"] == "MOV001"].iloc[0]
        self.assertEqual(salario_row["category_name"], "Trabajo")
        self.assertEqual(salario_row["subcategory_name"], "Salario")
        self.assertEqual(salario_row["payment_method_name"], "HSBC Debito")
        self.assertEqual(salario_row["movement_amount"], 30000.0)

    def test_payments_enrichment_and_columns(self):
        """Valida que payments tenga las columnas requeridas y cumpla la relación 1:N."""
        df_movements = create_movements_df(
            self.mock_movements,
            self.mock_categories,
            self.mock_subcategories,
            self.mock_payment_methods
        )
        df_payments = create_payments_df(self.mock_payments, df_movements)

        self.assertEqual(len(df_payments), 4)

        expected_cols = [
            "payment_id", "budget_movement_id", "payment_date", "payment_amount",
            "payment_description", "movement_type", "movement_date",
            "category_id", "category_name", "subcategory_id", "subcategory_name",
            "payment_method_id", "payment_method_name"
        ]
        self.assertEqual(list(df_payments.columns), expected_cols)

        # Validar que los campos eliminados no estén presentes
        excluded_cols = [
            "payment_year_month", "payment_year", "payment_month",
            "movement_description", "movement_amount", "installments",
            "payment_method_type", "day_period_cut", "payment_day", "movement_year_month"
        ]
        for col in excluded_cols:
            self.assertNotIn(col, df_payments.columns)

        mueble_payments = df_payments[df_payments["budget_movement_id"] == "MOV002"]
        self.assertEqual(len(mueble_payments), 3)
        self.assertEqual(mueble_payments["payment_amount"].sum(), 6000.0)

    def test_subcategories_dataframe(self):
        """Valida que el DataFrame subcategories sea un join detallado de subcategories con categories."""
        df_subcategories = create_subcategories_df(
            self.mock_subcategories,
            self.mock_categories
        )
        self.assertEqual(len(df_subcategories), 2)

        expected_cols = [
            "subcategory_id", "subcategory_name", "subcategory_description",
            "subcategory_is_active", "category_id", "category_name",
            "category_type", "category_is_active"
        ]
        self.assertEqual(list(df_subcategories.columns), expected_cols)

        row = df_subcategories[df_subcategories["subcategory_id"] == "1"].iloc[0]
        self.assertEqual(row["subcategory_name"], "Salario")
        self.assertEqual(row["category_name"], "Trabajo")
        self.assertEqual(row["category_type"], "Ingreso")

    def test_transform_budget_data_tuple(self):
        """Valida que transform_budget_data retorne los 3 DataFrames."""
        df_movements, df_payments, df_subcategories = transform_budget_data(self.mock_raw_tables)
        self.assertEqual(len(df_movements), 2)
        self.assertEqual(len(df_payments), 4)
        self.assertEqual(len(df_subcategories), 2)

    def test_sql_queries_defined(self):
        """Valida que todas las 5 queries requeridas estén definidas."""
        expected_tables = ["budget_movements", "budget_payments", "categories", "subcategories", "payment_methods"]
        for tbl in expected_tables:
            self.assertIn(tbl, SQL_QUERIES)
            self.assertIn(tbl, SQL_QUERIES[tbl])


if __name__ == "__main__":
    unittest.main()

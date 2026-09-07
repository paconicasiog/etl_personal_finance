import unittest
import pandas as pd
import numpy as np

from apps.transformer import transform_budget_data, create_movements_df, create_payments_df
from apps.extractor import SQL_QUERIES
from main import get_budget_dataframes


class TestBudgetPipelineTransformations(unittest.TestCase):
    """
    Pruebas unitarias para validar las transformaciones y la relación 1:N
    utilizando datos simulados.
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

    def test_movements_enrichment(self):
        """Valida que los movimientos se enriquezcan correctamente con categorías y métodos."""
        df_movements = create_movements_df(
            self.mock_movements,
            self.mock_categories,
            self.mock_subcategories,
            self.mock_payment_methods
        )
        self.assertEqual(len(df_movements), 2)
        self.assertIn("category_name", df_movements.columns)
        self.assertIn("subcategory_name", df_movements.columns)
        self.assertIn("payment_method_name", df_movements.columns)
        self.assertIn("movement_year_month", df_movements.columns)

        # Validar valores unidos
        salario_row = df_movements[df_movements["movement_id"] == "MOV001"].iloc[0]
        self.assertEqual(salario_row["category_name"], "Trabajo")
        self.assertEqual(salario_row["subcategory_name"], "Salario")
        self.assertEqual(salario_row["payment_method_name"], "HSBC Debito")
        self.assertEqual(salario_row["movement_amount"], 30000.0)

    def test_payments_1_to_n_relationship(self):
        """Valida que los pagos hereden los datos del movimiento padre y se cumpla la relación 1:N."""
        df_movements, df_payments = transform_budget_data(self.mock_raw_tables)

        self.assertEqual(len(df_movements), 2)
        self.assertEqual(len(df_payments), 4)

        # Verificar que el movimiento MOV002 tenga exactamente 3 pagos asociados
        mueble_payments = df_payments[df_payments["budget_movement_id"] == "MOV002"]
        self.assertEqual(len(mueble_payments), 3)
        self.assertEqual(mueble_payments["payment_amount"].sum(), 6000.0)

        # Verificar que hereden la categoría del movimiento
        self.assertTrue((mueble_payments["category_name"] == "Vivienda").all())
        self.assertTrue((mueble_payments["payment_method_name"] == "HSBC 2Now").all())
        self.assertTrue((mueble_payments["installments"] == 3).all())

    def test_sql_queries_defined(self):
        """Valida que todas las 5 queries requeridas estén definidas."""
        expected_tables = ["budget_movements", "budget_payments", "categories", "subcategories", "payment_methods"]
        for tbl in expected_tables:
            self.assertIn(tbl, SQL_QUERIES)
            self.assertIn(tbl, SQL_QUERIES[tbl])


if __name__ == "__main__":
    unittest.main()

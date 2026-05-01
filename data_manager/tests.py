from unittest.mock import MagicMock, patch

import pandas as pd
from django.test import TestCase
from django.urls import reverse

from data_manager.forms import PostgresImportForm
from services.postgres_importer import PostgresConfig, PostgresImportError, PostgresImporter


class PostgresImporterTests(TestCase):
    def _build_connection_mock(self, rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        cursor_context = MagicMock()
        cursor_context.__enter__ = MagicMock(return_value=cursor)
        cursor_context.__exit__ = MagicMock(return_value=False)
        connection = MagicMock()
        connection.cursor.return_value = cursor_context
        connection_context = MagicMock()
        connection_context.__enter__ = MagicMock(return_value=connection)
        connection_context.__exit__ = MagicMock(return_value=False)
        return connection_context

    def test_list_scenarios_returns_joined_scenarios(self):
        config = PostgresConfig(
            host="192.168.1.10",
            port=5432,
            database="simulacion",
            user="postgres",
            password="secret",
        )
        rows = [
            {
                "id": 7,
                "nombre": "Escenario A",
                "ejecucion_id": 3,
                "fecha": "2026-05-01 10:00:00",
                "modo": "MM1",
                "total_unidades": 12,
            }
        ]
        connection_context = self._build_connection_mock(rows)

        with patch.object(PostgresImporter, "_connect", return_value=connection_context):
            scenarios = PostgresImporter.list_scenarios(config)

        self.assertEqual(scenarios, rows)

    def test_fetch_sales_dataframe_expands_weighted_categories(self):
        config = PostgresConfig(
            host="192.168.1.10",
            port=5432,
            database="simulacion",
            user="postgres",
            password="secret",
        )
        rows = [
            {"escenario": "Escenario A", "categoria": "Vendido", "unidades_promedio": 3},
            {"escenario": "Escenario A", "categoria": "No vendido", "unidades_promedio": 2},
        ]
        connection_context = self._build_connection_mock(rows)

        with patch.object(PostgresImporter, "_connect", return_value=connection_context):
            df = PostgresImporter.fetch_sales_dataframe(config, escenario_id=7)

        self.assertEqual(list(df.columns), ["escenario", "categoria"])
        self.assertEqual(len(df), 5)
        self.assertEqual(df["categoria"].value_counts().to_dict(), {"Vendido": 3, "No vendido": 2})

    def test_fetch_sales_dataframe_rejects_empty_result(self):
        config = PostgresConfig(
            host="192.168.1.10",
            port=5432,
            database="simulacion",
            user="postgres",
            password="secret",
        )
        connection_context = self._build_connection_mock([])

        with patch.object(PostgresImporter, "_connect", return_value=connection_context):
            with self.assertRaises(PostgresImportError):
                PostgresImporter.fetch_sales_dataframe(config, escenario_id=999)


class PostgresImportFormTests(TestCase):
    def test_postgres_import_form_validates_connection_fields(self):
        form = PostgresImportForm(
            data={
                "pg_host": "192.168.1.10",
                "pg_port": "5432",
                "pg_database": "simulacion",
                "pg_user": "postgres",
                "pg_password": "secret",
                "pg_escenario_id": "7",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["pg_port"], 5432)
        self.assertEqual(form.cleaned_data["pg_escenario_id"], 7)


class PostgresScenarioApiTests(TestCase):
    @patch("data_manager.views.PostgresImporter.list_scenarios")
    def test_api_lists_scenarios(self, list_scenarios):
        list_scenarios.return_value = [
            {
                "id": 7,
                "nombre": "Escenario A",
                "ejecucion_id": 3,
                "fecha": "2026-05-01 10:00:00",
                "modo": "MM1",
                "total_unidades": 12,
            }
        ]

        response = self.client.post(
            reverse("data_manager:api_postgres_scenarios"),
            data={
                "pg_host": "192.168.1.10",
                "pg_port": "5432",
                "pg_database": "simulacion",
                "pg_user": "postgres",
                "pg_password": "secret",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scenarios"][0]["nombre"], "Escenario A")

    def test_api_rejects_invalid_connection_form(self):
        response = self.client.post(reverse("data_manager:api_postgres_scenarios"), data={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())


class PostgresUploadViewTests(TestCase):
    @patch("data_manager.views.PostgresImporter.fetch_sales_dataframe")
    def test_upload_view_imports_postgres_dataframe_into_session(self, fetch_sales_dataframe):
        fetch_sales_dataframe.return_value = pd.DataFrame(
            [
                {"escenario": "Escenario A", "categoria": "Vendido"},
                {"escenario": "Escenario A", "categoria": "Vendido"},
                {"escenario": "Escenario A", "categoria": "No vendido"},
            ]
        )

        response = self.client.post(
            reverse("data_manager:upload"),
            data={
                "source": "postgres",
                "pg_host": "192.168.1.10",
                "pg_port": "5432",
                "pg_database": "simulacion",
                "pg_user": "postgres",
                "pg_password": "secret",
                "pg_escenario_id": "7",
            },
        )

        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertIn("dataframe_json", session)
        self.assertIn("columns_info", session)
        self.assertIn("preview_data", session)
        self.assertEqual(session["columns_info"]["categoria"]["type"], "categorical")
        fetch_sales_dataframe.assert_called_once()


class UploadTemplatePostgresTests(TestCase):
    def test_upload_page_contains_postgres_import_form(self):
        response = self.client.get(reverse("data_manager:upload"))

        self.assertContains(response, "Importar desde PostgreSQL")
        self.assertContains(response, 'name="source" value="postgres"')
        self.assertContains(response, 'id="pg-load-scenarios-btn"')


class PostgresAnalysisCompatibilityTests(TestCase):
    @patch("data_manager.views.PostgresImporter.fetch_sales_dataframe")
    def test_postgres_imported_data_can_be_analyzed_like_csv_data(self, fetch_sales_dataframe):
        fetch_sales_dataframe.return_value = pd.DataFrame(
            [
                {"escenario": "Escenario A", "categoria": "Vendido"},
                {"escenario": "Escenario A", "categoria": "Vendido"},
                {"escenario": "Escenario A", "categoria": "Vendido"},
                {"escenario": "Escenario A", "categoria": "No vendido"},
                {"escenario": "Escenario A", "categoria": "No vendido"},
            ]
        )
        self.client.post(
            reverse("data_manager:upload"),
            data={
                "source": "postgres",
                "pg_host": "192.168.1.10",
                "pg_port": "5432",
                "pg_database": "simulacion",
                "pg_user": "postgres",
                "pg_password": "secret",
                "pg_escenario_id": "7",
            },
        )

        categories_response = self.client.get(
            reverse("data_manager:api_column_categories"),
            data={"column": "categoria"},
        )
        self.assertEqual(categories_response.status_code, 200)
        self.assertCountEqual(categories_response.json()["categories"], ["Vendido", "No vendido"])

        analysis_response = self.client.post(
            reverse("data_manager:api_analyze_column"),
            data={"column_name": "categoria", "success_category": "Vendido"},
        )
        self.assertEqual(analysis_response.status_code, 200)
        analysis = analysis_response.json()["analysis"]
        self.assertEqual(analysis["N"], 5)
        self.assertEqual(analysis["K"], 3)
        self.assertEqual(analysis["p"], 0.6)

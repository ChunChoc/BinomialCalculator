from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class PostgresImportError(Exception):
    pass


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


class PostgresImporter:
    MAX_EXPANDED_ROWS = 100000

    @staticmethod
    def _connect(config: PostgresConfig):
        return psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.database,
            user=config.user,
            password=config.password,
            connect_timeout=5,
            row_factory=dict_row,
        )

    @staticmethod
    def list_scenarios(config: PostgresConfig) -> list[dict[str, Any]]:
        query = """
            SELECT
                er.id,
                er.nombre,
                er.ejecucion_id,
                es.fecha,
                es.modo,
                COALESCE(SUM(ve.unidades_promedio), 0) AS total_unidades
            FROM escenario_resultado er
            JOIN ejecucion_simulacion es ON es.id = er.ejecucion_id
            LEFT JOIN ventas_escenario ve ON ve.escenario_id = er.id
            GROUP BY er.id, er.nombre, er.ejecucion_id, es.fecha, es.modo
            ORDER BY es.fecha DESC, er.id DESC
        """
        try:
            with PostgresImporter._connect(config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    return list(cursor.fetchall())
        except Exception as exc:
            raise PostgresImportError(f"No se pudo conectar o listar escenarios: {exc}") from exc

    @staticmethod
    def fetch_sales_dataframe(config: PostgresConfig, escenario_id: int) -> pd.DataFrame:
        query = """
            SELECT
                er.nombre AS escenario,
                ve.categoria,
                ve.unidades_promedio
            FROM ventas_escenario ve
            JOIN escenario_resultado er ON er.id = ve.escenario_id
            WHERE ve.escenario_id = %s
            ORDER BY ve.categoria
        """
        try:
            with PostgresImporter._connect(config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, (escenario_id,))
                    rows = list(cursor.fetchall())
        except Exception as exc:
            raise PostgresImportError(f"No se pudieron importar ventas del escenario: {exc}") from exc

        if not rows:
            raise PostgresImportError("El escenario seleccionado no tiene ventas registradas")

        expanded_rows: list[dict[str, str]] = []
        for row in rows:
            categoria = str(row["categoria"])
            escenario = str(row["escenario"])
            unidades = int(row["unidades_promedio"] or 0)
            if unidades < 0:
                raise PostgresImportError("Las unidades promedio no pueden ser negativas")
            for _ in range(unidades):
                expanded_rows.append({"escenario": escenario, "categoria": categoria})

        if not expanded_rows:
            raise PostgresImportError("El escenario seleccionado tiene 0 unidades importables")

        if len(expanded_rows) > PostgresImporter.MAX_EXPANDED_ROWS:
            raise PostgresImportError(
                f"El escenario tiene {len(expanded_rows)} filas expandidas; el limite es {PostgresImporter.MAX_EXPANDED_ROWS}"
            )

        return pd.DataFrame(expanded_rows, columns=["escenario", "categoria"])

    @staticmethod
    def fetch_scenario_details(config: PostgresConfig, escenario_id: int) -> dict[str, Any]:
        query = """
            SELECT
                er.id,
                er.nombre,
                er.lambda_h,
                er.mu_h,
                er.servidores_c,
                er.rho,
                er.wq,
                er.w,
                er.lq,
                es.modo,
                es.tiempo_minutos,
                es.replicas
            FROM escenario_resultado er
            JOIN ejecucion_simulacion es ON es.id = er.ejecucion_id
            WHERE er.id = %s
        """
        try:
            with PostgresImporter._connect(config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, (escenario_id,))
                    row = cursor.fetchone()
        except Exception as exc:
            raise PostgresImportError(f"No se pudieron obtener detalles del escenario: {exc}") from exc

        if not row:
            raise PostgresImportError("Escenario no encontrado")

        return dict(row)

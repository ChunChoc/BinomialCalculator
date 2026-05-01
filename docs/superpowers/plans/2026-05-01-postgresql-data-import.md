# PostgreSQL Data Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que `Cargar Datos` importe datos desde una base PostgreSQL en red local y los use con el mismo flujo de analisis/calculo que hoy usa archivos CSV/Excel.

**Architecture:** La importacion desde PostgreSQL debe terminar guardando en sesion los mismos datos que la carga por archivo: `dataframe_json`, `columns_info` y `preview_data`. Se agregara un servicio aislado que consulta las tablas del script, transforma `ventas_escenario.categoria` + `unidades_promedio` a un `DataFrame` categorico compatible y deja intactos `get_column_categories`, `analyze_column` y el calculo automatico.

**Tech Stack:** Django, pandas, psycopg 3, unittest/mock, Django TestCase.

---

## Contexto Verificado

La carga actual esta en `data_manager/views.py:22-104`. Cuando se carga archivo valido, la vista lee un `DataFrame` con `DataProcessor.read_file()`, calcula `preview_data` y `columns_info`, y guarda todo en sesion.

Los endpoints `data_manager/views.py:107-154` consumen exclusivamente `request.session['dataframe_json']`, por lo que una importacion PostgreSQL sera compatible si produce el mismo formato de sesion.

El template `templates/data_manager/upload.html` ya muestra columnas categoricas y permite seleccionar categoria de exito. No necesita saber si los datos vinieron de CSV o PostgreSQL, salvo para mostrar el formulario nuevo y mensajes de origen.

El script PostgreSQL entregado tiene estas tablas:

```sql
CREATE TABLE IF NOT EXISTS ejecucion_simulacion (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modo VARCHAR(10),
    tiempo_minutos REAL,
    replicas INTEGER
);

CREATE TABLE IF NOT EXISTS escenario_resultado (
    id SERIAL PRIMARY KEY,
    ejecucion_id INTEGER REFERENCES ejecucion_simulacion(id) ON DELETE CASCADE,
    nombre VARCHAR(100),
    lambda_h REAL,
    mu_h REAL,
    servidores_c INTEGER,
    rho REAL,
    wq REAL,
    w REAL,
    lq REAL
);

CREATE TABLE IF NOT EXISTS ventas_escenario (
    id SERIAL PRIMARY KEY,
    escenario_id INTEGER REFERENCES escenario_resultado(id) ON DELETE CASCADE,
    categoria VARCHAR(100),
    unidades_promedio INTEGER
);
```

La calculadora actual no usa directamente `lambda_h`, `mu_h`, `rho`, `wq`, `w` o `lq` para distribuciones binomial/hipergeometrica. El dato util para el flujo actual es `ventas_escenario`: cada categoria puede convertirse en una columna categorica `categoria` repetida `unidades_promedio` veces. Asi `N = SUM(unidades_promedio)` y `K = unidades_promedio` de la categoria seleccionada como exito.

## File Structure

- Create: `services/postgres_importer.py`
  - Responsabilidad: conectar a PostgreSQL, listar escenarios disponibles y convertir ventas por escenario a `DataFrame` compatible con `DataProcessor`.
- Modify: `data_manager/forms.py`
  - Agregar `PostgresImportForm` para host, puerto, base, usuario, password y escenario.
- Modify: `data_manager/views.py`
  - Agregar import del formulario/servicio y manejar un segundo POST en `upload_view` para fuente `postgres`.
- Modify: `data_manager/urls.py`
  - Agregar endpoint JSON para probar conexion/listar escenarios.
- Modify: `templates/data_manager/upload.html`
  - Agregar panel "Importar desde PostgreSQL" en el menu `Cargar Datos` y JS para cargar escenarios.
- Modify or create: `requirements.txt`
  - Agregar dependencia `psycopg[binary]` si el proyecto empieza a documentar dependencias Python aqui.
- Modify: `data_manager/tests.py`
  - Agregar pruebas unitarias del servicio con mocks y pruebas de vista/sesion.
- Modify: `README.md`
  - Reemplazar README de Bun obsoleto por instrucciones Django y variables de conexion local.

---

### Task 1: PostgreSQL Import Service

**Files:**
- Create: `services/postgres_importer.py`
- Test: `data_manager/tests.py`

- [ ] **Step 1: Write failing tests for scenario listing and DataFrame conversion**

Append this to `data_manager/tests.py`:

```python
from unittest.mock import MagicMock, patch

import pandas as pd
from django.test import TestCase

from services.postgres_importer import PostgresConfig, PostgresImportError, PostgresImporter


class PostgresImporterTests(TestCase):
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
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("services.postgres_importer.psycopg.connect", return_value=connection):
            scenarios = PostgresImporter.list_scenarios(config)

        self.assertEqual(scenarios, rows)
        cursor.execute.assert_called_once()

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
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("services.postgres_importer.psycopg.connect", return_value=connection):
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
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("services.postgres_importer.psycopg.connect", return_value=connection):
            with self.assertRaises(PostgresImportError):
                PostgresImporter.fetch_sales_dataframe(config, escenario_id=999)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python manage.py test data_manager.tests.PostgresImporterTests -v 2
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.postgres_importer'`.

- [ ] **Step 3: Implement service**

Create `services/postgres_importer.py`:

```python
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
```

- [ ] **Step 4: Add dependency**

If `requirements.txt` does not exist, create it with:

```text
django
pandas
scipy
openpyxl
psycopg[binary]
```

If the project already has another dependency file by the time this plan is executed, add only this line to that file:

```text
psycopg[binary]
```

- [ ] **Step 5: Run service tests**

Run:

```bash
python manage.py test data_manager.tests.PostgresImporterTests -v 2
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add services/postgres_importer.py data_manager/tests.py requirements.txt
git commit -m "feat: add PostgreSQL simulation importer"
```

---

### Task 2: Forms and API Endpoint for Scenario Discovery

**Files:**
- Modify: `data_manager/forms.py`
- Modify: `data_manager/views.py`
- Modify: `data_manager/urls.py`
- Test: `data_manager/tests.py`

- [ ] **Step 1: Write failing form and API tests**

Append this to `data_manager/tests.py`:

```python
from django.urls import reverse

from data_manager.forms import PostgresImportForm


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python manage.py test data_manager.tests.PostgresImportFormTests data_manager.tests.PostgresScenarioApiTests -v 2
```

Expected: FAIL because `PostgresImportForm` and `api_postgres_scenarios` do not exist.

- [ ] **Step 3: Add form**

Append this class to `data_manager/forms.py` after `FileUploadForm`:

```python
class PostgresImportForm(forms.Form):
    pg_host = forms.CharField(
        label="Host/IP",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "Ej: 192.168.1.10"}),
        error_messages={"required": "Debe ingresar el host o IP"},
    )
    pg_port = forms.IntegerField(
        label="Puerto",
        min_value=1,
        max_value=65535,
        initial=5432,
        widget=forms.NumberInput(attrs={"class": "input-field", "placeholder": "5432"}),
        error_messages={"required": "Debe ingresar el puerto"},
    )
    pg_database = forms.CharField(
        label="Base de datos",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "Ej: simulacion"}),
        error_messages={"required": "Debe ingresar la base de datos"},
    )
    pg_user = forms.CharField(
        label="Usuario",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "Ej: postgres"}),
        error_messages={"required": "Debe ingresar el usuario"},
    )
    pg_password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "input-field", "placeholder": "Password de PostgreSQL"}),
    )
    pg_escenario_id = forms.IntegerField(
        label="Escenario",
        required=False,
        min_value=1,
        widget=forms.HiddenInput(attrs={"id": "pg-escenario-id"}),
    )
```

- [ ] **Step 4: Add view imports and helper**

Modify imports in `data_manager/views.py`:

```python
from services.postgres_importer import PostgresConfig, PostgresImporter, PostgresImportError
from .forms import (
    FileUploadForm,
    ColumnSelectionForm,
    CalculationParamsForm,
    HypergeometricManualForm,
    PostgresImportForm,
)
```

Add this helper above `upload_view`:

```python
def _postgres_config_from_form(form):
    return PostgresConfig(
        host=form.cleaned_data["pg_host"],
        port=form.cleaned_data["pg_port"],
        database=form.cleaned_data["pg_database"],
        user=form.cleaned_data["pg_user"],
        password=form.cleaned_data.get("pg_password") or "",
    )
```

- [ ] **Step 5: Add API endpoint**

Add this view to `data_manager/views.py` before `clear_session`:

```python
@require_http_methods(["POST"])
def postgres_scenarios(request):
    form = PostgresImportForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    try:
        config = _postgres_config_from_form(form)
        scenarios = PostgresImporter.list_scenarios(config)
        return JsonResponse({"scenarios": scenarios})
    except PostgresImportError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
```

Modify `data_manager/urls.py`:

```python
urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('hypergeometric/', views.hypergeometric_view, name='hypergeometric'),
    path('api/column-categories/', views.get_column_categories, name='api_column_categories'),
    path('api/analyze-column/', views.analyze_column, name='api_analyze_column'),
    path('api/postgres-scenarios/', views.postgres_scenarios, name='api_postgres_scenarios'),
    path('clear/', views.clear_session, name='clear_session'),
]
```

- [ ] **Step 6: Run tests**

Run:

```bash
python manage.py test data_manager.tests.PostgresImportFormTests data_manager.tests.PostgresScenarioApiTests -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add data_manager/forms.py data_manager/views.py data_manager/urls.py data_manager/tests.py
git commit -m "feat: expose PostgreSQL scenario lookup"
```

---

### Task 3: Import PostgreSQL Data Through Upload View

**Files:**
- Modify: `data_manager/views.py`
- Test: `data_manager/tests.py`

- [ ] **Step 1: Write failing view test**

Append this to `data_manager/tests.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python manage.py test data_manager.tests.PostgresUploadViewTests -v 2
```

Expected: FAIL because `upload_view` ignores `source=postgres`.

- [ ] **Step 3: Modify upload view initialization**

In `data_manager/views.py`, modify the start of `upload_view`:

```python
def upload_view(request):
    upload_form = FileUploadForm()
    postgres_form = PostgresImportForm()
    column_form = None
    preview_data = None
    columns_info = None
    file_loaded = False
    analysis = None
```

- [ ] **Step 4: Add PostgreSQL POST branch before the file upload branch**

In `data_manager/views.py`, insert this block before `if request.method == 'POST' and request.FILES.get('data_file'):`:

```python
    if request.method == 'POST' and request.POST.get('source') == 'postgres':
        postgres_form = PostgresImportForm(request.POST)
        if postgres_form.is_valid():
            escenario_id = postgres_form.cleaned_data.get('pg_escenario_id')
            if not escenario_id:
                messages.error(request, 'Debe seleccionar un escenario de PostgreSQL')
            else:
                try:
                    config = _postgres_config_from_form(postgres_form)
                    df = PostgresImporter.fetch_sales_dataframe(config, escenario_id)

                    preview_data = DataProcessor.get_preview_data(df)
                    columns_info = DataProcessor.get_columns_info(df)

                    request.session['dataframe_json'] = df.to_json()
                    request.session['columns_info'] = columns_info
                    request.session['preview_data'] = preview_data
                    request.session['data_source'] = 'postgres'

                    messages.success(
                        request,
                        f'Datos PostgreSQL importados: {len(df)} filas, {len(df.columns)} columnas'
                    )
                    return redirect('data_manager:upload')
                except PostgresImportError as exc:
                    messages.error(request, str(exc))
                except Exception as exc:
                    messages.error(request, f'Error inesperado al importar PostgreSQL: {exc}')
        else:
            messages.error(request, 'Revise los datos de conexion a PostgreSQL')
```

- [ ] **Step 5: Preserve source in context and clearing**

Modify the context in `upload_view`:

```python
    context = {
        'upload_form': upload_form,
        'postgres_form': postgres_form,
        'column_form': column_form,
        'preview_data': preview_data,
        'columns_info': columns_info,
        'file_loaded': file_loaded,
        'analysis': analysis,
        'data_source': request.session.get('data_source', 'file'),
        'page_title': 'Gestion de Datos',
        'active_nav': 'data_manager',
    }
```

Modify `clear_session` keys:

```python
def clear_session(request):
    keys_to_clear = ['dataframe_json', 'columns_info', 'preview_data', 'column_analysis', 'data_source']
    for key in keys_to_clear:
        if key in request.session:
            del request.session[key]
    messages.success(request, 'Datos de sesion eliminados')
    return redirect('data_manager:upload')
```

- [ ] **Step 6: Run test**

Run:

```bash
python manage.py test data_manager.tests.PostgresUploadViewTests -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add data_manager/views.py data_manager/tests.py
git commit -m "feat: import PostgreSQL data into calculator session"
```

---

### Task 4: Upload Page UI for PostgreSQL Import

**Files:**
- Modify: `templates/data_manager/upload.html`
- Test: `data_manager/tests.py`

- [ ] **Step 1: Write failing template smoke test**

Append this to `data_manager/tests.py`:

```python
class UploadTemplatePostgresTests(TestCase):
    def test_upload_page_contains_postgres_import_form(self):
        response = self.client.get(reverse("data_manager:upload"))

        self.assertContains(response, "Importar desde PostgreSQL")
        self.assertContains(response, "name=\"source\" value=\"postgres\"")
        self.assertContains(response, "id=\"pg-load-scenarios-btn\"")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python manage.py test data_manager.tests.UploadTemplatePostgresTests -v 2
```

Expected: FAIL because the template has no PostgreSQL form yet.

- [ ] **Step 3: Add PostgreSQL panel below the file upload panel**

In `templates/data_manager/upload.html`, after the closing `</div>` of the `Cargar Archivo` panel (`line 140` in the current file), insert:

```html
            <div class="animate-slide-up opacity-0 glass-panel rounded-xl p-6 glow-purple" style="animation-delay: 0.12s;">
                <h3 class="font-display text-lg font-semibold text-white mb-6 flex items-center gap-2">
                    <svg class="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7c0 1.657 3.582 3 8 3s8-1.343 8-3-3.582-3-8-3-8 1.343-8 3zm0 0v10c0 1.657 3.582 3 8 3s8-1.343 8-3V7"/>
                    </svg>
                    Importar desde PostgreSQL
                </h3>

                <form method="post" id="postgres-import-form" class="space-y-4">
                    {% csrf_token %}
                    <input type="hidden" name="source" value="postgres">
                    {{ postgres_form.pg_escenario_id }}

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Host/IP</label>
                            {{ postgres_form.pg_host }}
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Puerto</label>
                            {{ postgres_form.pg_port }}
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1">Base de datos</label>
                        {{ postgres_form.pg_database }}
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Usuario</label>
                            {{ postgres_form.pg_user }}
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Password</label>
                            {{ postgres_form.pg_password }}
                        </div>
                    </div>

                    <button type="button" id="pg-load-scenarios-btn" class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium text-violet-300 border border-violet-400/30 hover:bg-violet-500/10 transition-all duration-300">
                        Buscar escenarios
                    </button>

                    <div id="pg-scenarios-wrapper" class="hidden">
                        <label class="block text-sm font-medium text-slate-300 mb-1">Escenario</label>
                        <select id="pg-scenarios-select" class="input-field">
                            <option value="">-- Buscar escenarios primero --</option>
                        </select>
                    </div>

                    <p id="pg-import-error" class="hidden text-rose-400 text-sm"></p>

                    <button type="submit" id="pg-import-btn" class="btn-primary w-full flex items-center justify-center gap-2 opacity-50 cursor-not-allowed" disabled>
                        Importar escenario
                    </button>
                </form>
            </div>
```

- [ ] **Step 4: Add JS for scenario discovery**

In the `<script>` block, after the existing const declarations, add:

```javascript
    const pgForm = document.getElementById('postgres-import-form');
    const pgLoadScenariosBtn = document.getElementById('pg-load-scenarios-btn');
    const pgScenariosWrapper = document.getElementById('pg-scenarios-wrapper');
    const pgScenariosSelect = document.getElementById('pg-scenarios-select');
    const pgEscenarioId = document.getElementById('pg-escenario-id');
    const pgImportBtn = document.getElementById('pg-import-btn');
    const pgImportError = document.getElementById('pg-import-error');
```

Before the closing `})();`, add:

```javascript
    if (pgLoadScenariosBtn && pgForm) {
        pgLoadScenariosBtn.addEventListener('click', function() {
            pgImportError.classList.add('hidden');
            pgImportError.textContent = '';
            pgLoadScenariosBtn.disabled = true;
            pgLoadScenariosBtn.textContent = 'Buscando...';

            const formData = new FormData(pgForm);

            fetch('{% url "data_manager:api_postgres_scenarios" %}', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) {
                    throw new Error(data.error || 'No se pudieron cargar escenarios');
                }

                pgScenariosSelect.innerHTML = '<option value="">-- Seleccionar escenario --</option>';
                data.scenarios.forEach(scenario => {
                    const option = document.createElement('option');
                    option.value = scenario.id;
                    option.textContent = `${scenario.nombre} | ejecucion ${scenario.ejecucion_id} | ${scenario.total_unidades} unidades`;
                    pgScenariosSelect.appendChild(option);
                });
                pgScenariosWrapper.classList.remove('hidden');
            })
            .catch(error => {
                pgImportError.textContent = error.message;
                pgImportError.classList.remove('hidden');
            })
            .finally(() => {
                pgLoadScenariosBtn.disabled = false;
                pgLoadScenariosBtn.textContent = 'Buscar escenarios';
            });
        });
    }

    if (pgScenariosSelect && pgEscenarioId && pgImportBtn) {
        pgScenariosSelect.addEventListener('change', function() {
            pgEscenarioId.value = this.value;
            pgImportBtn.disabled = !this.value;
            pgImportBtn.classList.toggle('opacity-50', !this.value);
            pgImportBtn.classList.toggle('cursor-not-allowed', !this.value);
        });
    }
```

- [ ] **Step 5: Update user-facing text**

Change `templates/data_manager/upload.html:5` from:

```html
{% block header_subtitle %}Carga y análisis de archivos Excel/CSV{% endblock %}
```

to:

```html
{% block header_subtitle %}Carga y análisis desde Excel, CSV o PostgreSQL{% endblock %}
```

Change the empty-state copy around current lines `460-465` from:

```html
Carga un Archivo de Datos
Sube un archivo Excel (.xlsx, .xls) o CSV para analizar los datos 
y calcular distribuciones automáticamente.
```

to:

```html
Carga Datos para Analizar
Sube un archivo Excel/CSV o importa un escenario desde PostgreSQL para analizar los datos
```

- [ ] **Step 6: Run template test**

Run:

```bash
python manage.py test data_manager.tests.UploadTemplatePostgresTests -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add templates/data_manager/upload.html data_manager/tests.py
git commit -m "feat: add PostgreSQL import controls"
```

---

### Task 5: End-to-End Compatibility Verification

**Files:**
- Modify: `data_manager/tests.py`
- Modify: `README.md`

- [ ] **Step 1: Write compatibility test for imported PostgreSQL data and existing analysis endpoint**

Append this to `data_manager/tests.py`:

```python
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
```

- [ ] **Step 2: Run compatibility test**

Run:

```bash
python manage.py test data_manager.tests.PostgresAnalysisCompatibilityTests -v 2
```

Expected: PASS.

- [ ] **Step 3: Run all Django tests**

Run:

```bash
python manage.py test -v 2
```

Expected: PASS.

- [ ] **Step 4: Manually verify with a local PostgreSQL database**

On the teammate machine that hosts PostgreSQL, verify PostgreSQL accepts LAN connections:

```bash
psql -h 0.0.0.0 -p 5432 -U postgres -d simulacion -c "SELECT COUNT(*) FROM escenario_resultado;"
```

Expected: one count row, not connection refused.

On the calculator machine, run Django:

```bash
python manage.py runserver 0.0.0.0:8000
```

Then open `http://127.0.0.1:8000/datos/` or the project route that points to `data_manager:upload`, enter host/IP, port, database, user, password, click `Buscar escenarios`, select one, click `Importar escenario`, then select column `categoria` and success category.

Expected: `Datos PostgreSQL importados` message appears, preview table shows `escenario` and `categoria`, analysis returns `N`, `K`, and `p`, and `Calcular Modelo Automático` redirects to binomial or hypergeometric with valid parameters.

- [ ] **Step 5: Document setup**

Replace `README.md` contents with:

```markdown
# BinomialCalculator

Aplicacion Django para cargar datos desde Excel, CSV o PostgreSQL y calcular distribuciones binomial/hipergeometrica.

## Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar

```bash
python manage.py migrate
python manage.py runserver
```

## Importar desde PostgreSQL en red local

La computadora que tiene PostgreSQL debe permitir conexiones desde la red local en `postgresql.conf` y `pg_hba.conf`.

La calculadora necesita estos datos:

- Host/IP: IP local de la computadora con PostgreSQL, por ejemplo `192.168.1.10`.
- Puerto: normalmente `5432`.
- Base de datos: nombre donde existen `ejecucion_simulacion`, `escenario_resultado` y `ventas_escenario`.
- Usuario y password: credenciales con permiso `SELECT` sobre esas tablas.

La importacion usa `ventas_escenario.categoria` como columna categorica y `ventas_escenario.unidades_promedio` como cantidad de ocurrencias por categoria.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add data_manager/tests.py README.md
git commit -m "test: verify PostgreSQL import compatibility"
```

---

## Self-Review

Spec coverage:

- Verificar si la calculadora puede importar y usar los datos: Task 5 prueba que los datos importados desde PostgreSQL alimentan `api_column_categories` y `api_analyze_column` con `N`, `K` y `p` correctos.
- Reutilizar `Cargar Datos`: Tasks 3 y 4 agregan la importacion al mismo `upload_view` y `upload.html`.
- Consultar datos desde la computadora del companero en red local: Tasks 1, 2 y 4 agregan host/IP, puerto, base, usuario y password.
- Basarse en el script de BD: Task 1 usa explicitamente `ejecucion_simulacion`, `escenario_resultado` y `ventas_escenario` con joins y filtros por `escenario_id`.

Implementation notes:

- No se agregan modelos Django porque esta base PostgreSQL es externa y solo se consulta; usar modelos/migraciones acoplaria la app a una segunda base que no administra.
- No se guarda password en sesion. El password se usa solo en el POST actual para listar/importar.
- La transformacion expandida es compatible con el flujo actual. Si `unidades_promedio` puede ser muy grande, el limite de `100000` filas evita llenar la sesion; si necesitan datos mas grandes, el siguiente cambio deberia ser soportar columnas categoricas ponderadas sin expandirlas.

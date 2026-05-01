# BinomialCalculator

Aplicacion Django para cargar datos desde Excel, CSV o PostgreSQL y calcular distribuciones binomial/hipergeometrica.

## Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configurar PostgreSQL (opcional pero recomendado)

Copia el archivo de ejemplo y editalo con los datos de tu red:

```bash
cp .env.example .env
```

Edita `.env` con los datos de la computadora que tiene PostgreSQL:

```env
PG_HOST=192.168.1.10
PG_PORT=5432
PG_DATABASE=simulacion
PG_USER=postgres
PG_PASSWORD=tu_password_aqui
```

> **Nota:** Estos valores apareceran pre-llenados en el formulario de importacion. Siempre puedes cambiarlos directamente en el formulario sin editar el `.env`.

## Ejecutar

```bash
python manage.py migrate
python manage.py runserver
```

## Importar desde PostgreSQL en red local

1. Ve a la pagina **Cargar Datos**
2. En el panel **Importar desde PostgreSQL**, los campos apareceran pre-llenados con los valores de tu `.env` (si existe)
3. Ajusta los valores si es necesario y haz clic en **Buscar escenarios**
4. Selecciona un escenario de la lista
5. Haz clic en **Importar escenario**

La computadora que tiene PostgreSQL debe permitir conexiones desde la red local en `postgresql.conf` y `pg_hba.conf`.

La importacion usa `ventas_escenario.categoria` como columna categorica y `ventas_escenario.unidades_promedio` como cantidad de ocurrencias por categoria.

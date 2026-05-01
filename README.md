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

# ETL Personal Finance

Pipeline de extracción, transformación y unificación de datos presupuestarios personales desde Google BigQuery (tablas externas enlazadas a Google Sheets) utilizando autenticación mediante Service Account.

---

## 🎯 Objetivo

Generar dos DataFrames estructurados, limpios y listos para análisis exploratorio (EDA):
1. **`movements`**: Representa los movimientos de ingresos y gastos presupuestados, enriquecidos con sus categorías, subcategorías y métodos de pago.
2. **`payments`**: Representa el calendario de pagos (relación 1:N respecto a los movimientos, por ejemplo compras a meses o pagos en cuotas), donde cada cuota hereda el contexto completo del movimiento origen.

---

## 📁 Estructura del Proyecto

```
etl_personal_finance/
├── acceso/
│   ├── __init__.py
│   └── bq_client.py              # Gestión de credenciales y conexión con BigQuery/Google Drive
├── apps/
│   ├── __init__.py
│   ├── extractor.py              # Ejecución de queries SQL para extraer tablas fuente
│   └── transformer.py            # Limpieza, formateo de tipos y unificación (joins)
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py          # Pruebas unitarias de integridad referencial 1:N y tipos
├── main.py                       # Orquestador del pipeline y reporte ejecutivo
├── requirements.txt              # Dependencias de Python
├── service_account.json          # Llave de cuenta de servicio de Google Cloud (con permisos)
└── README.md                     # Documentación del proyecto
```

---

## ⚙️ ¿Cómo Funciona el Proceso?

El pipeline se ejecuta en 3 etapas secuenciales:

```
[1/3] Conexión BigQuery  ───►  [2/3] Extracción SQL  ───►  [3/3] Transformación & Joins  ───►  Resultados (DataFrames)
 (Service Account + Scopes)       (5 Tablas Fuente)           (movements & payments 1:N)         (Listos para EDA)
```

### 1. Conexión (`acceso/bq_client.py`)
- Carga las credenciales de `service_account.json`.
- Configura los scopes requeridos (`bigquery`, `drive`, `spreadsheets`) para consultar tablas externas vinculadas a Google Sheets sin problemas de permisos.

### 2. Extracción (`apps/extractor.py`)
Ejecuta las siguientes 5 consultas SQL en BigQuery:
- **Movimientos:** `SELECT * FROM \`fincasio_v2.budget_movements\``
- **Plan de Pagos:** `SELECT * FROM \`fincasio_v2.budget_payments\``
- **Categorías:** `SELECT * FROM \`fincasio_v2.categories\``
- **Subcategorías:** `SELECT * FROM \`fincasio_v2.subcategories\``
- **Métodos de Pago:** `SELECT * FROM \`fincasio_v2.payment_methods\``

### 3. Transformación y Unificación (`apps/transformer.py`)
- **Limpieza:** Filtra filas vacías generadas por Google Sheets (evitando productos cartesianos).
- **Tipos de Datos:** Convierte montos a numéricos (`float`), cuotas a enteros (`int`) y fechas a `datetime` con campos derivados (`year`, `month`, `year_month`).
- **Enriquecimiento `movements`:** Une movimientos con `categories`, `subcategories` y `payment_methods`.
- **Enriquecimiento `payments`:** Une cada pago con su movimiento padre para tener el contexto analítico completo en una sola tabla de pagos.

---

## 📊 Descripción de los Resultados

Al ejecutar el pipeline se obtienen dos DataFrames:

### [1] Tabla `movements` (Movimientos Presupuestados)
- **Granularidad:** 1 fila = 1 movimiento presupuestado.
- **Columnas clave:** `movement_id`, `movement_type`, `movement_date`, `movement_year_month`, `movement_description`, `movement_amount`, `installments`, `category_name`, `subcategory_name`, `subcategory_description`, `payment_method_name`, `payment_method_type`, `day_period_cut`, `payment_day`, etc.

### [2] Tabla `payments` (Calendario de Pagos 1:N)
- **Granularidad:** 1 fila = 1 pago / cuota individual.
- **Relación 1:N:** Si un movimiento es de \$6,000 a 3 cuotas, en `movements` genera 1 fila y en `payments` genera 3 filas de \$2,000 con sus respectivas fechas de vencimiento.
- **Columnas clave:** `payment_id`, `budget_movement_id`, `payment_date`, `payment_year_month`, `payment_amount`, `payment_description`, además de todas las dimensiones del movimiento asociado (`category_name`, `subcategory_name`, `payment_method_name`, etc.).

---

## 🚀 Instalación y Uso

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el pipeline desde la terminal
```bash
python3 main.py
```

**Ejemplo de salida en consola:**
```text
21:42:00 | INFO | Iniciando Pipeline ETL...
21:42:00 | INFO | [1/3] Conectando con BigQuery / Google Sheets...
21:42:01 | INFO | [2/3] Extrayendo tablas fuente desde BigQuery...
21:42:15 | INFO | [3/3] Limpiando, enriqueciendo y unificando datos...
21:42:15 | INFO | Pipeline completado exitosamente.

=================================================================
        RESULTADOS DEL PROCESO ETL - BUDGET PERSONAL
=================================================================
  [1] TABLA MOVEMENTS (Movimientos Presupuestados)
      • Registros procesados : 465
      • Columnas generadas   : 22
      • Monto total          : $2,563,120.00
      • Periodo de fechas    : 2026-07-01 al 2027-12-26
-----------------------------------------------------------------
  [2] TABLA PAYMENTS (Calendario de Pagos 1:N)
      • Registros procesados : 476
      • Columnas generadas   : 24
      • Monto total          : $2,570,670.00
      • Periodo de pagos     : 2026-07-01 al 2027-12-26
=================================================================
  ✓ DataFrames listos en memoria para análisis exploratorio (EDA).
```

### 3. Usar en un Jupyter Notebook o script de Análisis Exploratorio (EDA)
```python
from main import get_budget_dataframes

# Ejecuta el flujo y retorna los DataFrames
df_movements, df_payments = get_budget_dataframes()

# Exploración rápida
df_movements.info()
df_payments.groupby('payment_year_month')['payment_amount'].sum()
```

### 4. Ejecutar pruebas automatizadas
```bash
python3 -m unittest tests/test_pipeline.py
```

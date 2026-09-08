# ETL Personal Finance (Silver Layer Pipeline)

Pipeline integral de extracción, transformación y carga (ETL) de finanzas personales. Extrae datos de Google BigQuery respaldados por Google Sheets (dataset `fincasio_v2`), unifica y limpia las dimensiones de movimientos, pagos y subcategorías, y carga los DataFrames resultantes a la capa Silver en BigQuery (dataset `finance_silver_layer`).

---

## 🎯 Objetivo

Generar tres modelos de datos analíticos limpios y cargarlos automáticamente a BigQuery:
1. **`ft_budget_movements`** (Tabla de Hechos): Movimientos de ingresos y gastos presupuestados enriquecidos con categorías, subcategorías y métodos de pago.
2. **`ft_budget_payments`** (Tabla de Hechos): Calendario de pagos individuales en relación **1:N** con los movimientos (por ejemplo compras a meses o pagos en cuotas), donde cada pago hereda el contexto de su movimiento origen.
3. **`dim_budget_subcategories`** (Tabla de Dimensión): Catálogo detallado de subcategorías unificadas con sus respectivas categorías.

---

## 📁 Estructura del Proyecto

```
etl_personal_finance/
├── acceso/
│   ├── __init__.py
│   └── bq_client.py              # Gestión de credenciales y conexión con BigQuery/Google Drive
├── apps/
│   ├── __init__.py
│   ├── extractor.py              # Extracción de tablas fuente desde BigQuery
│   ├── transformer.py            # Limpieza, formateo de tipos y unificación de DataFrames
│   └── loader.py                 # Carga de DataFrames a BigQuery (Silver Layer)
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py          # Pruebas unitarias de integridad 1:N, tipos y columnas
├── main.py                       # Orquestador principal del pipeline (ETL + Carga a BQ)
├── upload_to_bq.py               # Script dedicado para ejecución y carga a la capa Silver
├── requirements.txt              # Dependencias de Python
├── service_account.json          # Credenciales del Service Account de Google Cloud
└── README.md                     # Documentación técnica del proyecto
```

---

## ⚙️ ¿Cómo Funciona el Proceso?

El pipeline se ejecuta en 4 etapas secuenciales:

```
[1/4] Conexión BigQuery ──► [2/4] Extracción SQL ──► [3/4] Transformación & Joins ──► [4/4] Carga Silver Layer
 (Service Account+Scopes)      (5 Tablas Fuente)         (movements, payments, subcat)     (finance_silver_layer)
```

### 1. Conexión (`acceso/bq_client.py`)
- Autentica mediante `service_account.json`.
- Configura los scopes de OAuth requeridos (`bigquery`, `drive`, `spreadsheets`) para consultar tablas externas vinculadas a Google Sheets sin errores de permisos.

### 2. Extracción (`apps/extractor.py`)
Ejecuta las siguientes consultas SQL sobre las tablas fuente en `fincasio_v2`:
- **Movimientos:** `SELECT * FROM \`fincasio_v2.budget_movements\``
- **Plan de Pagos:** `SELECT * FROM \`fincasio_v2.budget_payments\``
- **Categorías:** `SELECT * FROM \`fincasio_v2.categories\``
- **Subcategorías:** `SELECT * FROM \`fincasio_v2.subcategories\``
- **Métodos de Pago:** `SELECT * FROM \`fincasio_v2.payment_methods\``

### 3. Transformación y Unificación (`apps/transformer.py`)
- **Limpieza de Nulos:** Filtra automáticamente filas vacías procedentes de Google Sheets para evitar duplicidades o productos cartesianos.
- **Tipos de Datos:** Convierte montos a numéricos (`float`), cuotas a enteros (`int`) y fechas a `datetime`.
- **Estructuración de Tablas:**
  - `movements`: Se une con `categories`, `subcategories` y `payment_methods`.
  - `payments`: Se une con la información del movimiento padre (relación 1:N).
  - `subcategories`: Se une con el catálogo de categorías padre.

### 4. Carga a BigQuery (`apps/loader.py`)
Carga los 3 DataFrames al dataset `finance_silver_layer` con disposición `WRITE_TRUNCATE` (reemplazo de snapshot diario/ejecución):
- `df_movements` $\longrightarrow$ `finance_silver_layer.ft_budget_movements`
- `df_payments` $\longrightarrow$ `finance_silver_layer.ft_budget_payments`
- `df_subcategories` $\longrightarrow$ `finance_silver_layer.dim_budget_subcategories`

---

## 📊 Descripción de los Modelos de Datos

### [1] `ft_budget_movements` (12 columnas)
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `movement_id` | String | Identificador único del movimiento presupuestado |
| `movement_type` | String | Tipo de movimiento (ej. 'Ingreso', 'Gasto') |
| `movement_date` | Timestamp | Fecha del movimiento presupuestado |
| `movement_description` | String | Descripción del movimiento |
| `movement_amount` | Float | Monto total del movimiento |
| `installments` | Integer | Número de parcialidades/cuotas |
| `category_id` | String | Identificador de la categoría |
| `category_name` | String | Nombre de la categoría (ej. 'Trabajo', 'Tecnologia') |
| `subcategory_id` | String | Identificador de la subcategoría |
| `subcategory_name` | String | Nombre de la subcategoría |
| `payment_method_id` | String | Identificador del método de pago |
| `payment_method_name` | String | Nombre del método de pago (ej. 'HSBC Debito', 'HSBC 2Now') |

### [2] `ft_budget_payments` (13 columnas - Relación 1:N)
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `payment_id` | String | Identificador único del pago/cuota |
| `budget_movement_id` | String | Llave foránea al movimiento presupuestado origen |
| `payment_date` | Timestamp | Fecha programada del pago |
| `payment_amount` | Float | Monto específico de la cuota/pago |
| `payment_description` | String | Descripción del pago individual |
| `movement_type` | String | Tipo de movimiento heredado |
| `movement_date` | Timestamp | Fecha del movimiento presupuestado origen |
| `category_id` | String | Identificador de la categoría |
| `category_name` | String | Nombre de la categoría |
| `subcategory_id` | String | Identificador de la subcategoría |
| `subcategory_name` | String | Nombre de la subcategoría |
| `payment_method_id` | String | Identificador del método de pago |
| `payment_method_name` | String | Nombre del método de pago |

### [3] `dim_budget_subcategories` (8 columnas)
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `subcategory_id` | String | Identificador único de la subcategoría |
| `subcategory_name` | String | Nombre de la subcategoría |
| `subcategory_description` | String | Detalle/descripción de la subcategoría |
| `subcategory_is_active` | Boolean | Estado activo/inactivo de la subcategoría |
| `category_id` | String | Identificador de la categoría padre |
| `category_name` | String | Nombre de la categoría |
| `category_type` | String | Tipo de categoría (ej. 'Ingreso', 'Gasto') |
| `category_is_active` | Boolean | Estado activo/inactivo de la categoría |

---

## 🚀 Instalación y Ejecución

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el pipeline completo (ETL + Carga a BigQuery)
```bash
python3 main.py
```

**Salida en consola:**
```text
13:47:30 | INFO | Iniciando Pipeline ETL de Presupuesto Personal...
13:47:30 | INFO | [1/4] Conectando con BigQuery / Google Sheets...
13:47:30 | INFO | [2/4] Extrayendo tablas fuente desde BigQuery...
13:47:44 | INFO | [3/4] Limpiando, enriqueciendo y unificando datos...
13:47:44 | INFO | [4/4] Cargando tablas a BigQuery (Dataset: 'finance_silver_layer')...
13:47:44 | INFO | [1/3] Cargando 'ft_budget_movements' a finance_silver_layer (465 registros)...
13:47:48 | INFO | [2/3] Cargando 'ft_budget_payments' a finance_silver_layer (476 registros)...
13:47:51 | INFO | [3/3] Cargando 'dim_budget_subcategories' a finance_silver_layer (48 registros)...
13:47:54 | INFO | ✓ Carga completa: 3 tablas actualizadas en dataset 'finance_silver_layer'.
13:47:54 | INFO | Pipeline completado exitosamente.

=================================================================
        RESULTADOS DEL PROCESO ETL - BUDGET PERSONAL
=================================================================
  [1] TABLA MOVEMENTS (Movimientos Presupuestados)
      • Registros procesados : 465
      • Columnas generadas   : 12
      • Monto total          : $2,563,120.00
      • Periodo de fechas    : 2026-07-01 al 2027-12-26
-----------------------------------------------------------------
  [2] TABLA PAYMENTS (Calendario de Pagos 1:N)
      • Registros procesados : 476
      • Columnas generadas   : 13
      • Monto total          : $2,570,670.00
      • Periodo de pagos     : 2026-07-01 al 2027-12-26
-----------------------------------------------------------------
  [3] TABLA SUBCATEGORIES (Subcategorías con Categorías)
      • Registros procesados : 48
      • Columnas generadas   : 8
      • Subcategorías activas: 48
=================================================================
  ✓ Tablas actualizadas en BigQuery (Silver Layer):
      • ft_budget_movements       ──► `nicapp-467321.finance_silver_layer.ft_budget_movements`
      • ft_budget_payments        ──► `nicapp-467321.finance_silver_layer.ft_budget_payments`
      • dim_budget_subcategories  ──► `nicapp-467321.finance_silver_layer.dim_budget_subcategories`
=================================================================
```

### 3. Uso en Jupyter Notebook / Python (Modo solo lectura para EDA)
Si deseas obtener los DataFrames en memoria sin realizar la carga a BigQuery:

```python
from main import get_budget_dataframes

# Obtiene los DataFrames en memoria
df_movements, df_payments, df_subcategories = get_budget_dataframes()

# Análisis exploratorio
print(df_movements.head())
print(df_payments.head())
print(df_subcategories.head())
```

### 4. Ejecutar pruebas unitarias
```bash
python3 -m unittest tests/test_pipeline.py
```

# ETL Personal Finance

Pipeline de extracción, transformación y unificación de datos presupuestarios personales desde Google BigQuery (tablas externas enlazadas a Google Sheets) utilizando autenticación mediante Service Account.

---

## 🎯 Objetivo

Generar tres DataFrames estructurados, limpios y listos para análisis exploratorio (EDA):
1. **`movements`**: Movimientos de ingresos y gastos presupuestados, enriquecidos con sus categorías, subcategorías y métodos de pago.
2. **`payments`**: Calendario de pagos (relación 1:N respecto a los movimientos, ej. compras a meses o cuotas), donde cada pago hereda el contexto de su movimiento origen.
3. **`subcategories`**: Catálogo enriquecido resultante de la unión de subcategorías con sus categorías correspondientes.

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
│   └── transformer.py            # Limpieza, unificación y creación de los 3 DataFrames
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py          # Pruebas unitarias de integridad 1:N, tipos y columnas
├── main.py                       # Orquestador del pipeline y reporte ejecutivo
├── requirements.txt              # Dependencias de Python
├── service_account.json          # Credenciales del Service Account de Google Cloud
└── README.md                     # Documentación técnica
```

---

## ⚙️ ¿Cómo Funciona el Proceso?

El pipeline se ejecuta en 3 etapas secuenciales:

```
[1/3] Conexión BigQuery  ───►  [2/3] Extracción SQL  ───►  [3/3] Transformación & Joins  ───►  Resultados (DataFrames)
 (Service Account + Scopes)       (5 Tablas Fuente)           (movements, payments, subcat)      (Listos para EDA)
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
- **Limpieza:** Filtra filas vacías generadas automáticamente por Google Sheets.
- **Tipos de Datos:** Convierte montos a numéricos (`float`), cuotas a enteros (`int`) y fechas a `datetime`.
- **Enriquecimiento `movements`:** Une movimientos con nombres de categorías, subcategorías y métodos de pago.
- **Enriquecimiento `payments`:** Une cada pago con las dimensiones de su movimiento origen (relación 1:N).
- **Enriquecimiento `subcategories`:** Une el catálogo de subcategorías con la información y tipo de su categoría padre.

---

## 📊 Descripción de los DataFrames Generados

### [1] Tabla `movements` (Movimientos Presupuestados)
- **Granularidad:** 1 fila = 1 movimiento presupuestado.
- **Columnas:**
  - `movement_id`
  - `movement_type`
  - `movement_date`
  - `movement_description`
  - `movement_amount`
  - `installments`
  - `category_id`
  - `category_name`
  - `subcategory_id`
  - `subcategory_name`
  - `payment_method_id`
  - `payment_method_name`

### [2] Tabla `payments` (Calendario de Pagos 1:N)
- **Granularidad:** 1 fila = 1 pago / cuota individual.
- **Relación 1:N:** Si un movimiento es de \$6,000 a 3 cuotas, en `movements` genera 1 fila y en `payments` genera 3 filas de \$2,000 con sus fechas de vencimiento.
- **Columnas:**
  - `payment_id`
  - `budget_movement_id`
  - `payment_date`
  - `payment_amount`
  - `payment_description`
  - `movement_type`
  - `movement_date`
  - `category_id`
  - `category_name`
  - `subcategory_id`
  - `subcategory_name`
  - `payment_method_id`
  - `payment_method_name`

### [3] Tabla `subcategories` (Subcategorías con Categorías)
- **Granularidad:** 1 fila = 1 subcategoría.
- **Columnas:**
  - `subcategory_id`
  - `subcategory_name`
  - `subcategory_description`
  - `subcategory_is_active`
  - `category_id`
  - `category_name`
  - `category_type`
  - `category_is_active`

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

**Salida en consola:**
```text
13:20:11 | INFO | Iniciando Pipeline ETL...
13:20:11 | INFO | [1/3] Conectando con BigQuery / Google Sheets...
13:20:11 | INFO | [2/3] Extrayendo tablas fuente desde BigQuery...
13:20:26 | INFO | [3/3] Limpiando, enriqueciendo y unificando datos...
13:20:26 | INFO | Pipeline completado exitosamente.

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
  ✓ DataFrames listos en memoria para análisis exploratorio (EDA).
```

### 3. Importar en un Jupyter Notebook o script para Análisis Exploratorio (EDA)
```python
from main import get_budget_dataframes

# Obtiene los tres DataFrames limpios
df_movements, df_payments, df_subcategories = get_budget_dataframes()

# Listo para análisis exploratorio
print(df_movements.head())
print(df_payments.head())
print(df_subcategories.head())
```

### 4. Ejecutar pruebas automatizadas
```bash
python3 -m unittest tests/test_pipeline.py
```

# 🚌 TRANSURBAN SpA - Sistema de Capacity Planning & Rostering Optimization

![Python Version](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![UI](https://img.shields.io/badge/UI-Tkinter-red?logo=python)
![Status](https://img.shields.io/badge/Status-Academic%20Project-orange)
![Type](https://img.shields.io/badge/Type-Data%20Science%20%26%20Optimization-blue)
![Academic](https://img.shields.io/badge/Academic%20Project-TII%202026-purple)

> ⚠️ **Nota Importante:** Este es un proyecto académico desarrollado para el Taller de Ingeniería Industrial (TII) en abril de 2026. 
> El proyecto **NO se encuentra en desarrollo activo** en este momento, pero está disponible como referencia e inspiración para otros desarrolladores y investigadores.
> Si deseas utilizarlo o mejorarlo, siéntete libre de hacer un fork y adaptar el código a tus necesidades.

## 📋 Descripción

Aplicación integral de planificación de flota y optimización de turnos desarrollada como **proyecto del Taller de Ingeniería Industrial (TII)** en la Universidad del Desarrollo de Chile, finalizado en **abril de 2026**.

La solución importa recorridos oficiales desde archivos CSV, genera demanda por bloque horario (24/7), estima la plantilla de conductores (Full-Time y Part-Time) y ejecuta la optimización **ADMM** (Alternating Direction Method of Multipliers) mensual, cumpliendo con restricciones laborales y empresariales.

Incluy interfaz gráfica interactiva con Tkinter, métricas en tiempo real, exportación de turnos y optimización basada en la frontera de Pareto para el balance costo-servicio.

### 📌 Estado del Proyecto
- ✅ **Fase:** Completo como proyecto académico
- ⏸️ **Desarrollo:** No está en desarrollo activo en este momento
- 🤝 **Colaboraciones:** Disponible para inspiración y referencias
- 📚 **Propósito:** Referencia académica y punto de partida para futuros proyectos

---

## 👥 Autores

Este proyecto fue desarrollado por estudiantes de Ingeniería Civil Industrial:

- **Javier Becerra**
- **Diego Raquelich**
- **Valentina Morales**

**Institución:** Universidad del Desarrollo de Chile  
**Ramo:** Taller de Ingeniería Industrial (TII) - 1° Trimestre 2026

---

## 📑 Tabla de Contenidos
- [Descripción](#-descripción)
- [Autores](#-autores)
- [Características principales](#-características-principales)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso y ejecución](#-uso-y-ejecución)
- [Documentación adicional](#-documentación-adicional)
- [Licencia](#-licencia)
- [Contacto](#-contacto)

---

## ✨ Características principales

### 🎨 Interfaz gráfica (Tkinter)
- **Diseño moderno:** Paleta de colores editorial centrada en tonos rojos y arquitectónicos.
- **Flujo asíncrono:** Barra de progreso animada durante las ejecuciones utilizando *threading* para mantener la UI responsiva.
- **Pestaña de Resultados:** Análisis de la planificación y coberturas.
- **Pestaña de Cronograma:** Visualización interactiva y editorial de los recorridos con *tooltips* informativos.
- **Sección de Ejecuciones:** Logs en tiempo real con marcas de tiempo (timestamp).

### ⚙️ Motor de Optimización ADMM
- Asignación automatizada de conductores a turnos (*slots*).
- Respeto estricto a las **restricciones legales** (descansos obligatorios, fines de semana libres, etc.).
- Soporte para personal Full-Time (FT) y Part-Time (PT).
- Cálculo preciso del nivel de servicio y cobertura.
- Iteraciones parametrizables para ajustar la convergencia del algoritmo.
- **Frontera de Pareto:** Búsqueda y análisis de múltiples combinaciones FT/PT para optimizar el ratio costo-servicio.

### 💾 Importación / Exportación
- Importación directa de archivos CSV de paraderos y rutas (`Paraderos TRANSURBAN.csv`, `Rutas tiempo frecuencia TRANSURBAN.csv`).
- **Validación robusta:** Verificación *fuzzy* de valores con sugerencias en caso de inconsistencias.
- Exportación automática a formato CSV de los turnos mensuales consolidados (`ROSTER_FINAL_TRANSURBAN.csv`).
- Generación automática de demanda mensual (24/7).

---

## 📂 Estructura del proyecto

El repositorio sigue buenas prácticas de arquitectura de software para aplicaciones en Python:

```text
📁 APP
├── 📄 app_transurban.py                 # Punto de entrada y GUI principal (Tkinter)
├── 📄 adaptar_recorridos_a_demanda.py   # Módulo adaptador de rutas y frecuencias a demanda
├── 📄 generador_rostering.py            # Generación de la plantilla de conductores FT/PT
├── 📄 main_rostering_admm.py            # Motor principal de asignación (algoritmo ADMM)
├── 📄 Loader.py                         # Scripts de precarga y utilidades del sistema
├── 📄 requirements.txt                  # Dependencias del proyecto
├── 📄 diccionario_datos.md              # Diccionario con estructura y definición de datos
├── 📄 Paraderos TRANSURBAN.csv          # Dataset origen: Paraderos
├── 📄 Rutas tiempo frecuencia TRANSURBAN.csv # Dataset origen: Rutas y frecuencias
│
├── 📁 src/                              # Lógica core de la aplicación
│   ├── 📁 adapter/                      # Adaptadores y procesamiento CSV
│   │   ├── adapter.py                   # Reexportación de funciones de parsing y validación
│   │   ├── parsers.py                   # Lectura y agregación horaria
│   │   └── validators.py                # Validación fuzzy y chequeos de integridad
│   └── 📁 rostering/                    # Lógica de optimización de turnos
│       └── rostering.py                 # Clases y utilidades del ADMM
│
├── 📁 datos_rostering/                  # Outputs y datos canónicos generados (ignorados por git típicamente)
│   ├── demanda_mensual.csv              # Demanda horaria calculada
│   ├── plantilla_mensual.csv            # Plantilla de conductores disponible
│   └── ROSTER_FINAL_TRANSURBAN.csv      # Archivo final de turnos exportados
│
└── 📁 logs/                             # Archivos de registro de ejecución
    └── ejecuciones.txt                  # Registro persistente de la consola
```

---

## 🔧 Requisitos

- **Python:** Versión `3.10` o superior.
- Librerías listadas en `requirements.txt`. Principalmente:
  - `pandas` (Manejo integral de datos tabulares).

*Nota: La interfaz de usuario utiliza la librería nativa `tkinter` y ejecución asíncrona mediante `threading`, que ya vienen incluidos en la biblioteca estándar de Python.*

---

## 🚀 Instalación

### Opción 1: Clonar desde GitHub
```bash
git clone https://github.com/[tu-usuario]/transurban-capacity-planning.git
cd transurban-capacity-planning
```

### Opción 2: Instalación manual
1. Descarga los archivos del proyecto
2. Abre una terminal en la raíz del proyecto.

### Configurar el entorno
```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```
3. Se recomienda utilizar un entorno virtual (opcional pero sugerido).
4. Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

---

## 💻 Uso y ejecución

### 1. Levantar la aplicación
Para iniciar la interfaz principal de la aplicación, ejecuta el siguiente comando estando posicionado en el directorio raíz de la aplicación:

```bash
python app_transurban.py
```
*(Si lo ejecutas desde el directorio padre, puedes usar `python -m APP.app_transurban`)*

### 2. Flujo de trabajo principal
1. **Importar Paraderos:** Carga el archivo `Paraderos TRANSURBAN.csv`.
2. **Importar Rutas:** Carga el archivo de recorridos `Rutas tiempo frecuencia TRANSURBAN.csv`.
3. **Revisar estado:** Observa el panel de `Ejecuciones` para comprobar si hay advertencias de paraderos no encontrados o valores aproximados.
4. **Configurar parámetros:** En el panel lateral, ajusta:
   - Días y opciones de fin de semana.
   - Cantidad de conductores Full-Time (FT) y Part-Time (PT).
   - Cantidad de iteraciones ADMM (se recomienda al menos `5`).
5. **Ejecutar motor:** Haz clic en **"🚀 EJECUTAR MOTOR"**.
   - El motor correrá en segundo plano (verás la barra de progreso).
   - Se crearán internamente `demanda_mensual.csv` y `plantilla_mensual.csv`.
6. **Revisar y Exportar:** Al terminar, explora la pestaña de **Resultados** (métricas de déficit/cobertura) y el **Cronograma**. El sistema generará automáticamente el archivo de turnos, o bien puedes usar el botón de exportación para guardar tu resultado en `ROSTER_FINAL_TRANSURBAN.csv`.

---

## 📚 Documentación adicional

- Revisa el archivo [diccionario_datos.md](diccionario_datos.md) para entender qué significa cada columna en las salidas de las matrices y bases de datos generadas.
- **Pestaña Cronograma**: Visualización editorial de recorridos por hora y día.
  - Selecciona un día (1-28) en el selector.
  - Pasa el ratón sobre los bloques de recorrido para ver detalles.
  - Presiona sobre un bloque para abrir modal con operadores asignados.
- **Botón Métricas**: Abre modal con análisis detallado (FT/PT usados, cobertura por bloque, etc.).
- **Botón Consola**: Ver logs en tiempo real del backend.

#### Exportar turnos
- En la pestaña `Cronograma`, presiona `💾 Exportar Turnos CSV`.
- Guarda archivo con todos los 28 días, recorridos, operadores asignados y deficits.
- Formato: `.csv` compatible con Excel/spreadsheets.

#### Optimización (Pareto)
1. Presiona `🔎 Optimizar`.
2. Confirma el diálogo de múltiples corridas (puede tardar varios minutos).
3. El sistema explora combinaciones FT/PT alrededor de los valores actuales.
4. Se calcula frontera Pareto (máximo servicio por mínimo costo).
5. Modal muestra opciones óptimas → selecciona una → se aplica la plantilla y re-ejecuta motor.

### Formato esperado de CSVs

#### CSV de rutas
Debe incluir columnas detectadas automáticamente por el sistema:
- **Recorrido/Ruta** (nombre del recorrido, ej. "R1", "Ruta 100")
- **Rango horario/Horario** (ej. "6:00-22:00", "06:00 - 22:00", "6 - 22")
- **Tiempo recorrido estimado** (minutos, ej. "45")
- **Frecuencia/Headway** (minutos entre pasadas, ej. "15")
- Opcionales: `Terminal_logico`, `Origen`, `Destino`

**Ejemplo:**
```
Recorrido,Origen,Destino,Rango_horario,Tiempo_recorrido_estimado_min,Frecuencia_headway_min
R1,Terminal 1,Terminal 2,6:00-22:00,45,15
R2,Terminal 2,Terminal 3,5:00-23:00,60,20
```

#### CSV de paraderos
Debe contener columna de nombres/códigos de paraderos para validación:
- **Nombre o Código** del paradero (ej. "Paradero Central", "P001")

**Ejemplo:**
```
Codigo,Nombre
P001,Paradero Central
P002,Estación Sur
P003,Terminal Metropolitana
```

**Notas sobre validación:**
- El sistema valida que `Origen` y `Destino` (del CSV de rutas) existan en el de paraderos.
- Si hay No encontrados, sugiere las coincidencias más cercanas (fuzzy matching).
- Permite generar demanda igual con advertencias.

### Flujo de datos

1. **Import CSVs** → `adaptar_recorridos_a_demanda.aggregate_from_routes_csv` → Demanda por bloque.
2. **Generar demanda** → `adaptar_recorridos_a_demanda.generate_demanda_csv` → `datos_rost5ring/demanda_mensual.csv`.
3. **Generar plantilla** → `generador_rostering.generar_demanda_mensual_24_7` → `datos_rost5ring/plantilla_mensual.csv`.
4. **Cargar datos** → `main_rostering_admm.cargar_datos_rostering` → Slots de demanda + conductores disponibles.
5. **Ejecutar ADMM** (en hilo separado) → `main_rostering_admm.ejecutar_admm_mensual` → Asignación de turnos.
6. **Refrescar UI** → Cronograma, métricas y sección ejecuciones se actualizan sin freezes.
7. **Exportar** → `_build_export_rows` → CSV con todos los turnos asignados (28 días).

**Componentes UI en paralelo:**
- Barra de progreso animada (actualiza cada 10ms).
- Mensajes de progreso (ej. "Cargando datos...", "Ejecutando ADMM...").
- Logs en consola integrada.

### Carpeta de datos actual

#### Datos canónicos (motor)
- `datos_rost5ring/demanda_mensual.csv` — Demanda 24/7 por bloque horario (28 días).
- `datos_rost5ring/plantilla_mensual.csv` — Plantilla de conductores FT/PT generados automáticamente.
- `datos_rost5ring/.demand_source` — Marcador indicando que demanda viene de CSV oficial (activa el botón de ejecución).

#### Datos importados
- `datos/Paraderos TRANSURBAN.csv` — Paraderos descargados en el import.
- `datos/Rutas tiempo frecuencia TRANSURBAN.csv` — Rutas y cronogramas importados.
- `datos/paraderos_map.json` — Mapeos manuales para paraderos con fuzzy matching.

#### Exportados
- `{escritorio o seleccionado}/turnos_asignados.csv` — Salida de exportación de turnos (28 días con operadores).

### Notas importantes

- **Ejecución sin freezes**: El motor ADMM corre en hilo separado; la barra de progreso y UI permanecen responsivos.
- **Demanda requerida**: El motor solo se ejecuta si existe `datos_rost5ring/.demand_source` (se crea al importar CSV oficial).
- **Parámetros con efecto inmediato**: Cambiar FT/PT o iteraciones en UI se aplica en la siguiente ejecución.
- **Cronograma y métricas**: Se refrescan automáticamente tras cada ejecución ADMM.
- **Exportación mensual**: Genera CSV con todos los 28 días en una sola tanda.
- **Optimización Pareto**: Múltiples corridas ADMM pueden tardar varios minutos; se recomienda hacer en segundo plano.

### Arquitectura técnica

#### Threading y concurrencia
- `execute_planning()` → inicia `_run_planning_thread()` en segundo plano.
- `optimize_service_cost()` → inicia `_run_optimization_thread()` en segundo plano.
- `_schedule_ui()` → encolador seguro para actualizar UI desde thread de trabajo.

#### Diseño de componentes
- Paleta: Rojo primario (#af101a), Teal terciario (#005f7b), Grises arquitectónicos.

#### Motor ADMM
- **M1 (Carga)**: Lectura de demanda y plantilla de conductores.
- **M2 (Multiplicadores)**: Inicialización de lambdas (subsidios).
- **M3 (Penalización)**: Rho = 2.0 para duplicidad.
- **M4 (Asignación)**: Cada iteración busca mejorar cobertura.

### Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Botón `EJECUTAR MOTOR` deshabilitado | No se importó CSV oficial | Importa Rutas y Paraderos primero |
| Cronograma vacío después de ejecutar | No hay `route_schedule` cargado | Importa CSV de Rutas antes |
| Bajos niveles de servicio | Demanda mayor que capacidad FT/PT | Incrementa FT/PT o usa `Optimizar` |
| UI se freezea | (Raro con threading actual) | Reporta el issue |

---

## 📖 Metodología & Contribuciones Académicas

Este proyecto implementa algoritmos de **Investigación de Operaciones** en el contexto del **Problema de Planificación de Turnos** (Rostering Problem):

### Conceptos clave
- **ADMM (Alternating Direction Method of Multipliers):** Método de optimización distribuida para resolver problemas convexos con restricciones.
- **Frontera de Pareto:** Análisis multi-objetivo para encontrar soluciones que balancean costo operacional vs. calidad de servicio.
- **Restricted Master Problem:** Subproblema legal que respeta restricciones laborales.
- **Column Generation:** Generación dinámica de variables para conductores (implícitamente en la búsqueda de rutas viables).

### Paper de Inspiración
Este proyecto se inspira en la investigación de **Feng et al. (2023)** sobre la integración de crew scheduling y rostering usando ADMM en sistemas de tránsito urbano:

> Feng, T., Lusby, R. M., Zhang, Y., Peng, Q., Shang, P., & Tao, S. (2023). 
> *An ADMM-based dual decomposition mechanism for integrating crew scheduling and rostering in an urban rail transit line*. 
> Transportation Research Part C: Emerging Technologies, 149, 104081.
> https://doi.org/10.1016/j.trc.2023.104081

### Restricciones implementadas
✅ Descansos obligatorios (mínimo 11 horas entre jornadas)  
✅ Máximas horas de trabajo por conductor  
✅ Fines de semana libres (mínimo 1 libre cada 2 semanas)  
✅ Balance de turnos punta vs. valle  
✅ Disponibilidad según tipo de contrato (FT/PT)  

---

## 🤝 Contribuciones

### Sobre Este Proyecto
Este es un **proyecto académico finalizado** y **no se encuentra en desarrollo activo**. Sin embargo, si encuentras valor en el código o las ideas:

#### Opción 1: Usa como Inspiración
- Haz un **fork** del repositorio
- Adapta el código a tus necesidades
- Desarrolla tu propia versión
- Mantén la atribución al proyecto original

#### Opción 2: Reporta Bugs/Sugerencias
- Si encuentras errores o tienes sugerencias, puedes abrir un **Issue**
- Los autores responderán cuando sea posible
- No se garantiza que los cambios se implementen

#### Opción 3: Pull Requests
- Si deseas mejorar el código, puedes hacer un **Pull Request**
- Sigue la guía en [CONTRIBUTING.md](CONTRIBUTING.md)
- Los cambios serán revisados, pero sin compromisos de timing

### Directrices de Uso
- ✅ **Permitido:** Usar como base para tu propio proyecto
- ✅ **Permitido:** Citar en investigaciones académicas
- ✅ **Permitido:** Modificar y distribuir bajo MIT License
- ⚠️ **Requerido:** Mantener atribución a los autores originales

---

## 📜 Licencia

Este proyecto está bajo la licencia **MIT License**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

> **Nota académica:** Este proyecto fue desarrollado como parte del curriculum de la Pontificia Universidad Católica de Chile. Se permite el uso académico y comercial bajo los términos de la licencia MIT.

---

## 📞 Contacto

Para preguntas, sugerencias o reportes de bugs, contacta a los autores:

- **Javier Becerra** - [@javier-becerra](https://github.com/) - jabecerram@udd.cl
- **Diego Raquelich** - [@diego-raquelich](https://github.com/) - draquelichm@udd.cl
- **Valentina Morales** - [@valentina-morales](https://github.com/) - vmoralesf@udd.cl

**Institución:** Universidad del Desarrollo de Chile  
**Departamento:** Ingeniería Civil Industrial  
**Período:** 1° Trimestre 2026

---

## 📝 Citas & Referencias

Si utilizas este código en tu investigación o proyecto académico, considera citar:

```bibtex
@software{transurban_2026,
  authors = {Becerra, J. and Raquelich, D. and Morales, V.},
  title = {TRANSURBAN Capacity Planning & Rostering Optimization},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub Repository},
  howpublished = {\url{https://github.com/[tu-usuario]/transurban-capacity-planning}},
  note = {Universidad del Desarrollo de Chile - Taller de Ingeniería Industrial}
}
```

### Referencias Académicas Utilizadas

```bibtex
@article{Feng2023,
  author = {Feng, Tao and Lusby, Richard M. and Zhang, Yongxiang and Peng, Qiyuan and Shang, Pan and Tao, Siyu},
  title = {An ADMM-based dual decomposition mechanism for integrating crew scheduling and rostering in an urban rail transit line},
  journal = {Transportation Research Part C: Emerging Technologies},
  volume = {149},
  pages = {104081},
  year = {2023},
  issn = {0968-090X},
  doi = {10.1016/j.trc.2023.104081},
  url = {https://www.sciencedirect.com/science/article/pii/S0968090X23000700}
}
```

---

**Gracias por tu interés en este proyecto. ¡Happy coding! 🚀**
| Export CSV vacío | Sin estado de roster o rutas | Ejecuta motor y carga rutas primero |

### Roadmap / Mejoras futuras
- [ ] Importación incremental de datos sin recargar UI.
- [ ] Gráficos de frontera Pareto en modal.
- [ ] Persistencia de preferencias (FT/PT, iteraciones).
- [ ] Reportes en PDF con métricas y cronograma.
- [ ] Sincronización con base de datos remota.

### Contacto y contribuciones
Desarrollado para TRANSURBAN SpA. Para consultas, reportar bugs o sugerencias, contactar al equipo de TI.

**Versión**: 2.0 (con threading, exportación CSV y optimización Pareto)  
**Última actualización**: Abril 2026

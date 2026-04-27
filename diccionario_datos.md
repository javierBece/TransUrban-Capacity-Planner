# Diccionario para el conjunto de datos de Transurban
## Descripción general
Este documento proporciona un diccionario detallado de los datos utilizados en el proyecto de Capacity Planning para Transurban SpA. Incluye la descripción de cada archivo de datos, su formato, y el significado de cada columna.

## CSV Rutas tiempo frecuencia TRANSURBAN.csv
### Descripción
Este archivo contiene la información oficial de los recorridos y frecuencias de Transurban SpA. Es la fuente principal con la que se basa la generación de la demanda mensual para el motor de planificación.

### Columnas
- `Terminal_logico`: El terminal donde se estaciona el bus al finalizar su ruta o donde comienza (generalmente este terminal tiene puntos para recarga de baterías o combustibles). Luego este bus puede ser utilizado para otras rutas que nacen desde ese terminal, puede ser el mismo conductor o otro dependiendo del estado o horario que se encuentre dicho conductor en ese momento.
- `recorrido:` El nombre del recorrido, que TRANSURBAN SpA utiliza para identificar el tramo, este puede tener varios slots o rutas en diferentes tiempos.
- `Origen`:El punto de inicio del recorrido.
- `Destino`: El punto final del recorrido, el cual puede ser un terminal o un paradero.
- `Rango_horario`: Rango horarrio ej: 07:00-09:59, este rango horario se puede dividir en varios slots dependiendo de la frecuencia que tenga el recorrido (su banda si es punta o no).
- `Banda`: Si el recorrido se hace en horario AM_PUNTA, PM_PUNTA o VALLE. Esto afecta la frecuencia del recorrido, ya que en horas punta se necesitan más buses para cubrir la demanda.
- `Tiempo_recorrido_estimado_min`: El tiempo estimado para completar el recorrido en minutos.
- `Frecuencia_headway_min`: La frecuencia en minutos entre cada bus que realiza el recorrido. Por ejemplo, si la frecuencia es de 15 minutos, significa que cada 15 minutos sale un bus para ese recorrido.

## CSV Paraderos TRANSURBAN.csv
### Descripción
Este archivo contiene información sobre los paraderos utilizados por Transurban SpA. Es opcional para el flujo de generación de demanda, pero puede ser útil para análisis adicionales o para la visualización de rutas.

### Columnas
- `Recorrido`: El nombre del recorrido al que pertenece el paradero, que debe coincidir con los recorridos listados en el archivo de rutas.
- `Origen`: El punto de inicio del recorrido asociado al paradero.
- `Destino`: El punto final del recorrido asociado al paradero.
- `Paradero_seq`: El numero de secuencia del paradero dentro del recorrido, indicando su posición relativa (por ejemplo, 1 para el primer paradero, 2 para el segundo, etc.).
- `Paradero_nombre`: El nombre del paradero, que puede ser utilizado para identificarlo en mapas o visualizaciones.
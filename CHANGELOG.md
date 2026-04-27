# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2025-04-27

### Estado del Proyecto
**PROYECTO COMPLETO - NO EN DESARROLLO ACTIVO**

Este es el lanzamiento final como proyecto académico para el Taller de Ingeniería Industrial (TII) en abril de 2026. El código está disponible como referencia e inspiración, pero no se seguirá desarrollando en el corto plazo.

### Añadido
- 🎉 Lanzamiento inicial del proyecto
- ✨ Interfaz gráfica Tkinter con diseño editorial moderno
- ⚙️ Motor de optimización ADMM para planificación de turnos
- 📊 Generación de demanda 24/7 desde archivos CSV
- 📈 Análisis de frontera de Pareto para optimización costo-servicio
- 💾 Importación/Exportación de rutas y paraderos
- 📋 Visualización de cronogramas interactivos
- 🔍 Validación fuzzy de paraderos y rutas
- 📱 Barra de progreso animada y logs en tiempo real
- 👥 Soporte para conductores Full-Time (FT) y Part-Time (PT)
- ⚖️ Restricciones laborales: descansos, fines de semana, horas máximas

### Características
- **Algoritmo ADMM:** Implementación del Alternating Direction Method of Multipliers
  - Inspirado en: Feng et al. (2023) - *Transportation Research Part C*, 149, 104081
  - Adaptación: Dual decomposition para integración de crew scheduling y rostering
- **Threading:** Ejecución no bloqueante del motor para mantener UI responsiva
- **Validación robusta:** Detección y sugerencia de inconsistencias en datos
- **Documentación:** Diccionario de datos, guía de uso y especificaciones de diseño

## Roadmap Futuro

> ⚠️ **Nota:** Estos son planes conceptuales. El proyecto está "congelado" en v1.0.0 por ahora.
> Si deseas continuar el desarrollo, puedes hacer un fork e implementar estas mejoras.

### Planeado para v1.1.0 (Futuro - No Programado)
- [ ] Integración con bases de datos (PostgreSQL/MySQL)
- [ ] API REST para consultas externas
- [ ] Dashboard web con Dash/Streamlit
- [ ] Múltiples escenarios de demanda
- [ ] Exportación a formatos adicionales (Excel con gráficos, PDF)

### Planeado para v2.0.0 (Futuro - No Programado)
- [ ] Optimización con machine learning para predicción de demanda
- [ ] Integración con sistemas de GPS en tiempo real
- [ ] Análisis predictivo de ausentismo
- [ ] Mobile app para asignación de turnos

## Notas

Este proyecto es desarrollado como parte del Taller de Ingeniería Industrial en la Universidad del Desarrollo de Chile.

### Referencias Principales
- **Feng, T., Lusby, R. M., Zhang, Y., Peng, Q., Shang, P., & Tao, S. (2023)**
  - An ADMM-based dual decomposition mechanism for integrating crew scheduling and rostering in an urban rail transit line
  - Transportation Research Part C: Emerging Technologies, 149, 104081
  - https://doi.org/10.1016/j.trc.2023.104081

---

**Fecha de inicio del proyecto:** Enero 2025  
**Fecha de finalización:** Abril 2026  
**Estado actual:** Completo (Sin desarrollo activo)  
**Versión actual:** 1.0.0  
**Propósito:** Proyecto académico - Referencia e inspiración

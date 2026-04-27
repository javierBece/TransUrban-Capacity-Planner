import pandas as pd
from pathlib import Path

class RuteadorLegal:
    def __init__(self, df_viajes):
        """
        Inicializa el ruteador con el dataframe maestro de viajes.
        Se asume que df_viajes tiene: ID_VIAJE, HORA_INICIO_MIN, HORA_FIN_MIN
        """
        # Convertimos el DataFrame a un diccionario para búsquedas súper rápidas O(1)
        self.viajes_info = {}
        for _, row in df_viajes.iterrows():
            self.viajes_info[row['ID_VIAJE']] = {
                'inicio': row['HORA_INICIO_MIN'], # En minutos (ej. 08:00 -> 480)
                'fin': row['HORA_FIN_MIN'],       # En minutos
                'duracion': row['HORA_FIN_MIN'] - row['HORA_INICIO_MIN']
            }
            
        # Parámetros Legales (Art. 25 y 25 bis)
        self.MAX_CONDUCCION_CONTINUA = 5 * 60  # 300 minutos (5 horas)
        self.MAX_PERMANENCIA = 12 * 60         # 720 minutos (12 horas)
        self.MIN_DESCANSO = 30                 # 30 minutos obligatorios post 5 hrs

    def es_transicion_valida(self, ruta_actual, nuevo_viaje_id, conductor_id):
        """
        Verifica si agregar 'nuevo_viaje_id' cumple la ley, separando los turnos
        diarios mediante el descanso legal de 10 horas (600 minutos).
        """
        viaje_nuevo = self.viajes_info[nuevo_viaje_id]

        # --- CANDADO DE DÍA CALENDARIO PARA PART-TIME ---
        if conductor_id.startswith('PT'):
            # Extraer el día del viaje (Ej: 'D2_B6_20_24_Bus51' -> 'D2')
            dia_nuevo = nuevo_viaje_id.split('_')[0]
            minutos_hoy = 0

            # Sumar todo lo que ya se le asignó en ese mismo día
            for v_id in ruta_actual:
                if v_id.startswith(dia_nuevo + '_'):
                    minutos_hoy += self.viajes_info[v_id]['duracion']
                    
            # Límite estricto: 6 horas (360 min) totales en el día calendario
            if (minutos_hoy + viaje_nuevo['duracion']) > 360:
                return False
                
        if not ruta_actual:
            return True # Primer viaje del mes
            
        ultimo_viaje_id = ruta_actual[-1]
        ultimo_viaje = self.viajes_info[ultimo_viaje_id]
        
        # 1. Validar Traslape (El bus no puede estar en dos lugares a la vez)
        if viaje_nuevo['inicio'] < ultimo_viaje['fin']:
            return False 
            
        # 2. ¿Es un Nuevo Día o el Mismo Turno?
        # Descanso legal mínimo entre jornadas es 10 hrs = 600 min
        descanso_previo = viaje_nuevo['inicio'] - ultimo_viaje['fin']
        
        if descanso_previo >= 600:
            # --- ES UN NUEVO TURNO (Al día siguiente) ---
            # Los contadores están en cero. Solo validamos la conducción continua de este viaje.
            if viaje_nuevo['duracion'] > self.MAX_CONDUCCION_CONTINUA:
                return False
            return True
            
        else:
            # --- ES EL MISMO TURNO (Continuación de la jornada de hoy) ---
            inicio_turno = viaje_nuevo['inicio']
            tiempo_continuo = viaje_nuevo['duracion']
            
            # Revisamos el historial hacia atrás para calcular los acumulados de HOY
            for i in range(len(ruta_actual)-1, -1, -1):
                v_actual = self.viajes_info[ruta_actual[i]]
                
                if i == len(ruta_actual)-1:
                    descanso = viaje_nuevo['inicio'] - v_actual['fin']
                else:
                    v_siguiente = self.viajes_info[ruta_actual[i+1]]
                    descanso = v_siguiente['inicio'] - v_actual['fin']
                    
                # Si encontramos el fin del turno de ayer, dejamos de sumar
                if descanso >= 600:
                    break 
                    
                # Actualizamos cuándo empezó el turno de hoy
                inicio_turno = v_actual['inicio']
                
                # Regla de 5 hrs de conducción: si el descanso fue menor a 30 min, seguimos sumando fatiga
                if descanso < self.MIN_DESCANSO:
                    tiempo_continuo += v_actual['duracion']
                    
                if tiempo_continuo > self.MAX_CONDUCCION_CONTINUA:
                    return False # Excedió las 5 horas seguidas al volante
                    
            # 3. Validar Permanencia Diaria Máxima
            limite_permanencia = 6 * 60 if conductor_id.startswith('PT') else self.MAX_PERMANENCIA
            permanencia = viaje_nuevo['fin'] - inicio_turno
            if permanencia > limite_permanencia:
                return False
                
            return True

    def construir_mejor_ruta(self, costos_ajustados, conductor_id):
        """
        Busca armar una secuencia de viajes que minimice el costo ajustado.
        """
        # Ordenar los viajes por hora de inicio cronológicamente
        viajes_ordenados = sorted(self.viajes_info.keys(), key=lambda x: self.viajes_info[x]['inicio'])
        
        ruta_optima = []
        
        for viaje_id in viajes_ordenados:
            costo_viaje = costos_ajustados.get(viaje_id, float('inf'))
            
            # CORRECCIÓN: El costo base es 50. 
            # Si el costo es menor a 55, significa que nadie más lo ha tomado (no hay peaje).
            # Por lo tanto, el chofer lo toma si es legal.
            if costo_viaje < 55: 
                if self.es_transicion_valida(ruta_optima, viaje_id, conductor_id):
                    ruta_optima.append(viaje_id)
                    
        return set(ruta_optima)


def generar_demanda_mensual_24_7(num_ft: int, num_pt: int, write_demanda: bool = True, dias: int = 28, output_dir: str | Path = 'datos_rostering') -> Path:
    """Genera la plantilla mensual de conductores para el motor ADMM.

    Crea `datos_rostering/plantilla_mensual.csv` con IDs tipo FTxxx y PTxxx.
    El parámetro `write_demanda` queda disponible para compatibilidad, pero
    no altera la plantilla directamente.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    registros = []
    for i in range(1, max(0, int(num_ft)) + 1):
        registros.append({'ID_Conductor': f'FT{i:03d}', 'Tipo': 'Full-Time'})
    for i in range(1, max(0, int(num_pt)) + 1):
        registros.append({'ID_Conductor': f'PT{i:03d}', 'Tipo': 'Part-Time'})

    df_plantilla = pd.DataFrame(registros)
    plantilla_path = out_dir / 'plantilla_mensual.csv'
    df_plantilla.to_csv(plantilla_path, index=False, sep=';')

    return plantilla_path

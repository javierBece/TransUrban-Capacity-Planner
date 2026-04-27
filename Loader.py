import pandas as pd
import os

# 1. IDENTIFICACIÓN DE RUTAS
# Obtenemos la carpeta donde está este script (C:\...\APP)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Definimos la subcarpeta de datos (según tu imagen: 'datos_rostering')
CARPETA_DATOS = os.path.join(BASE_DIR, 'datos_rostering')

def cargar_datos_proyecto():
    """
    Carga los archivos de TransUrban SpA y transforma la demanda 
    agregada en tareas individuales para el motor ADMM.
    """
    # Construcción de rutas completas
    ruta_plantilla = os.path.join(CARPETA_DATOS, 'plantilla_mensual.csv')
    ruta_demanda = os.path.join(CARPETA_DATOS, 'demanda_mensual.csv')

    print(f"\n[Loader] Iniciando carga...")
    print(f"[Loader] Carpeta de origen: {CARPETA_DATOS}")

    try:
        # 2. CARGA DE CONDUCTORES
        # Usamos sep=';' porque tus archivos usan punto y coma
        df_conductores = pd.read_csv(ruta_plantilla, sep=';')
        # El archivo real usa 'ID_Conductor' (case sensitive)
        ids_conductores = df_conductores['ID_Conductor'].tolist()

        # 3. CARGA DE DEMANDA MENSUAL
        df_demanda = pd.read_csv(ruta_demanda, sep=';')
        
    except FileNotFoundError as e:
        print(f"\n[!] ERROR CRÍTICO: No se encontró el archivo.")
        print(f"Ruta buscada: {e.filename}")
        print("Asegúrate de que la carpeta 'datos_rostering' esté dentro de 'APP'.")
        raise

    # 4. CONFIGURACIÓN DE BLOQUES HORARIOS (En minutos para el Art. 25)
    info_bloques = {
        'B1_00_04': {'inicio': 0,    'fin': 240},
        'B2_04_08': {'inicio': 240,  'fin': 480},
        'B3_08_12': {'inicio': 480,  'fin': 720},
        'B4_12_16': {'inicio': 720,  'fin': 960},
        'B5_16_20': {'inicio': 960,  'fin': 1200},
        'B6_20_24': {'inicio': 1200, 'fin': 1440}
    }
    
    lista_viajes = []

    # 5. "DESENROLLADO" DE DEMANDA (Matrix to Flat list)
    # Convertimos cada número de bus en una tarea unitaria
    for index, fila in df_demanda.iterrows():
        dia = int(fila['Dia'])
        for nombre_bloque, tiempos in info_bloques.items():
            # Obtenemos la cantidad de buses requeridos para ese bloque
            cantidad_buses = int(fila[nombre_bloque])
            
            for i in range(cantidad_buses):
                id_viaje = f"D{dia}_{nombre_bloque}_Bus{i+1}"
                
                # Desplazamiento por día (1440 min = 24 horas)
                minutos_dia_extra = (dia - 1) * 1440
                
                lista_viajes.append({
                    'ID_VIAJE': id_viaje,
                    'HORA_INICIO_MIN': tiempos['inicio'] + minutos_dia_extra,
                    'HORA_FIN_MIN': tiempos['fin'] + minutos_dia_extra,
                    'DIA': dia,
                    'COSTO': 50.0  # Costo base para el motor
                })
                
    # Creamos el DataFrame final de tareas
    df_viajes_completo = pd.DataFrame(lista_viajes)
    ids_viajes = df_viajes_completo['ID_VIAJE'].tolist()
    
    # Diccionario de costos para el ADMM
    costos_base = dict(zip(df_viajes_completo['ID_VIAJE'], df_viajes_completo['COSTO']))
    
    print(f"[Loader] Proceso completado exitosamente.")
    print(f" -> Conductores cargados: {len(ids_conductores)}")
    print(f" -> Tareas de bus generadas: {len(ids_viajes)}\n")
    
    return ids_conductores, ids_viajes, costos_base, df_viajes_completo
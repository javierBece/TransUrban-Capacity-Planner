import pandas as pd
import numpy as np
import time
from Loader import cargar_datos_proyecto
from generador_rostering import RuteadorLegal
import os

# --- CONFIGURACIÓN TÉCNICA DEL MOTOR ---
CONFIG = {
    "rho_inicial": 0.5,        # Penalización inicial
    "rho_max": 10.0,           # Límite de penalización para evitar inestabilidad
    "rho_incremento": 1.05,    # Factor de crecimiento por iteración
    "max_iteraciones": 100,    # Máximo de intentos para encontrar consenso
    "alpha_equidad": 0.1       # Peso de la equidad en el costo (opcional)
}

class MotorADMMTransUrban:
    def __init__(self, ids_conductores, ids_viajes, costos_base, df_viajes_completo):
        self.conductores = ids_conductores
        self.viajes = ids_viajes
        self.costos_base = costos_base
        
        # Inicialización de parámetros ADMM
        self.lambdas = {v: 0.0 for v in ids_viajes}
        self.rho = CONFIG["rho_inicial"]
        
        # Estado del sistema
        self.rutas_actuales = {d: set() for d in ids_conductores}
        self.consenso_global = {v: 0 for v in ids_viajes}
        
        # El "Abogado Legal" (Subproblema)
        self.ruteador = RuteadorLegal(df_viajes_completo)

    def calcular_costo_ajustado(self, viaje_id):
        """
        Fórmula M4: c_hat = c - lambda + (rho/2)*(2*F_da - 1)
        Nota: consenso_global[viaje_id] ya actúa como F_da 
        porque extraemos al conductor actual antes de calcular esto.
        """
        c_base = self.costos_base.get(viaje_id, 50.0)
        l_dual = self.lambdas.get(viaje_id, 0.0)
        f_da = self.consenso_global[viaje_id]
        
        peaje_admm = (self.rho / 2.0) * (2 * f_da - 1)
        return c_base - l_dual + peaje_admm

    def ejecutar_iteracion(self):
        """
        ACTUALIZACIÓN RODANTE: Corazón del Algoritmo
        Los conductores deciden uno por uno, viendo lo que hicieron los anteriores.
        """
        for d in self.conductores:
            # 1. Extraer la decisión previa de este conductor del consenso
            for v_id in self.rutas_actuales[d]:
                if v_id in self.consenso_global:
                    self.consenso_global[v_id] -= 1
            
            # 2. Calcular costos actualizados según el estado de los DEMÁS
            costos_percibidos = {v: self.calcular_costo_ajustado(v) for v in self.viajes}
            
            # 3. Resolver el ruteador legal para este conductor
            nueva_ruta_d = self.ruteador.construir_mejor_ruta(costos_percibidos, d)
            
            # 4. Actualizar su ruta y sumarla al consenso INMEDIATAMENTE
            self.rutas_actuales[d] = nueva_ruta_d
            for v_id in nueva_ruta_d:
                if v_id in self.consenso_global:
                    self.consenso_global[v_id] += 1

    def actualizar_multiplicadores(self):
        """ Actualización de Lambdas (Precios de Sombra) """
        for v in self.viajes:
            # CORRECCIÓN: Si el viaje está vacío (0), el error es +1. 
            # Esto hace que el subsidio (lambda) crezca y el costo baje.
            error = 1 - self.consenso_global[v] 
            self.lambdas[v] += self.rho * error

    def calcular_kpis(self):
        """ Monitoreo de calidad de la solución """
        total_viajes = len(self.viajes)
        cubiertos = sum(1 for v in self.viajes if self.consenso_global[v] >= 1)
        conflictos = sum(max(0, self.consenso_global[v] - 1) for v in self.viajes)
        
        return {
            "cobertura": (cubiertos / total_viajes) * 100,
            "conflictos": conflictos,
            "rho": self.rho
        }

    def optimizar(self):
        print(f"Iniciando Motor ADMM: {len(self.conductores)} conductores, {len(self.viajes)} viajes.")
        print("-" * 50)
        
        for i in range(CONFIG["max_iteraciones"]):
            self.ejecutar_iteracion()
            self.actualizar_multiplicadores()
            
            # Aumentar rho gradualmente
            self.rho = min(CONFIG["rho_max"], self.rho * CONFIG["rho_incremento"])
            
            stats = self.calcular_kpis()
            print(f"Iter {i+1:02d} | Cobertura: {stats['cobertura']:>5.1f}% | Conflictos: {stats['conflictos']} | Rho: {stats['rho']:.2f}")
            
            if stats['cobertura'] == 100 and stats['conflictos'] == 0:
                print("-" * 50)
                print("¡CONSENSO ALCANZADO! Todos los viajes cubiertos legalmente.")
                break

    def exportar_resultados_csv(self):
        """ Exporta el calendario final a un CSV para entregar a la empresa """
        print("\nExportando el Roster mensual a CSV...")
        filas = []
        
        for conductor, viajes in self.rutas_actuales.items():
            for viaje_id in viajes:
                # Extraemos el día, bloque y bus del ID (Ej: D1_B2_04_08_Bus1)
                partes = viaje_id.split('_')
                dia = partes[0].replace('D', '')
                bloque = partes[1]
                
                filas.append({
                    'ID_Conductor': conductor,
                    'Dia_Mes': dia,
                    'Bloque': bloque,
                    'ID_Viaje_Asignado': viaje_id
                })
                
        df_resultados = pd.DataFrame(filas)
        # Lo guardamos en la misma carpeta de datos
        import pathlib
        base_dir = pathlib.Path(__file__).resolve().parent
        out_dir = base_dir / 'datos_rostering'
        out_dir.mkdir(parents=True, exist_ok=True)
        ruta_salida = out_dir / 'ROSTER_FINAL_TRANSURBAN.csv'
        df_resultados.to_csv(ruta_salida, index=False, sep=';')
        print(f"¡Éxito! Archivo guardado en: {ruta_salida}")

# --- BLOQUE DE EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    try:
        # 1. Carga de datos reales desde Loader.py
        ids_c, ids_v, costos_b, df_v = cargar_datos_proyecto()
        
        # 2. Inicializar y correr motor
        motor = MotorADMMTransUrban(ids_c, ids_v, costos_b, df_v)
        
        start = time.time()
        motor.optimizar()
        end = time.time()
        
        print(f"\nTiempo de ejecución: {end - start:.2f} segundos.")
        
    except FileNotFoundError as e:
        print(f"Error: No se encontró uno de los archivos CSV. {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
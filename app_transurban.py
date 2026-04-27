print("====================================================")
print("🚀 EL ARCHIVO SE ESTÁ EJECUTANDO CORRECTAMENTE 🚀")
print("====================================================")

import os
import time
import math
import threading
import queue
import csv
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import itertools
import threading
from Loader import cargar_datos_proyecto
from main_rostering_admm import MotorADMMTransUrban


class GradientButton(tk.Canvas):
    def __init__(self, parent, text, command=None, height=44, **kwargs):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=parent.cget('bg'))
        self._text = text
        self._command = command
        self._enabled = True
        self._height = height
        self.bind('<Configure>', lambda e: self._draw())
        self.bind('<Button-1>', self._on_click)

    def _hex_interp(self, a, b, t):
        return '#%02x%02x%02x' % tuple(int(a[i:i+2], 16) + int((int(b[i:i+2], 16)-int(a[i:i+2], 16))*t) for i in (0,2,4))

    def _draw(self):
        self.delete('all')
        w = max(self.winfo_width(), 10)
        h = self._height
        # gradient colors
        if self._enabled:
            c1 = 'af101a'
            c2 = 'd32f2f'
        else:
            c1 = 'f2bdbd'
            c2 = 'f7d6d6'
        # draw vertical gradient
        for i in range(w):
            t = i / max(w-1, 1)
            color = self._hex_interp(c1, c2, t)
            self.create_line(i, 0, i, h, fill=color)
        # rounded-ish overlay
        self.create_text(w/2, h/2, text=self._text, fill='white' if self._enabled else '#7a2a2a', font=('Inter', 10, 'bold'))

    def _on_click(self, event):
        if not self._enabled:
            return
        if callable(self._command):
            self._command()

    def enable(self):
        self._enabled = True
        self._draw()

    def disable(self):
        self._enabled = False
        self._draw()

    def set_state(self, state):
        if state in (tk.NORMAL, 'normal'):
            self.enable()
        else:
            self.disable()


class ConsoleWriter:
    def __init__(self, app, stream_name):
        self.app = app
        self.stream_name = stream_name

    def write(self, text):
        if not text:
            return
        # Evitar insertar sólo retornos de carro aislados
        if text == '\r':
            return
        try:
            if hasattr(self.app, '_schedule_ui'):
                self.app._schedule_ui(self.app._append_console_log, text)
            else:
                self.app._append_console_log(text)
        except Exception:
            pass

    def flush(self):
        pass


try:
    import generador_rostering
    import main_rostering_admm
    from Loader import cargar_datos_proyecto
    
    # ESTA ES LA LÍNEA QUE FALTABA
    import adaptar_recorridos_a_demanda as adapter
    
except Exception as e:
    print("========================================")
    print("🚨 ERROR CRÍTICO DE IMPORTACIÓN 🚨")
    print(f"Detalle del error: {repr(e)}")
    print("========================================")
    raise


class TransurbanPlanningApp:
    def __init__(self, root):
        print(">> [SYS] Iniciando secuencia de arranque de la aplicación...")
        self.root = root
        self.root.title("TRANSURBAN SpA - Sistema de Capacity Planning")
        self.root.geometry("1140x780")
        self.root.minsize(1100, 760)
        self.root.configure(bg="#f9f9f9")

        print(">> [SYS] Asignando memoria para variables de estado (Modelo)...")
        # --- BLOQUE DE ESTADO RESTAURADO ---
        self.num_ft = tk.StringVar(value="20")
        self.num_pt = tk.StringVar(value="10")
        self.max_iter = tk.StringVar(value="5")
        self.turnaround = tk.StringVar(value="0")
        self.weekend_factor = tk.StringVar(value="0.6")
        self.include_reverse = tk.BooleanVar(value=True)
        self.match_alternate = tk.BooleanVar(value=True)
        
        # VARIABLE CRÍTICA: Resuelve el primer AttributeError
        self.schedule_day = tk.StringVar(value="1") 
        
        self.schedule_zoom = 1.0
        self.current_routes_file = None
        self.route_schedule = []
        self.is_running = False
        self.last_roster_state = None
        self.last_roster_coverage = None
        self.console_log_buffer = ""
        self.console_window = None
        self.console_text = None
        self.app_dir = Path(__file__).resolve().parent
        self.ui_queue = queue.Queue()

        print(">> [SYS] Inicializando motor de renderizado de tipografías...")
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(family="Inter", size=10)
        except Exception:
            pass

        print(">> [SYS] Construyendo Árbol de Componentes de la Interfaz (Vista)...")
        # PARCHE CRÍTICO: Inyectar el componente faltante antes de construir la UI
        # Esto resuelve el segundo AttributeError
        self.state_label = tk.Label(self.root, text="") 
        
        self._build_ui()
        
        print(">> [SYS] Vinculando flujos estándar al gestor de logs interno...")
        self._redirect_stdout()
        
        print(">> [SYS] Estableciendo máquina de estados a 'idle'...")
        self._set_state("idle")
        self._process_ui_queue()
        
        print(">> [SYS] Secuencia de arranque completada. Interfaz montada y lista.")

    def _build_ui(self):
        # Header with subtle white surface and a thin primary accent
        top_accent = tk.Frame(self.root, bg="#af101a", height=6)
        top_accent.pack(fill=tk.X, side=tk.TOP)

        header = tk.Frame(self.root, bg="#ffffff", height=88)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(header, text="TRANSURBAN SpA", fg="#af101a", bg="#ffffff", font=("Inter", 22, "bold")).pack(pady=(10, 0), anchor="w", padx=18)
        tk.Label(header, text="Sistema de Gestión de Flota y Turnos • Red Metropolitana", fg="#5b5b5b", bg="#ffffff", font=("Inter", 10, "normal")).pack(pady=(0, 8), anchor="w", padx=18)

        body = tk.Frame(self.root, bg="#f9f9f9")
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        # Left sidebar background (surface_container_low)
        left = tk.Frame(body, bg="#f3f3f3")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=0)
        left.configure(width=360)

        # Inner card for left controls (white floating surface)
        left_card = tk.Frame(left, bg="#ffffff")
        left_card.pack(fill=tk.BOTH, expand=True, padx=16, pady=18)

        # Right main area
        right = tk.Frame(body, bg="#f9f9f9")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=0)

        right_card = tk.Frame(right, bg="#ffffff")
        right_card.pack(fill=tk.BOTH, expand=True, padx=(0, 6), pady=18)

        self._build_left_panel(left_card)
        self._build_right_panel(right_card)

    def _build_left_panel(self, parent):
        """Panel izquierdo minimalista y optimizado para el Motor ADMM"""
        # 1. SECCIÓN DE DATOS (Mantenemos esto si lo usas para visualizar)
        f_datos = ttk.LabelFrame(parent, text=" 📂 Carga de Datos Base ")
        f_datos.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(f_datos, text="🗺️ Importar Paraderos", command=self.import_paraderos).pack(fill="x", padx=5, pady=3)
        ttk.Button(f_datos, text="🚌 Importar Rutas", command=self.import_rutas).pack(fill="x", padx=5, pady=3)

        # 2. SECCIÓN DEL MOTOR ADMM (El corazón del nuevo sistema)
        f_admm = ttk.LabelFrame(parent, text=" ⚙️ Motor de Rostering ADMM ")
        f_admm.pack(fill="x", padx=10, pady=20)

        # Controles Full-Time
        tk.Label(f_admm, text="Conductores Full-Time:").pack(anchor="w", padx=10, pady=(10,0))
        f_ft = tk.Frame(f_admm)
        f_ft.pack(fill="x", padx=10)
        self.ft_var = tk.IntVar(value=250)
        ttk.Scale(
            f_ft,
            from_=100,
            to_=400,
            variable=self.ft_var,
            orient="horizontal",
            command=lambda v: self.ft_var.set(int(float(v)))
        ).pack(side="left", fill="x", expand=True)
        tk.Label(f_ft, textvariable=self.ft_var, width=4).pack(side="right")

        # Controles Part-Time
        tk.Label(f_admm, text="Conductores Part-Time:").pack(anchor="w", padx=10, pady=(10,0))
        f_pt = tk.Frame(f_admm)
        f_pt.pack(fill="x", padx=10)
        self.pt_var = tk.IntVar(value=150)
        ttk.Scale(
            f_pt,
            from_=50,
            to_=300,
            variable=self.pt_var,
            orient="horizontal",
            command=lambda v: self.pt_var.set(int(float(v)))
        ).pack(side="left", fill="x", expand=True)
        tk.Label(f_pt, textvariable=self.pt_var, width=4).pack(side="right")

        ttk.Button(f_admm, text="✨ Encontrar Plantilla Óptima", command=self.optimize_service_cost).pack(fill="x", padx=10, pady=(10, 5))

        # Botón Maestro de Ejecución
        self.admm_btn_run = ttk.Button(
            f_admm, 
            text="🚀 Iniciar Optimización Global", 
            command=self._preparar_y_ejecutar_admm
        )
        self.admm_btn_run.pack(fill="x", padx=10, pady=20, ipady=8) # ipady=8 lo hace un botón grande y principal

        # Panel de Estado y Progreso
        self.admm_progress = ttk.Progressbar(f_admm, orient="horizontal", mode="determinate")
        self.admm_progress.pack(fill="x", padx=10, pady=5)
        
        self.admm_status_label = tk.Label(f_admm, text="Estado: Sistema Listo", font=("Segoe UI", 9, "italic"))
        self.admm_status_label.pack(pady=5)

    def _grid_field(self, frame, label, var, row):
        tk.Label(frame, text=label, bg="#ffffff", fg="#1a1c1c", font=("Inter", 10)).grid(row=row, column=0, sticky="w", pady=6)
        tk.Entry(frame, textvariable=var, width=12, font=("Inter", 10), bd=0, relief=tk.FLAT, highlightthickness=1, highlightbackground="#eeeeee", highlightcolor="#af101a").grid(row=row, column=1, pady=6, padx=8)

    def _build_right_panel(self, parent):
        tk.Label(parent, text="Resultados y Análisis", bg="#ffffff", fg="#1a1c1c", font=("Inter", 16, "bold")).pack(anchor="w", pady=(10, 8), padx=12)

        top_buttons = tk.Frame(parent, bg="#ffffff")
        top_buttons.pack(fill=tk.X, padx=12, pady=(0, 8))
        tab_kwargs = {
            'bg': '#ffffff',
            'fg': '#005f7b',
            'font': ('Inter', 10, 'bold'),
            'bd': 1,
            'relief': tk.RIDGE,
            'activebackground': '#f8fafc',
            'activeforeground': '#005f7b',
            'highlightthickness': 0,
            'cursor': 'hand2',
            'padx': 10,
            'pady': 6,
        }
        tk.Button(top_buttons, text="Métricas", command=self._show_metrics_modal, **tab_kwargs).pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(top_buttons, text="Consola", command=self._show_console_window, **tab_kwargs).pack(side=tk.RIGHT)

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        results_frame = tk.Frame(notebook, bg="#ffffff")
        schedule_frame = tk.Frame(notebook, bg="#ffffff")
        notebook.add(results_frame, text="Resultados")
        notebook.add(schedule_frame, text="Cronograma")

        driver_frame = tk.Frame(notebook, bg="#ffffff")
        notebook.add(driver_frame, text="Vista por Conductor")

        driver_controls = tk.Frame(driver_frame, bg="#ffffff")
        driver_controls.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(driver_controls, text="Conductor:", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10, "bold")).pack(side=tk.LEFT)
        self.driver_view_var = tk.StringVar()
        self.driver_view_combobox = ttk.Combobox(
            driver_controls,
            textvariable=self.driver_view_var,
            values=[],
            width=18,
            state="readonly",
            font=("Inter", 10)
        )
        self.driver_view_combobox.pack(side=tk.LEFT, padx=(8, 8))
        self.driver_view_combobox.bind("<<ComboboxSelected>>", lambda e: self._update_driver_view())
        ttk.Button(driver_controls, text="🔍 Ver Rutina", command=self._update_driver_view).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(driver_controls, text="📄 Exportar a CSV", command=self._export_individual_roster_csv).pack(side=tk.LEFT)

        driver_tree_frame = tk.Frame(driver_frame, bg="#ffffff")
        driver_tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.driver_view_tree = ttk.Treeview(
            driver_tree_frame,
            columns=("Día", "Bloque Horario", "Horario Real", "Recorrido"),
            show="headings",
            height=14
        )
        self.driver_view_tree.heading("Día", text="Día")
        self.driver_view_tree.heading("Bloque Horario", text="Bloque Horario")
        self.driver_view_tree.heading("Horario Real", text="Horario Real")
        self.driver_view_tree.heading("Recorrido", text="Recorrido")
        self.driver_view_tree.column("Día", width=50, anchor="center")
        self.driver_view_tree.column("Bloque Horario", width=160, anchor="w")
        self.driver_view_tree.column("Horario Real", width=120, anchor="center")
        self.driver_view_tree.column("Recorrido", width=320, anchor="w")
        self.driver_view_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        driver_tree_scroll = ttk.Scrollbar(driver_tree_frame, orient=tk.VERTICAL, command=self.driver_view_tree.yview)
        driver_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.driver_view_tree.configure(yscrollcommand=driver_tree_scroll.set)

        self.results_text = tk.Text(results_frame, height=18, wrap=tk.WORD, bd=0, relief=tk.FLAT, font=("Inter", 10), bg="#fbfcff", fg="#111")
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        welcome_text = """Bienvenido al sistema\n\nEste módulo de planificación utiliza técnicas avanzadas (ADMM) para:\n- Generar planes de turnos mensuales óptimos\n- Cumplir restricciones laborales y legales\n- Minimizar costos operativos\n- Maximizar nivel de servicio\n\n1. Configure los parámetros\n2. Importe el CSV oficial (preferible con 'Importar y Ejecutar Motor')\n3. Presione 'EJECUTAR PLANIFICACIÓN'"""
        self.results_text.insert(tk.END, welcome_text)
        self.results_text.tag_configure('title', font=("Inter", 11, 'bold'), foreground='#0f3f8c')
        self.results_text.tag_add('title', '1.0', '1.end')
        self.results_text.config(state=tk.DISABLED)

        schedule_card = tk.Frame(schedule_frame, bg="#ffffff")
        schedule_card.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        schedule_card.configure(highlightthickness=0)

        header_card = tk.Frame(schedule_card, bg="#f9f9f9")
        header_card.pack(fill=tk.X, padx=16, pady=(16, 0))
        tk.Label(header_card, text="Cronograma por recorrido", bg="#f9f9f9", fg="#1a1c1c", font=("Inter", 13, "bold")).pack(anchor="w", pady=(10, 2))
        tk.Label(header_card, text="Selecciona un día para revisar la agenda diaria. El eje X muestra las 24 horas y cada bloque refleja el operador asignado.", bg="#f9f9f9", fg="#5b5b5b", font=("Inter", 10)).pack(anchor="w", pady=(0, 14))

        toolbar = tk.Frame(schedule_card, bg="#ffffff")
        toolbar.pack(fill=tk.X, padx=16, pady=(0, 16))
        tk.Label(toolbar, text="Seleccionar día:", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10)).pack(side=tk.LEFT, padx=(0, 8))
        day_values = [str(i) for i in range(1, 29)]
        day_picker = ttk.Combobox(toolbar, values=day_values, textvariable=self.schedule_day, width=5, state="readonly", font=("Inter", 10))
        day_picker.pack(side=tk.LEFT)
        day_picker.bind("<<ComboboxSelected>>", lambda e: self._refresh_schedule_tab())
        try:
            # Also refresh when the variable changes programmatically or by typing
            self.schedule_day.trace_add('write', lambda *args: self._refresh_schedule_tab())
        except Exception:
            pass

        zoom_frame = tk.Frame(toolbar, bg="#ffffff")
        zoom_frame.pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(zoom_frame, text="Zoom:", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(zoom_frame, text="−", command=lambda: self._adjust_schedule_zoom(-0.1), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="+", command=lambda: self._adjust_schedule_zoom(0.1), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT, padx=(4, 0))
        self.zoom_level_label = tk.Label(zoom_frame, text="100%", bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"))
        self.zoom_level_label.pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(zoom_frame, text="Reset", command=self._reset_schedule_zoom, bg="#ffffff", fg="#005f7b", font=("Inter", 10), bd=1, relief="solid", cursor="hand2").pack(side=tk.LEFT, padx=(8, 0))

        nav_frame = tk.Frame(toolbar, bg="#ffffff")
        nav_frame.pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(nav_frame, text="Mover:", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(nav_frame, text="←", command=lambda: self._pan_schedule(-1, 0), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(nav_frame, text="→", command=lambda: self._pan_schedule(1, 0), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(nav_frame, text="↑", command=lambda: self._pan_schedule(0, -1), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(nav_frame, text="↓", command=lambda: self._pan_schedule(0, 1), bg="#ffffff", fg="#005f7b", font=("Inter", 10, "bold"), bd=1, relief="solid", width=2, cursor="hand2").pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(nav_frame, text="Ajustar ancho", command=self._fit_schedule_width, bg="#ffffff", fg="#005f7b", font=("Inter", 10), bd=1, relief="solid", cursor="hand2").pack(side=tk.LEFT, padx=(10, 0))

        self.export_schedule_btn = GradientButton(toolbar, text="💾 Exportar Turnos CSV", command=self._export_assignments_csv, height=34)
        self.export_schedule_btn.pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(toolbar, text="Ver detalle del día", command=self._show_day_detail_modal, bg="#f9f9f9", fg="#005f7b", font=("Inter", 10, "bold"), bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=(0, 8))
        canvas_outer = tk.Frame(schedule_card, bg="#f3f3f3", bd=0)
        canvas_outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        canvas_frame = tk.Frame(canvas_outer, bg="#f3f3f3")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.schedule_canvas = tk.Canvas(canvas_frame, bg="#f9f9f9", highlightthickness=0)
        self.schedule_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        schedule_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.schedule_canvas.yview)
        schedule_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        hscroll = ttk.Scrollbar(canvas_outer, orient=tk.HORIZONTAL, command=self.schedule_canvas.xview)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))

        self.schedule_canvas.configure(yscrollcommand=schedule_scroll.set, xscrollcommand=hscroll.set)
        self.schedule_canvas.bind("<Leave>", lambda e: self._hide_schedule_tooltip())
        self.schedule_canvas.bind("<Configure>", lambda e: self.schedule_canvas.configure(scrollregion=self.schedule_canvas.bbox("all")))
        self.schedule_canvas.bind("<Shift-MouseWheel>", lambda e: self.schedule_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.schedule_canvas.bind("<MouseWheel>", lambda e: self.schedule_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self.schedule_canvas_event_details = {}
        self.schedule_tooltip = tk.Label(self.schedule_canvas, bg="#1a1c1c", fg="#ffffff", font=("Inter", 9), bd=0, padx=6, pady=4, relief=tk.SOLID, wraplength=260, justify=tk.LEFT)
        self.schedule_tooltip.place_forget()

        self._refresh_schedule_tab()

        # --- Sección Ejecuciones (reportes de funcionamiento) ---
        ejecuciones_container = tk.Frame(parent, bg="#f3f3f3")
        ejecuciones_container.pack(fill=tk.X, padx=12, pady=(6, 12))

        ejecuciones_card = tk.Frame(ejecuciones_container, bg="#ffffff")
        ejecuciones_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Label(ejecuciones_card, text="Ejecuciones", bg="#ffffff", fg="#1a1c1c", font=("Inter", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

        scroll_frame = tk.Frame(ejecuciones_card, bg="#ffffff")
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.ejecuciones_text = tk.Text(scroll_frame, height=8, wrap=tk.WORD, bd=0, relief=tk.FLAT, font=("Inter", 10), bg="#ffffff", fg="#111")
        vscroll = tk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=self.ejecuciones_text.yview)
        self.ejecuciones_text.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.ejecuciones_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ejecuciones_text.insert(tk.END, "Registros de ejecuciones aparecerán aquí.\n")
        self.ejecuciones_text.config(state=tk.DISABLED)

    def _set_state(self, state):
        """Controlador de estado global blindado para la nueva UI ADMM"""
        # 1. ESTADO: ESPERANDO DATOS
        if state == "idle":
            if hasattr(self, 'admm_status_label'):
                self.admm_status_label.config(text="⚠️ Faltan datos — importe CSV para continuar", fg="#ba1a1a")
            if hasattr(self, 'admm_progress'):
                self.admm_progress.stop()
            if hasattr(self, 'admm_btn_run'):
                self.admm_btn_run.config(state=tk.DISABLED)
            self._set_progress_message("")

        # 2. ESTADO: LISTO PARA MOTOR ADMM
        elif state == "ready":
            if hasattr(self, 'admm_status_label'):
                self.admm_status_label.config(text="✅ Estado: Lista para optimizar", fg="#005f7b")
            if hasattr(self, 'admm_progress'):
                self.admm_progress.stop()
            if hasattr(self, 'admm_btn_run'):
                self.admm_btn_run.config(state=tk.NORMAL)
            self._set_progress_message("")

        # 3. ESTADO: CALCULANDO
        elif state == "running":
            if hasattr(self, 'admm_status_label'):
                self.admm_status_label.config(text="⚙️ Estado: Ejecución en curso...", fg="#f57c00")
            if hasattr(self, 'admm_progress'):
                self.admm_progress.start(10)
            if hasattr(self, 'admm_btn_run'):
                self.admm_btn_run.config(state=tk.DISABLED)
            self._set_progress_message("Preparando ejecución...")

        # 4. ESTADO: ERROR
        elif state == "error":
            if hasattr(self, 'admm_status_label'):
                self.admm_status_label.config(text="❌ Estado: Error en el proceso", fg="#ba1a1a")
            if hasattr(self, 'admm_progress'):
                self.admm_progress.stop()
            self._set_progress_message("")
            
        # Parche de seguridad por si alguna función antigua busca la etiqueta vieja
        if hasattr(self, 'state_label') and self.state_label.winfo_exists():
            try:
                if state == "idle": self.state_label.config(text="⚠️ Demanda no generada")
                elif state == "ready": self.state_label.config(text="Estado: lista para ejecutar")
                elif state == "running": self.state_label.config(text="Estado: ejecución en curso...")
                elif state == "error": self.state_label.config(text="Estado: error")
            except Exception:
                pass

    def _set_progress_message(self, message: str):
        if hasattr(self, 'progress_message'):
            self.progress_message.config(text=message or "")

    def _schedule_ui(self, callback, *args, **kwargs):
        try:
            self.ui_queue.put((callback, args, kwargs))
        except Exception:
            pass

    def _process_ui_queue(self):
        try:
            while not self.ui_queue.empty():
                callback, args, kwargs = self.ui_queue.get()
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"[UI QUEUE ERROR] {e}")
                    continue
        finally:
            try:
                self.root.after(100, self._process_ui_queue)
            except Exception as e:
                print(f"[UI QUEUE SCHEDULING ERROR] {e}")

    def _redirect_stdout(self):
        import sys
        sys.stdout = ConsoleWriter(self, 'stdout')
        sys.stderr = ConsoleWriter(self, 'stderr')

    def _append_console_log(self, text: str):
        if not text:
            return
        self.console_log_buffer += text
        if hasattr(self, 'console_text') and self.console_text is not None:
            try:
                import re
                self.console_text.config(state=tk.NORMAL)

                # Guardamos el índice donde empieza el nuevo texto
                start_index = self.console_text.index("end-1c")
                self.console_text.insert(tk.END, text)

                # Patrones de búsqueda para el Motor ADMM
                patrones = {
                    r"Iter \d+": "iter",
                    r"Cobertura:\s*\d+\.\d+%": "cob",
                    r"Conflictos:\s*\d+": "conf",
                    r"Rho:\s*\d+\.\d+": "rho"
                }

                # Aplicar los tags de color
                for patron, tag in patrones.items():
                    for match in re.finditer(patron, text):
                        start_pos = f"{start_index}+{match.start()}c"
                        end_pos = f"{start_index}+{match.end()}c"
                        self.console_text.tag_add(tag, start_pos, end_pos)

                self.console_text.see(tk.END)
                self.console_text.config(state=tk.DISABLED)
            except Exception:
                pass

    def _show_console_window(self):
        if self.console_window is not None and self.console_window.winfo_exists():
            self.console_window.lift()
            return

        self.console_window = tk.Toplevel(self.root)
        self.console_window.title("Consola de Backend")
        self.console_window.geometry("780x460")

        frame = tk.Frame(self.console_window, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True)

        self.console_text = tk.Text(frame, wrap=tk.WORD, bd=0, relief=tk.FLAT, font=("Inter", 10), bg="#111111", fg="#f5f5f5")
        self.console_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.console_text.tag_configure("iter", foreground="#3b82f6", font=("Inter", 10, "bold")) # Azul
        self.console_text.tag_configure("cob", foreground="#22c55e", font=("Inter", 10, "bold"))  # Verde
        self.console_text.tag_configure("conf", foreground="#ef4444", font=("Inter", 10, "bold")) # Rojo
        self.console_text.tag_configure("rho", foreground="#f59e0b", font=("Inter", 10, "bold"))  # Naranja
        self.console_text.configure(state=tk.NORMAL)
        self.console_text.insert(tk.END, self.console_log_buffer)
        self.console_text.configure(state=tk.DISABLED)

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.configure(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(self.console_window, bg="#f9f9f9")
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Limpiar consola", command=self._clear_console, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold"), bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=6, pady=6)
        tk.Button(btn_frame, text="Cerrar", command=self._on_close_console, bg="#ffffff", fg="#005f7b", font=("Inter", 10), bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=6, pady=6)
        self.console_window.protocol("WM_DELETE_WINDOW", self._on_close_console)

    def _clear_console(self):
        self.console_log_buffer = ""
        if hasattr(self, 'console_text') and self.console_text is not None:
            try:
                self.console_text.config(state=tk.NORMAL)
                self.console_text.delete(1.0, tk.END)
                self.console_text.config(state=tk.DISABLED)
            except Exception:
                pass

    def _on_close_console(self):
        if self.console_window is not None:
            try:
                self.console_window.destroy()
            except Exception:
                pass
        self.console_window = None
        self.console_text = None

    def _write_results(self, text):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state=tk.DISABLED)

    def _schedule_block_label(self, block: int) -> str:
        labels = {
            1: 'Madrugada (00-04)',
            2: 'Punta Mañana (04-08)',
            3: 'Valle Mañana (08-12)',
            4: 'Valle Tarde (12-16)',
            5: 'Punta Tarde (16-20)',
            6: 'Noche (20-24)'
        }
        return labels.get(block, f'B{block}')

    def _format_hour(self, hour_float):
        if hour_float is None:
            return "--:--"
        h = int(hour_float) % 24
        m = int(round((hour_float - int(hour_float)) * 60))
        return f"{h:02d}:{m:02d}"

    def _build_bus_segments(self, details):
        segments = []
        start = details.get('start_float', 0.0)
        end = details.get('end_float', start + 1.0)
        buses = max(1, int(details.get('buses', 1)))
        headway = details.get('headway')
        duration = details.get('duration')
        total_span = max(0.1, end - start)

        if buses == 1:
            segments.append({'bus': 1, 'start': start, 'end': end, 'operator': details['operators'][0] if details['operators'] else None})
            return segments

        if headway and duration and headway > 0:
            interval = headway / 60.0
            for i in range(buses):
                bus_start = start + i * interval
                bus_end = bus_start + duration
                if bus_start >= end:
                    break
                if bus_end > end:
                    bus_end = end
                operator = details['operators'][i] if i < len(details['operators']) else None
                segments.append({'bus': i + 1, 'start': bus_start, 'end': bus_end, 'operator': operator})

            if len(segments) < buses:
                for i in range(len(segments), buses):
                    bus_start = max(start, end - (duration if duration else total_span / buses))
                    bus_end = end
                    operator = details['operators'][i] if i < len(details['operators']) else None
                    segments.append({'bus': i + 1, 'start': bus_start, 'end': bus_end, 'operator': operator})
            return segments

        bus_duration = duration if duration else max(0.5, total_span / max(1, buses))
        spacing = (total_span - bus_duration) / max(1, buses - 1)
        for i in range(buses):
            bus_start = start + i * spacing
            bus_end = bus_start + bus_duration
            if bus_end > end:
                bus_end = end
            operator = details['operators'][i] if i < len(details['operators']) else None
            segments.append({'bus': i + 1, 'start': bus_start, 'end': bus_end, 'operator': operator})

        return segments

    def _show_schedule_tooltip(self, event, tag):
        details = self.schedule_canvas_event_details.get(tag)
        if not details:
            return
        self.schedule_tooltip.config(text=details['detail_text'])
        x = event.x + 16
        y = event.y + 12
        self.schedule_tooltip.place(x=x, y=y)

    def _hide_schedule_tooltip(self):
        if hasattr(self, 'schedule_tooltip'):
            self.schedule_tooltip.place_forget()

    def _show_route_detail_modal(self, tag):
        details = self.schedule_canvas_event_details.get(tag)
        if not details:
            return
        top = tk.Toplevel(self.root)
        top.title(f"Detalle del recorrido {details['route']}")
        top.transient(self.root)
        top.grab_set()
        top.geometry("640x520")

        header = tk.Frame(top, bg="#ffffff")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        tk.Label(header, text=f"Detalle de {details['route']}", font=("Inter", 13, "bold"), bg="#ffffff", fg="#1a1c1c").pack(anchor="w")

        body = tk.Frame(top, bg="#f9f9f9")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        summary = tk.Frame(body, bg="#ffffff", bd=0)
        summary.pack(fill=tk.X, pady=(0, 10), padx=10)
        tk.Label(summary, text=f"Recorrido: {details['route']}", font=("Inter", 11, "bold"), bg="#ffffff", fg="#1a1c1c").pack(anchor='w', pady=(10, 2))
        tk.Label(summary, text=f"Horario: {details['start']} - {details['end']}    Bloque: {details['block']}    Buses: {details['buses']}", font=("Inter", 9), bg="#ffffff", fg="#555").pack(anchor='w', pady=(0, 8))

        timeline_frame = tk.Frame(body, bg="#f5f5f5")
        timeline_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        canvas = tk.Canvas(timeline_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(timeline_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(canvas, bg="#f5f5f5")
        canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_config(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
        inner.bind('<Configure>', _on_inner_config)

        start_float = details['start_float']
        end_float = details['end_float']
        visible_duration = max(1.0, end_float - start_float)
        timeline_width = 520
        axis_left = 10

        axis_canvas = tk.Canvas(inner, width=timeline_width + 150, height=40, bg="#f9f9f9", highlightthickness=0)
        axis_canvas.pack(fill=tk.X, pady=(0, 10))
        axis_canvas.create_rectangle(axis_left, 20, axis_left + timeline_width, 22, fill="#ddd", outline="")

        tick_count = max(2, int(math.ceil(visible_duration)) + 1)
        for i in range(tick_count):
            tick_time = start_float + i
            x = axis_left + (timeline_width * i / (tick_count - 1))
            axis_canvas.create_line(x, 16, x, 26, fill="#888")
            axis_canvas.create_text(x, 30, text=f"{int(tick_time) % 24:02d}:00", font=("Inter", 8), fill="#333")

        segments = self._build_bus_segments(details)
        if not segments:
            tk.Label(inner, text="No hay buses asignados.", bg="#f5f5f5", fg="#555", font=("Inter", 10, "italic")).pack(pady=12)
        else:
            for seg in segments:
                row_frame = tk.Frame(inner, bg="#ffffff")
                row_frame.pack(fill=tk.X, pady=4)
                label = tk.Label(row_frame, text=f"Bus {seg['bus']}", width=12, anchor='w', bg="#ffffff", fg="#1a1c1c", font=("Inter", 9, "bold"))
                label.pack(side=tk.LEFT, padx=(0, 10))

                bar_canvas = tk.Canvas(row_frame, width=timeline_width, height=28, bg="#eceff1", highlightthickness=0)
                bar_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

                bar_x0 = axis_left + ((seg['start'] - start_float) / visible_duration) * timeline_width
                bar_x1 = axis_left + ((seg['end'] - start_float) / visible_duration) * timeline_width
                if bar_x1 <= bar_x0 + 12:
                    bar_x1 = bar_x0 + 12

                bar_canvas.create_rectangle(bar_x0 - axis_left, 4, bar_x1 - axis_left, 24, fill="#af101a", outline="")
                operator_label = seg['operator'] if seg['operator'] else "Sin operador"
                bar_canvas.create_text((bar_x0 + bar_x1) / 2 - axis_left, 14, text=operator_label, fill="#ffffff", font=("Inter", 8, "bold"))
                bar_canvas.create_text(bar_x0 - axis_left + 2, 2, anchor='nw', text=self._format_hour(seg['start']), font=("Inter", 7), fill="#111")
                bar_canvas.create_text(bar_x1 - axis_left - 2, 2, anchor='ne', text=self._format_hour(seg['end']), font=("Inter", 7), fill="#111")

        footer = tk.Frame(body, bg="#ffffff")
        footer.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(footer, text="Cerrar", command=top.destroy, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold"), bd=0, cursor="hand2").pack(side=tk.RIGHT)

    def _update_driver_view(self):
        conductor = self.driver_view_var.get()
        if not conductor:
            messagebox.showwarning("Seleccionar conductor", "Seleccione un conductor antes de ver la rutina.")
            return

        if not self.last_roster_state or conductor not in self.last_roster_state:
            messagebox.showwarning("Datos no disponibles", "No hay datos de rutina para el conductor seleccionado.")
            return

        self.driver_view_tree.delete(*self.driver_view_tree.get_children())
        rows = []
        for viaje_id in self.last_roster_state[conductor].get('slots_asignados', []):
            partes = viaje_id.split('_')
            dia = int(partes[0].replace('D', '')) if partes and partes[0].startswith('D') else 0
            bloque = 1
            inicio_hora = 0
            hora_label = "--:--"
            if len(partes) >= 4:
                try:
                    bloque = int(partes[1].replace('B', ''))
                except Exception:
                    bloque = 1
                try:
                    inicio_hora = int(partes[2])
                    fin_hora = int(partes[3])
                    hora_label = f"{self._format_hour(inicio_hora)} - {self._format_hour(fin_hora)}"
                except Exception:
                    hora_label = "--:--"
            else:
                try:
                    bloque = int(partes[1].replace('B', ''))
                except Exception:
                    bloque = 1

            rows.append({
                'day': dia,
                'block': bloque,
                'block_label': self._schedule_block_label(bloque),
                'time_label': hora_label,
                'viaje_id': viaje_id,
                'start_hour': inicio_hora
            })

        rows.sort(key=lambda x: (x['day'], x['start_hour']))
        for row in rows:
            self.driver_view_tree.insert(
                '',
                tk.END,
                values=(
                    row['day'],
                    row['block_label'],
                    row['time_label'],
                    row['viaje_id']
                )
            )

    def _export_individual_roster_csv(self):
        conductor = self.driver_view_var.get()
        if not conductor:
            messagebox.showwarning("Seleccionar conductor", "Seleccione un conductor antes de exportar la rutina.")
            return

        if not self.last_roster_state or conductor not in self.last_roster_state:
            messagebox.showwarning("Datos no disponibles", "No hay datos de rutina para el conductor seleccionado.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv')],
            initialfile=f'Rutina_Mes_{conductor}.csv',
            title='Guardar rutina de conductor'
        )
        if not filepath:
            return

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Día', 'Bloque Horario', 'Horario Real', 'Recorrido'])

            rows = []
            for viaje_id in self.last_roster_state[conductor].get('slots_asignados', []):
                partes = viaje_id.split('_')
                dia = int(partes[0].replace('D', '')) if partes and partes[0].startswith('D') else 0
                bloque = 1
                horario = "--:--"
                if len(partes) >= 4:
                    try:
                        bloque = int(partes[1].replace('B', ''))
                        horario = f"{self._format_hour(int(partes[2]))} - {self._format_hour(int(partes[3]))}"
                    except Exception:
                        bloque = 1
                        horario = "--:--"
                else:
                    try:
                        bloque = int(partes[1].replace('B', ''))
                    except Exception:
                        bloque = 1

                rows.append({
                    'day': dia,
                    'block': bloque,
                    'block_label': self._schedule_block_label(bloque),
                    'time_label': horario,
                    'viaje_id': viaje_id,
                    'start_hour': int(partes[2]) if len(partes) >= 3 and partes[2].isdigit() else 0
                })

            rows.sort(key=lambda x: (x['day'], x['start_hour']))
            for row in rows:
                writer.writerow([row['day'], row['block_label'], row['time_label'], row['viaje_id']])

        messagebox.showinfo("Exportación completada", f"Rutina del conductor {conductor} exportada a {filepath}")

    def _show_day_detail_modal(self):
        if not self.schedule_canvas_event_details:
            messagebox.showinfo("Detalle del día", "No hay recorridos cargados para el día seleccionado.")
            return
        top = tk.Toplevel(self.root)
        top.title(f"Detalle del día {self.schedule_day.get()}")
        top.transient(self.root)
        top.grab_set()
        top.geometry("560x420")

        header = tk.Frame(top, bg="#ffffff")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        tk.Label(header, text=f"Detalle completo del día {self.schedule_day.get()}", font=("Inter", 12, "bold"), bg="#ffffff", fg="#1a1c1c").pack(anchor="w")

        body = tk.Frame(top, bg="#f9f9f9")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        text = tk.Text(body, wrap=tk.WORD, bd=0, relief=tk.FLAT, font=("Inter", 10), bg="#ffffff", fg="#111")
        text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vs = tk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=vs.set)

        for _, details in sorted(self.schedule_canvas_event_details.items(), key=lambda item: item[1]['start']):
            text.insert(tk.END, f"Recorrido: {details['route']}\n")
            text.insert(tk.END, f"  Horario: {details['start']} - {details['end']}\n")
            text.insert(tk.END, f"  Bloque: {details['block']}\n")
            text.insert(tk.END, f"  Buses: {details['buses']}\n")
            if details['operators']:
                for i, operator in enumerate(details['operators'], start=1):
                    text.insert(tk.END, f"    Bus {i}: {operator}\n")
            else:
                text.insert(tk.END, "    Sin operador\n")
            text.insert(tk.END, "\n")

        text.config(state=tk.DISABLED)
        tk.Button(top, text="Cerrar", command=top.destroy, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold"), bd=0, cursor="hand2").pack(pady=10)

    def _compute_metrics(self, selected_day: int | None = None):
        """Calcula métricas de la última ejecución y de la demanda/plantilla actual para un día concreto."""
        if selected_day is None:
            selected_day = int(self.schedule_day.get()) if self.schedule_day.get().isdigit() else 1
        selected_day = max(1, min(28, selected_day))

        if self.last_roster_state is None:
            return {
                'error': 'Debe ejecutar la optimización global primero para ver las métricas.',
                'selected_day': selected_day
            }

        metrics = {}
        try:
            estado = self.last_roster_state
            cobertura = self.last_roster_coverage
            slots = None

            ids_c, ids_v, costos_b, df_v = cargar_datos_proyecto()
            daily_slots = df_v[df_v['DIA'] == selected_day]
            total_slots = len(daily_slots)
            coverage_source = self.last_roster_coverage or {}
            slots_cubiertos = sum(
                1 for _, slot in daily_slots.iterrows()
                if coverage_source.get(slot['ID_VIAJE'], 0) >= 1
            )
            coverage_pct = (slots_cubiertos / total_slots * 100) if total_slots else 0.0

            estado = self.last_roster_state
            cobertura = coverage_source
            ft_usados = 0
            pt_usados = 0
            if estado is not None:
                for d, dat in estado.items():
                    bloques = dat.get('bloques_por_dia', {})
                    if len(bloques.get(selected_day, [])) > 0:
                        if dat.get('tipo') == 'Full-Time':
                            ft_usados += 1
                        else:
                            pt_usados += 1

            slots_by_block = {i: 0 for i in range(1, 7)}
            drivers_by_block = {i: 0 for i in range(1, 7)}

            if 'daily_slots' in locals() and daily_slots is not None:
                for _, slot in daily_slots.iterrows():
                    viaje_id = slot['ID_VIAJE']
                    try:
                        bloque = int(viaje_id.split('_')[1].replace('B', ''))
                    except Exception:
                        bloque = 1

                    slots_by_block[bloque] += 1
                    if coverage_source.get(viaje_id, 0) >= 1:
                        drivers_by_block[bloque] += 1

            deficits = []
            top_deficits = []
            if self.route_schedule and estado is not None:
                drivers_pool = {}
                for d, dat in estado.items():
                    for b in dat.get('bloques_por_dia', {}).get(selected_day, []):
                        drivers_pool.setdefault(b, []).append(d)
                for ev in self.route_schedule:
                    if ev.get('block') and ev.get('start') is not None:
                        b = ev['block']
                        required = int(ev.get('buses', 0))
                        assigned = min(len(drivers_pool.get(b, [])), required)
                        deficit = max(0, required - assigned)
                        if deficit > 0:
                            deficits.append({'route': ev.get('route'), 'block': b, 'required': required, 'deficit': deficit})
                from collections import defaultdict
                agg = defaultdict(int)
                for d in deficits:
                    agg[d['route']] += d['deficit']
                top_deficits = sorted([{'route': r, 'faltan': n} for r, n in agg.items()], key=lambda x: x['faltan'], reverse=True)[:8]


            metrics = {
                'total_slots': total_slots,
                'slots_cubiertos': slots_cubiertos,
                'coverage_pct': coverage_pct,
                'ft_usados': ft_usados,
                'pt_usados': pt_usados,
                'slots_by_block': slots_by_block,
                'drivers_by_block': drivers_by_block,
                'top_deficits': top_deficits,
                'selected_day': selected_day,
                'has_roster': estado is not None,
                'has_route_schedule': bool(self.route_schedule),
            }
        except Exception as e:
            metrics = {'error': 'No fue posible calcular métricas (revisar logs).', 'error_detail': str(e), 'selected_day': selected_day}
        return metrics

    def _show_metrics_modal(self):
        initial_day = int(self.schedule_day.get()) if self.schedule_day.get().isdigit() else 1
        visible_day = max(1, min(28, initial_day))
        day_var = tk.IntVar(value=visible_day)

        top = tk.Toplevel(self.root)
        top.title(f"Métricas — Día {day_var.get()}")
        top.transient(self.root)
        top.grab_set()
        top.geometry("760x560")

        header = tk.Frame(top, bg="#af101a")
        header.pack(fill=tk.X)
        tk.Label(header, text="Métricas de Cobertura y Plantilla", bg="#af101a", fg="#ffffff", font=("Inter", 13, "bold")).pack(padx=12, pady=10, anchor='w')

        body = tk.Frame(top, bg="#f9f9f9")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        nav_frame = tk.Frame(body, bg="#f9f9f9")
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(nav_frame, text="Seleccione día:", bg="#f9f9f9", fg="#1a1c1c", font=("Inter", 10, "bold")).pack(side=tk.LEFT)

        prev_button = tk.Button(nav_frame, text="← Día anterior", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10), bd=1, relief="solid", command=lambda: day_var.set(max(1, day_var.get() - 1)), cursor="hand2")
        prev_button.pack(side=tk.LEFT, padx=(12, 6))

        day_picker = ttk.Combobox(nav_frame, values=[str(i) for i in range(1, 29)], textvariable=day_var, width=4, state="readonly", font=("Inter", 10))
        day_picker.pack(side=tk.LEFT)

        next_button = tk.Button(nav_frame, text="Día siguiente →", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10), bd=1, relief="solid", command=lambda: day_var.set(min(28, day_var.get() + 1)), cursor="hand2")
        next_button.pack(side=tk.LEFT, padx=(6, 0))

        content_frame = tk.Frame(body, bg="#f9f9f9")
        content_frame.pack(fill=tk.BOTH, expand=True)

        def update_buttons():
            prev_button.config(state=tk.NORMAL if day_var.get() > 1 else tk.DISABLED)
            next_button.config(state=tk.NORMAL if day_var.get() < 28 else tk.DISABLED)

        def render_metrics():
            for child in content_frame.winfo_children():
                child.destroy()

            m = self._compute_metrics(selected_day=day_var.get())
            top.title(f"Métricas — Día {m.get('selected_day', '?')}")
            update_buttons()

            if 'error' in m:
                tk.Label(content_frame, text=m['error'], bg="#f9f9f9", fg="#ba1a1a", font=("Inter", 11)).pack(pady=12)
                if m.get('error_detail'):
                    tk.Label(content_frame, text=m['error_detail'], bg="#f9f9f9", fg="#555", font=("Inter", 9), wraplength=700, justify='left').pack(pady=(0, 10))
                return

            stats_frame = tk.Frame(content_frame, bg="#ffffff")
            stats_frame.pack(fill=tk.X, pady=(0, 12), padx=0)
            stats_frame.configure(padx=12, pady=12)

            coverage_text = (
                f"Cobertura día {m['selected_day']}: {m['slots_cubiertos']}/{m['total_slots']} slots cubiertos ({m['coverage_pct']:.1f}%)"
                if m.get('coverage_pct') is not None else
                "Cobertura del día: datos de demanda no disponibles"
            )
            tk.Label(stats_frame, text=coverage_text, bg="#ffffff", fg="#1a1c1c", font=("Inter", 11, "bold")).pack(anchor='w')
            tk.Label(stats_frame, text=f"Choferes activos el día {m['selected_day']} (FT): {m['ft_usados']}    (PT): {m.get('pt_usados', 0)}", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10)).pack(anchor='w', pady=(6,0))

            block_frame = tk.Frame(content_frame, bg="#ffffff")
            block_frame.pack(fill=tk.X, pady=(0, 12), padx=0)
            tk.Label(block_frame, text="Demanda vs capacidad por bloque", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 6))
            headers = ["Bloque", "Buses requeridos", "Choferes programados", "Brecha"]
            for idx, text in enumerate(headers):
                tk.Label(block_frame, text=text, bg="#ffffff", fg="#555", font=("Inter", 9, "bold")).grid(row=1, column=idx, sticky='w', padx=(0 if idx == 0 else 12, 0))

            for i in range(1, 7):
                required = m['slots_by_block'].get(i, 0)
                assigned = m['drivers_by_block'].get(i, 0)
                gap = max(0, required - assigned)
                tk.Label(block_frame, text=self._schedule_block_label(i), bg="#ffffff", fg="#555", font=("Inter", 9)).grid(row=i+1, column=0, sticky='w', pady=2)
                tk.Label(block_frame, text=str(required), bg="#ffffff", fg="#555", font=("Inter", 9)).grid(row=i+1, column=1, sticky='w', padx=12)
                tk.Label(block_frame, text=str(assigned), bg="#ffffff", fg="#1a1c1c", font=("Inter", 9, "bold")).grid(row=i+1, column=2, sticky='w', padx=12)
                tk.Label(block_frame, text=str(gap), bg="#ffffff", fg="#ba1a1a" if gap > 0 else '#2ca02c', font=("Inter", 9)).grid(row=i+1, column=3, sticky='w', padx=12)

            deficits_frame = tk.Frame(content_frame, bg="#ffffff")
            deficits_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 12), padx=0)
            tk.Label(deficits_frame, text="Recorridos con mayor déficit", bg="#ffffff", fg="#1a1c1c", font=("Inter", 10, "bold")).pack(anchor='w')
            if m.get('top_deficits'):
                for td in m['top_deficits']:
                    tk.Label(deficits_frame, text=f"{td['route']}: faltan {td['faltan']}", bg="#ffffff", fg="#ba1a1a" if td['faltan']>0 else '#1a1c1c', font=("Inter", 9)).pack(anchor='w')
            else:
                tk.Label(deficits_frame, text="No hay déficits detectados por ruta con los datos disponibles.", bg="#ffffff", fg="#555", font=("Inter", 9, 'italic')).pack(anchor='w')

            insights_frame = tk.Frame(content_frame, bg="#f9f9f9")
            insights_frame.pack(fill=tk.X, padx=0, pady=(6,0))
            insights = []
            if m.get('coverage_pct') is not None and m['coverage_pct'] < 95.0:
                insights.append(f"Cobertura baja: {m['coverage_pct']:.1f}% para el día {m['selected_day']}.")
            if m['drivers_by_block'].get(2,0) < m['slots_by_block'].get(2,0):
                insights.append("Déficit en Bloque 2 (mañana): priorizar choferes FT o PT para ese bloque.")
            overcapacity_blocks = [i for i in range(1, 7) if m['drivers_by_block'].get(i, 0) > m['slots_by_block'].get(i, 0) and m['slots_by_block'].get(i, 0) > 0]
            if overcapacity_blocks:
                for i in overcapacity_blocks:
                    surplus = m['drivers_by_block'][i] - m['slots_by_block'][i]
                    insights.append(f"Sobreoferta en {self._schedule_block_label(i)}: {surplus} choferes adicionales respecto a buses requeridos.")
            if not insights:
                insights.append("Nivel de servicio adecuado según los datos disponibles.")

            for it in insights:
                tk.Label(insights_frame, text=f"• {it}", bg="#f9f9f9", fg="#005f7b", font=("Inter", 10)).pack(anchor='w')

        day_var.trace_add('write', lambda *args: render_metrics())
        render_metrics()

        tk.Button(top, text="Cerrar", command=top.destroy, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold"), bd=0, cursor="hand2").pack(pady=8)

    def _read_csv_autodetect(self, path):
        import pandas as pd
        from pathlib import Path

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)

        for sep in [';', ',', '\t']:
            try:
                df = pd.read_csv(p, sep=sep, dtype=str, encoding='latin-1').fillna('')
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue

        df = pd.read_csv(p, sep=None, engine='python', dtype=str, encoding='latin-1').fillna('')
        return df

    def _parse_time_range(self, value):
        import pandas as pd
        import re

        if value is None:
            return None, None
        s = str(value).strip()
        if not s:
            return None, None

        matches = re.findall(r'([0-2]?\d[:.]?[0-5]\d)', s)
        if len(matches) >= 2:
            try:
                start = pd.to_datetime(matches[0].replace('.', ':'), format='%H:%M', errors='coerce')
                end = pd.to_datetime(matches[1].replace('.', ':'), format='%H:%M', errors='coerce')
                if pd.isna(start) or pd.isna(end):
                    start = pd.to_datetime(matches[0], errors='coerce')
                    end = pd.to_datetime(matches[1], errors='coerce')
                if pd.isna(start) or pd.isna(end):
                    return None, None
                return float(start.hour) + start.minute / 60.0, float(end.hour) + end.minute / 60.0
            except Exception:
                return None, None

        matches2 = re.findall(r'(\d{1,2})\s*-\s*(\d{1,2})', s)
        if matches2:
            try:
                start = int(matches2[0][0])
                end = int(matches2[0][1])
                return float(start), float(end)
            except Exception:
                return None, None

        return None, None

    def _load_route_schedule(self, routes_csv):
        import math
        import pandas as pd

        df = self._read_csv_autodetect(routes_csv)
        if df.empty:
            return []

        rec_col = None
        range_col = None
        dur_col = None
        freq_col = None

        for col in df.columns:
            lc = str(col).strip().lower()
            if rec_col is None and ('recorr' in lc or 'ruta' in lc or 'route' in lc):
                rec_col = col
            if range_col is None and ('rango' in lc or 'horario' in lc or 'time' in lc or 'inicio' in lc or 'salida' in lc):
                range_col = col
            if dur_col is None and ('tiempo' in lc or 'durac' in lc or 'estim' in lc):
                dur_col = col
            if freq_col is None and ('frecuenc' in lc or 'headway' in lc or 'freq' in lc):
                freq_col = col

        events = []
        for _, row in df.iterrows():
            route_id = str(row.get(rec_col, '')).strip() if rec_col in df.columns else ''
            if not route_id:
                route_id = str(row.name)

            headway = None
            duration = None
            start_hour, end_hour = self._parse_time_range(row.get(range_col, '') if range_col in df.columns else '')
            if start_hour is None or end_hour is None:
                continue
            if end_hour <= start_hour:
                end_hour += 24.0

            buses = 1
            if freq_col in df.columns:
                try:
                    headway = float(str(row.get(freq_col, '')).replace(',', '.'))
                except Exception:
                    headway = None
                if headway and headway > 0:
                    if dur_col in df.columns and str(row.get(dur_col, '')).strip() != '':
                        try:
                            duration = float(str(row.get(dur_col, '')).replace(',', '.'))
                        except Exception:
                            duration = None
                    else:
                        duration = None
                    buses = max(1, int(math.ceil((duration / headway) if duration else (60.0 / headway))))

            block = 1
            if 0 <= start_hour < 4:
                block = 1
            elif 4 <= start_hour < 8:
                block = 2
            elif 8 <= start_hour < 12:
                block = 3
            elif 12 <= start_hour < 16:
                block = 4
            elif 16 <= start_hour < 20:
                block = 5
            elif 20 <= start_hour < 24:
                block = 6

            events.append({
                'route': route_id,
                'start': start_hour,
                'end': end_hour,
                'block': block,
                'buses': buses,
                'headway': headway if 'headway' in locals() else None,
                'duration': duration if 'duration' in locals() else None,
            })

        return events

    def _refresh_schedule_tab(self):
        if not hasattr(self, 'schedule_canvas'):
            return
        self.schedule_canvas.delete('all')
        self.schedule_canvas_event_details.clear()

        if not self.route_schedule:
            self.schedule_canvas.create_text(20, 20, anchor='nw', text="Importe un CSV de rutas válido para ver el cronograma de recorridos.", font=("Inter", 11, "italic"), fill="#444")
            self.schedule_canvas.configure(scrollregion=self.schedule_canvas.bbox('all'))
            return

        try:
            selected_day = int(self.schedule_day.get())
        except Exception:
            selected_day = 1

        route_ids = sorted({event['route'] for event in self.route_schedule})
        if not route_ids:
            self.schedule_canvas.create_text(20, 20, anchor='nw', text="No hay recorridos definidos en el CSV importado.", font=("Inter", 11, "italic"), fill="#444")
            self.schedule_canvas.configure(scrollregion=self.schedule_canvas.bbox('all'))
            return

        zoom = max(0.6, min(2.0, self.schedule_zoom))
        left_margin = 180
        hour_width = int(max(18, 34 * zoom))
        row_height = int(max(48, 74 * zoom))
        top_margin = int(max(70, 90 * zoom))
        canvas_width = left_margin + 24 * hour_width + 48
        canvas_height = top_margin + len(route_ids) * row_height + 96

        self.schedule_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        self.schedule_canvas.config(width=min(canvas_width, 980), height=min(canvas_height, 540))
        self.schedule_canvas.xview_moveto(0)
        self.schedule_canvas.yview_moveto(0)

        title = f"Cronograma del día {selected_day}"
        self.schedule_canvas.create_text(20, 20, anchor='nw', text=title, font=("Inter", 13, "bold"), fill="#1a1c1c")
        self.schedule_canvas.create_text(20, 44, anchor='nw', text="Visualización editorial de los recorridos por horario y conductor.", font=("Inter", 9), fill="#5b5b5b")

        header_bar_y = top_margin - 24
        self.schedule_canvas.create_rectangle(0, header_bar_y, canvas_width, top_margin - 4, fill="#f5f5f5", outline="")
        self.schedule_canvas.create_text(left_margin + 4, header_bar_y + 8, anchor='nw', text="Hora", font=("Inter", 8, "bold"), fill="#5b5b5b")

        for hour in range(0, 25, 2):
            x = left_margin + hour * hour_width
            self.schedule_canvas.create_line(x, top_margin, x, top_margin + len(route_ids) * row_height, fill="#e8e8e8")
            self.schedule_canvas.create_text(x + 2, top_margin - 18, anchor='nw', text=f"{hour:02d}:00", font=("Inter", 8), fill="#333")

        for idx, route in enumerate(route_ids):
            row_y0 = top_margin + idx * row_height
            row_y1 = row_y0 + row_height - 10
            bg = "#ffffff" if idx % 2 == 0 else "#f6f6f6"
            self.schedule_canvas.create_rectangle(0, row_y0, canvas_width, row_y1, fill=bg, outline="")
            self.schedule_canvas.create_text(18, row_y0 + 16, anchor='nw', text=route, font=("Inter", 9, "bold"), fill="#1a1c1c")

        drivers_by_block = {}
        if self.last_roster_state:
            for conductor, datos in self.last_roster_state.items():
                bloques_por_dia = datos.get('bloques_por_dia', {})
                for bloque in bloques_por_dia.get(selected_day, []):
                    drivers_by_block.setdefault(bloque, []).append(conductor)

        # Debug: append a short summary to ejecuciones to help diagnose day-specific assignments
        try:
            if hasattr(self, 'ejecuciones_text') and self.last_roster_state:
                counts = {b: len(v) for b, v in drivers_by_block.items()}
                self._append_ejecucion("Refresh Cronograma", f"Día {selected_day} — conductores por bloque: {counts}")
        except Exception:
            pass

        schedule_events = []
        for event in sorted(self.route_schedule, key=lambda e: (e['route'], e['start'])):
            assigned_drivers = []
            if drivers_by_block.get(event['block']):
                assigned_drivers = drivers_by_block[event['block']][:event['buses']]
                drivers_by_block[event['block']] = drivers_by_block[event['block']][len(assigned_drivers):]
            deficit = max(0, int(event.get('buses', 0)) - len(assigned_drivers))
            schedule_events.append({**event, 'assigned_drivers': assigned_drivers, 'deficit': deficit})

        colors = ["#af101a", "#d32f2f", "#005f7b", "#2ca02c", "#ff7f0e", "#8c564b"]
        for idx, event in enumerate(schedule_events):
            row_index = route_ids.index(event['route'])
            row_y0 = top_margin + row_index * row_height
            bar_y0 = row_y0 + 28
            bar_y1 = bar_y0 + 26
            x0 = left_margin + event['start'] * hour_width
            x1 = left_margin + event['end'] * hour_width
            if x1 <= x0 + 10:
                x1 = x0 + 10
            # Si hay déficit de operadores, usamos color de error y mostramos badge
            if event.get('deficit', 0) > 0:
                fill = '#ba1a1a'
            else:
                fill = colors[row_index % len(colors)] if event['assigned_drivers'] else '#8c8c8c'
            event_tag = f"schedule_event_{idx}"

            self.schedule_canvas.create_rectangle(x0, bar_y0, x1, bar_y1, fill=fill, outline="", tags=("schedule_event", event_tag))

            if event['assigned_drivers']:
                drivers = event['assigned_drivers']
                label = ", ".join(drivers[:3]) + (f" +{len(drivers)-3}" if len(drivers) > 3 else "")
                if event.get('deficit', 0) > 0:
                    label = f"{label} (faltan {event['deficit']})"
            else:
                if event.get('deficit', 0) > 0:
                    label = f"Faltan {event['deficit']}"
                else:
                    label = "Sin operador"

            self.schedule_canvas.create_text((x0 + x1) / 2, (bar_y0 + bar_y1) / 2, text=label, font=("Inter", 8, "bold"), fill="#ffffff", tags=("schedule_event", event_tag))

            start_text = self._format_hour(event['start'])
            end_text = self._format_hour(event['end'] if event['end'] < 24 else event['end'] - 24)
            operator_text = ", ".join(event['assigned_drivers']) if event['assigned_drivers'] else "Sin operador"
            detail_text = f"Recorrido: {event['route']}\nHorario: {start_text} - {end_text}\nBloque: {self._schedule_block_label(event['block'])}\nBuses: {event['buses']}\nOperador(es): {operator_text}"
            if event.get('deficit', 0) > 0:
                detail_text += f"\nFaltan: {event['deficit']} operador(es)"

            self.schedule_canvas_event_details[event_tag] = {
                'title': event['route'],
                'detail_text': detail_text,
                'route': event['route'],
                'start': start_text,
                'end': end_text,
                'start_float': event['start'],
                'end_float': event['end'] if event['end'] > event['start'] else event['end'] + 24.0,
                'headway': event.get('headway'),
                'duration': event.get('duration'),
                'block': self._schedule_block_label(event['block']),
                'buses': event['buses'],
                'operators': event['assigned_drivers'],
                'deficit': event.get('deficit', 0),
            }

            self.schedule_canvas.tag_bind(event_tag, "<Enter>", lambda e, t=event_tag: self._show_schedule_tooltip(e, t))
            self.schedule_canvas.tag_bind(event_tag, "<Leave>", lambda e: self._hide_schedule_tooltip())
            self.schedule_canvas.tag_bind(event_tag, "<Button-1>", lambda e, t=event_tag: self._show_route_detail_modal(t))

        footer_y = top_margin + len(route_ids) * row_height
        self.schedule_canvas.create_text(20, footer_y, anchor='nw', text="Si hay más de un conductor asignado, se muestra el primero + adicionales.", font=("Inter", 9), fill="#555")
        self.schedule_canvas.configure(scrollregion=self.schedule_canvas.bbox('all'))

    def _adjust_schedule_zoom(self, step: float):
        new_zoom = round(self.schedule_zoom + step, 2)
        new_zoom = max(0.6, min(2.0, new_zoom))
        if new_zoom != self.schedule_zoom:
            self.schedule_zoom = new_zoom
            if hasattr(self, 'zoom_level_label'):
                self.zoom_level_label.config(text=f"{int(self.schedule_zoom * 100)}%")
            self._refresh_schedule_tab()

    def _reset_schedule_zoom(self):
        self.schedule_zoom = 1.0
        if hasattr(self, 'zoom_level_label'):
            self.zoom_level_label.config(text="100%")
        self._refresh_schedule_tab()

    def _pan_schedule(self, dx: int, dy: int):
        if not hasattr(self, 'schedule_canvas'):
            return
        if dx != 0:
            self.schedule_canvas.xview_scroll(dx * 10, 'units')
        if dy != 0:
            self.schedule_canvas.yview_scroll(dy * 5, 'units')

    def _fit_schedule_width(self):
        if not hasattr(self, 'schedule_canvas'):
            return
        self.root.update_idletasks()
        visible_width = self.schedule_canvas.winfo_width()
        base_left_margin = 180
        base_hour_width = 34
        extra = 48
        max_width = visible_width - base_left_margin - extra
        if max_width <= 0:
            return
        new_zoom = max(0.6, min(2.0, max_width / (24 * base_hour_width)))
        self.schedule_zoom = round(new_zoom, 2)
        if hasattr(self, 'zoom_level_label'):
            self.zoom_level_label.config(text=f"{int(self.schedule_zoom * 100)}%")
        self._refresh_schedule_tab()

    def _build_export_rows(self):
        if not self.last_roster_state or not self.route_schedule:
            return []

        rows = []
        for selected_day in range(1, 29):
            drivers_by_block = {}
            for conductor, datos in self.last_roster_state.items():
                bloques_por_dia = datos.get('bloques_por_dia', {})
                for bloque in bloques_por_dia.get(selected_day, []):
                    drivers_by_block.setdefault(bloque, []).append(conductor)

            schedule_events = []
            for event in sorted(self.route_schedule, key=lambda e: (e['route'], e['start'])):
                assigned_drivers = []
                if drivers_by_block.get(event['block']):
                    assigned_drivers = drivers_by_block[event['block']][:event['buses']]
                    drivers_by_block[event['block']] = drivers_by_block[event['block']][len(assigned_drivers):]
                deficit = max(0, int(event.get('buses', 0)) - len(assigned_drivers))
                schedule_events.append({**event, 'assigned_drivers': assigned_drivers, 'deficit': deficit})

            for event in schedule_events:
                rows.append({
                    'Día': selected_day,
                    'Recorrido': event['route'],
                    'Bloque': self._schedule_block_label(event['block']),
                    'Inicio': self._format_hour(event['start']),
                    'Fin': self._format_hour(event['end'] if event['end'] < 24 else event['end'] - 24),
                    'Buses': event.get('buses', 0),
                    'Operadores asignados': "; ".join(event['assigned_drivers']) if event['assigned_drivers'] else '',
                    'Faltan operadores': event.get('deficit', 0),
                    'Observaciones': "Sin operador" if not event['assigned_drivers'] else "",
                })

        return rows

    def _export_assignments_csv(self):
        if not self.last_roster_state:
            messagebox.showwarning("Exportar Turnos", "No hay planificación cargada. Ejecute el motor antes de exportar turnos.")
            return
        if not self.route_schedule:
            messagebox.showwarning("Exportar Turnos", "No hay cronograma de recorridos válido. Importe un CSV de rutas primero.")
            return

        rows = self._build_export_rows()
        if not rows:
            messagebox.showwarning("Exportar Turnos", "No se pudieron generar los datos de exportación.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Guardar turnos asignados como CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="turnos_asignados.csv"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Día', 'Recorrido', 'Bloque', 'Inicio', 'Fin', 'Buses', 'Operadores asignados', 'Faltan operadores', 'Observaciones']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)

            messagebox.showinfo("Exportar Turnos", f"Turnos y choferes asignados exportados correctamente a:\n{file_path}")
            self._append_ejecucion("Exportar Turnos", f"Archivo CSV generado: {file_path}")
        except Exception as e:
            messagebox.showerror("Exportar Turnos", f"Error al exportar CSV: {e}")
            self._append_ejecucion("Exportar Turnos - Error", str(e))

    def _append_ejecucion(self, title: str, message: str):
        """Añade una entrada con timestamp a la sección Ejecuciones."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{ts}] {title}\n{message}\n\n"
            self.ejecuciones_text.config(state=tk.NORMAL)
            self.ejecuciones_text.insert(tk.END, entry)
            self.ejecuciones_text.see(tk.END)
            self.ejecuciones_text.config(state=tk.DISABLED)
        except Exception:
            # no bloquear la UI si falla el log visual
            pass
        try:
            self._append_console_log(entry)
        except Exception:
            pass
        try:
            # También persistir en disco para diagnóstico dentro de la carpeta APP
            base = getattr(self, 'app_dir', Path(__file__).resolve().parent)
            logs_dir = base / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / 'ejecuciones.txt'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception:
            pass

    def _show_validation_modal(self, validation_result: dict) -> bool:
        """Muestra un modal con detalles de la validación y sugerencias.

        Retorna True si el usuario decide continuar, False si cancela.
        """
        top = tk.Toplevel(self.root)
        top.title("Validación Paraderos - Detalles")
        top.transient(self.root)
        top.grab_set()
        top.geometry("640x360")

        tk.Label(top, text="Se detectaron inconsistencias entre Rutas y Paraderos.", font=("Inter", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        tk.Label(top, text="Puede continuar y generar la demanda igual, o cancelar para corregir el CSV.", font=("Inter", 10), fg="#5b5b5b").pack(anchor="w", padx=12)

        frame = tk.Frame(top)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        text = tk.Text(frame, wrap=tk.WORD, bd=0, relief=tk.SUNKEN, font=("Inter", 10))
        vs = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=vs.set)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Insert formatted details
        text.insert(tk.END, validation_result.get('report', '') + "\n\n")
        suggestions = validation_result.get('suggestions', {})
        if suggestions:
            text.insert(tk.END, "Sugerencias de coincidencia para valores no encontrados:\n")
            for val, s in suggestions.items():
                text.insert(tk.END, f"- {val}: {', '.join(s) if s else ' (sin sugerencias)'}\n")

        text.config(state=tk.DISABLED)

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=12, pady=(8, 12))

        result = {'continue': False}

        def _on_continue():
            result['continue'] = True
            top.destroy()

        def _on_cancel():
            result['continue'] = False
            top.destroy()

        tk.Button(btn_frame, text="Generar demanda igual", command=_on_continue, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold")).pack(side=tk.RIGHT, padx=6)
        tk.Button(btn_frame, text="Cancelar importación", command=_on_cancel, bg="#ffffff", fg="#ba1a1a", font=("Inter", 10)).pack(side=tk.RIGHT, padx=6)

        self.root.wait_window(top)
        return result['continue']

    def _show_pareto_modal(self, pareto_list: list, default_best: dict | None = None) -> dict | None:
        """Muestra la lista de soluciones Pareto y permite seleccionar una para aplicar.

        Retorna el dict seleccionado o None si se cancela.
        """
        if not pareto_list:
            messagebox.showinfo("Optimización", "No hay soluciones Pareto disponibles.")
            return None

        top = tk.Toplevel(self.root)
        top.title("Frontera Pareto - Seleccione plantilla")
        top.transient(self.root)
        top.grab_set()
        top.geometry("640x360")

        tk.Label(top, text="Seleccione una solución de la frontera Pareto para aplicar:", font=("Inter", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        frame = tk.Frame(top)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        canvas = tk.Canvas(frame)
        vs = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vs.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vs.pack(side=tk.RIGHT, fill=tk.Y)

        sel = tk.IntVar(value=0)
        for idx, p in enumerate(pareto_list):
            txt = f"FT={p['ft']} PT={p['pt']} — Servicio={p['service']*100:.1f}% — Coste={p['cost']:.1f}"
            rb = tk.Radiobutton(inner, text=txt, variable=sel, value=idx, anchor='w', justify='left')
            rb.pack(fill=tk.X, anchor='w', padx=6, pady=2)

        # intentar seleccionar el default_best si está en la lista
        if default_best:
            for i, p in enumerate(pareto_list):
                if p['ft'] == default_best.get('ft') and p['pt'] == default_best.get('pt'):
                    sel.set(i)
                    break

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=12, pady=(8, 12))

        result = {'selected': None}

        def _on_apply():
            idx = int(sel.get())
            result['selected'] = pareto_list[idx]
            top.destroy()

        def _on_cancel():
            result['selected'] = None
            top.destroy()

        tk.Button(btn_frame, text="Aplicar seleccionado", command=_on_apply, bg="#005f7b", fg="#ffffff", font=("Inter", 10, "bold")).pack(side=tk.RIGHT, padx=6)
        tk.Button(btn_frame, text="Cancelar", command=_on_cancel, bg="#ffffff", fg="#ba1a1a", font=("Inter", 10)).pack(side=tk.RIGHT, padx=6)

        self.root.wait_window(top)
        return result['selected']

    def edit_paraderos_map(self):
        """Editor simple para mapear valores de Rutas -> Paraderos y persistir en datos/paraderos_map.json."""
        path = filedialog.askopenfilename(title="Selecciona archivo CSV de Rutas para extraer valores", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        try:
            # Usar el validador para obtener valores faltantes y sugerencias
            v = adapter.validate_routes_vs_paraderos(path)
            missing = [m for m, _ in v.get('missing_values', [])]
            suggestions = v.get('suggestions', {})
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo analizar el CSV: {e}")
            return

        if not missing:
            messagebox.showinfo("Mapeos", "No se detectaron valores no encontrados en el CSV seleccionado.")
            return

        # cargar mapa existente (guardado dentro de la carpeta APP/datos)
        map_file = self.app_dir / 'datos' / 'paraderos_map.json'
        existing = {}
        try:
            if map_file.exists():
                import json
                with open(map_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
        except Exception:
            existing = {}

        top = tk.Toplevel(self.root)
        top.title("Editar mapeos de Paraderos")
        top.transient(self.root)
        top.grab_set()
        top.geometry("760x420")

        tk.Label(top, text=f"Mapear {len(missing)} valores no encontrados", font=("Inter", 12, "bold")).pack(anchor='w', padx=12, pady=(8,4))

        frame = tk.Frame(top)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        canvas = tk.Canvas(frame)
        vs = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vs.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vs.pack(side=tk.RIGHT, fill=tk.Y)

        entries = {}
        for val in missing:
            row = tk.Frame(inner)
            row.pack(fill=tk.X, anchor='w', pady=2)
            tk.Label(row, text=val, width=50, anchor='w').pack(side=tk.LEFT, padx=4)
            sug = suggestions.get(val, [])
            combo_vals = [''] + sug
            cb = ttk.Combobox(row, values=combo_vals, width=40)
            cb.pack(side=tk.LEFT, padx=4)
            # prefill from existing map if present
            mapped = existing.get(val, '')
            if mapped:
                cb.set(mapped)
            entries[val] = cb

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=12, pady=(8,12))

        def _on_save():
            try:
                import json
                map_out = {}
                for orig, widget in entries.items():
                    mapped = widget.get().strip()
                    if mapped:
                        map_out[orig] = mapped
                map_file.parent.mkdir(parents=True, exist_ok=True)
                with open(map_file, 'w', encoding='utf-8') as f:
                    json.dump(map_out, f, ensure_ascii=False, indent=2)
                self._append_ejecucion("Mapeos - Guardados", f"{len(map_out)} mapeos guardados en {map_file}")
                top.destroy()
                messagebox.showinfo("Mapeos", "Mapeos guardados exitosamente.")
            except Exception as e:
                messagebox.showerror("Error guardando", str(e))

        tk.Button(btn_frame, text="Guardar mapeos", command=_on_save, bg="#af101a", fg="#ffffff", font=("Inter", 10, "bold")).pack(side=tk.RIGHT, padx=6)
        tk.Button(btn_frame, text="Cancelar", command=top.destroy, bg="#ffffff", fg="#ba1a1a", font=("Inter", 10)).pack(side=tk.RIGHT, padx=6)

        self.root.wait_window(top)

    def import_paraderos(self):
        path = filedialog.askopenfilename(title="Selecciona archivo CSV de Paraderos TRANSURBAN", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            dst_dir = self.app_dir / 'datos'
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / 'Paraderos TRANSURBAN.csv'
            with open(path, 'rb') as r, open(dst, 'wb') as w:
                w.write(r.read())
            self._write_results(f"Archivo de paraderos importado a {dst}.")
            self._append_ejecucion("Importar Paraderos", f"Paraderos importados desde {Path(path).name}")
            if (self.app_dir / 'datos_rostering' / '.demand_source').exists():
                self._set_state("ready")
            else:
                self._set_state("idle")
        except Exception as e:
            self._set_state("error")
            messagebox.showerror("Error importando paraderos", str(e))

    def import_rutas(self):
        path = filedialog.askopenfilename(title="Selecciona archivo CSV de Rutas (Rutas tiempo frecuencia)", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        self._set_state("running")
        try:
            # Copiar el CSV a una ubicación canónica para trazabilidad
            dst_dir = self.app_dir / 'datos'
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / Path(path).name
            with open(path, 'rb') as r, open(dst, 'wb') as w:
                w.write(r.read())

            self.current_routes_file = dst
            try:
                self.route_schedule = self._load_route_schedule(dst)
            except Exception as e:
                self.route_schedule = []
                try:
                    self._append_ejecucion("Importar Rutas - Cronograma", f"Ruta importada pero no se pudo parsear el cronograma: {e}")
                except Exception:
                    pass

            paraderos_path = self.app_dir / 'datos' / 'Paraderos TRANSURBAN.csv'
            if paraderos_path.exists():
                v = adapter.validate_routes_vs_paraderos(path, paraderos_path)
                try:
                    self._append_ejecucion("Validación Paraderos", v.get('report', ''))
                except Exception:
                    pass
                if v.get('missing_values'):
                    try:
                        proceed = self._show_validation_modal(v)
                    except Exception:
                        proceed = messagebox.askyesno(
                            "Validación Paraderos",
                            f"Se detectaron {len(v.get('missing_values', []))} valores de Origen/Destino no encontrados en {paraderos_path.name}.\nVer detalles en 'Ejecuciones'.\n¿Desea continuar y generar la demanda de todos modos?"
                        )
                    if not proceed:
                        self._set_state("idle")
                        self._write_results("Importación cancelada. Corrige los valores no encontrados o usa el editor de mapeos antes de volver a importar.")
                        self._append_ejecucion("Importar Rutas - Cancelada", "El usuario canceló la importación tras la validación de paraderos.")
                        return
                    else:
                        self._append_ejecucion("Importar Rutas - Continuada", "Se continuará generando demanda pese a las inconsistencias detectadas.")
            else:
                try:
                    self._append_ejecucion("Validación Paraderos - Omitida", f"Archivo {paraderos_path} no encontrado. Se omite validación.")
                except Exception:
                    pass

            block_totals = adapter.aggregate_from_routes_csv(
                path,
                include_reverse=self.include_reverse.get(),
                match_alternate=self.match_alternate.get(),
                turnaround_min=int(self.turnaround.get() or 0),
            )
            out_dir = self.app_dir / 'datos_rostering'
            adapter.generate_demanda_csv(block_totals, dias=28, output_dir=str(out_dir), weekend_factor=float(self.weekend_factor.get() or 1.0))
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / '.demand_source').write_text(
                f'source: transurban_csv\nfile: {Path(path).name}\n', encoding='utf-8'
            )
            self._set_state("ready")
            self._write_results("Demanda generada y precargada desde CSV oficial. Ejecute el motor.")
            try:
                self._append_ejecucion("Importar Rutas", f"Demanda generada desde {Path(path).name} — Totales por bloque: {block_totals}")
            except Exception:
                pass
        except Exception as e:
            self._set_state("error")
            self._append_ejecucion("Importar Rutas - Error", str(e))
            messagebox.showerror(
                "Error importando rutas",
                f"No fue posible leer el CSV de rutas. Asegúrate de que el archivo tenga el formato esperado y columnas como Origen, Destino, Rango_horario, Tiempo_recorrido_estimado_min y Frecuencia_headway_min.\n\nDetalle técnico:\n{e}"
            )

    def execute_planning(self):
        if self.is_running:
            messagebox.showwarning("Ejecutando", "Ya hay un proceso en curso")
            return

        if not (self.app_dir / 'datos_rostering' / '.demand_source').exists():
            messagebox.showwarning("Demanda faltante", "Debe generar demanda oficial desde un CSV antes de planificar")
            self._set_state("idle")
            return

        try:
            n_ft = int(self.num_ft.get())
            n_pt = int(self.num_pt.get())
            n_iter = int(self.max_iter.get())
        except Exception as e:
            messagebox.showerror("Parámetros inválidos", str(e))
            return

        self.is_running = True
        self._set_state("running")
        self.root.update_idletasks()

        threading.Thread(target=self._run_planning_thread, args=(n_ft, n_pt, n_iter), daemon=True).start()

    def _run_planning_thread(self, n_ft, n_pt, n_iter):
        try:
            self._schedule_ui(self._set_progress_message, "Generando plantilla temporal...")
            try:
                generador_rostering.generar_demanda_mensual_24_7(n_ft, n_pt, write_demanda=False)
            except Exception as e:
                try:
                    self._schedule_ui(self._append_ejecucion, "Generar Plantilla", f"Error regenerando plantilla: {e}")
                except Exception:
                    pass

            slots, cond = main_rostering_admm.cargar_datos_rostering()
            estado_final, cob_final = main_rostering_admm.ejecutar_admm_mensual(slots, cond, max_iteraciones=n_iter)
            self.last_roster_state = estado_final
            self.last_roster_coverage = cob_final
            self._schedule_ui(self._refresh_schedule_tab)

            total_slots = len(cob_final)
            covered = sum(1 for c in cob_final.values() if c >= 1)
            missing = total_slots - covered
            service = (covered / total_slots * 100) if total_slots > 0 else 0.0

            report = (
                f"Nivel de servicio: {service:.1f}%\n"
                f"Turnos totales: {total_slots}\n"
                f"Turnos cubiertos: {covered}\n"
                f"Turnos vacíos: {missing}\n"
            )
            self._schedule_ui(self._write_results, report)
            try:
                self._schedule_ui(self._append_ejecucion, "Planificación ADMM", report)
            except Exception:
                pass
            self._schedule_ui(self._set_state, "ready")
        except Exception as e:
            self._schedule_ui(self._set_state, "error")
            try:
                self._schedule_ui(self._append_ejecucion, "Planificación - Error", str(e))
            except Exception:
                pass
            self._schedule_ui(messagebox.showerror, "Error de planificación", str(e))
        finally:
            self.is_running = False

    def optimize_service_cost(self):
        """Busca combinaciones de plantilla (FT/PT) que balanceen nivel de servicio y costo.

        Ejecuta ADMM para combinaciones en una cuadrícula pequeña y presenta la frontera Pareto.
        """
        if self.is_running:
            messagebox.showwarning("Ejecutando", "Ya hay un proceso en curso")
            return

        proceed = messagebox.askyesno("Optimización", "Esto ejecutará múltiples corridas del motor ADMM. Puede tardar varios minutos. ¿Desea continuar?")
        if not proceed:
            return

        try:
            base_ft = int(self.num_ft.get())
            base_pt = int(self.num_pt.get())
            max_iter_opt = max(1, int(self.max_iter.get()))
        except Exception as e:
            messagebox.showerror("Parámetros inválidos", str(e))
            return

        self.is_running = True
        self._set_state("running")
        self.root.update_idletasks()
        threading.Thread(target=self._run_optimization_thread, args=(base_ft, base_pt, max_iter_opt), daemon=True).start()
        return

        # Rango conservador alrededor de los valores actuales
        ft_vals = sorted(set([max(1, base_ft - 5), base_ft, base_ft + 5, base_ft + 10, base_ft + 15, base_ft + 20]))
        pt_vals = sorted(set([max(0, base_pt - 5), base_pt, base_pt + 5, base_pt + 10, base_pt + 15]))

        try:
            for ft, pt in itertools.product(ft_vals, pt_vals):
                self._set_progress_message(f"Optimizando FT={ft} PT={pt}...")
                self._append_ejecucion("Optimización - Inicio prueba", f"FT={ft} PT={pt}")
                # generar plantilla temporal (no altera demanda)
                generador_rostering.generar_demanda_mensual_24_7(ft, pt, write_demanda=False)
                slots, cond = main_rostering_admm.cargar_datos_rostering()
                _, cob = main_rostering_admm.ejecutar_admm_mensual(slots, cond, max_iteraciones=max_iter_opt)
                total_slots = len(cob)
                covered = sum(1 for c in cob.values() if c >= 1)
                service = (covered / total_slots) if total_slots > 0 else 0.0
                self.root.update_idletasks()
                # coste simple: 1.0 por FT, 0.6 por PT (configurable en futuro)
                cost = ft + 0.6 * pt
                results.append({'ft': ft, 'pt': pt, 'service': service, 'cost': cost, 'total_slots': total_slots, 'covered': covered})
                self._append_ejecucion("Optimización - Resultado", f"FT={ft} PT={pt} -> Servicio={service*100:.1f}% Coste={cost:.1f}")

            # calcular frontera Pareto (min cost por mayor service)
            results_sorted = sorted(results, key=lambda r: (r['cost'], -r['service']))
            pareto = []
            best_service = -1.0
            for r in results_sorted:
                if r['service'] > best_service:
                    pareto.append(r)
                    best_service = r['service']

            best_by_ratio = max(results, key=lambda r: (r['service'] / r['cost']) if r['cost'] > 0 else r['service'])
            best_by_service = max(results, key=lambda r: r['service'])

            # construir reporte
            lines = ["Optimización completa. Frontera Pareto (cost -> servicio):"]
            for p in pareto:
                lines.append(f" - FT={p['ft']} PT={p['pt']}: Servicio={p['service']*100:.1f}% Coste={p['cost']:.1f}")

            lines.append("")
            lines.append(f"Mejor candidato por servicio: FT={best_by_service['ft']} PT={best_by_service['pt']} -> Servicio={best_by_service['service']*100:.1f}% Coste={best_by_service['cost']:.1f}")
            if best_by_ratio != best_by_service:
                lines.append(f"Mejor candidato por ratio servicio/coste: FT={best_by_ratio['ft']} PT={best_by_ratio['pt']} -> Servicio={best_by_ratio['service']*100:.1f}% Coste={best_by_ratio['cost']:.1f}")

            if best_by_service['service'] < 0.15:
                lines.append("")
                lines.append("Advertencia: todos los resultados tienen servicio bajo. Considere aumentar la plantilla FT/PT o revisar la demanda/modelo de asignación.")

            report = "\n".join(lines)
            self._write_results(report)
            self._append_ejecucion("Optimización - Resumen", report)

            # mostrar modal para elegir solución Pareto a aplicar
            try:
                chosen = self._show_pareto_modal(pareto, default_best=best_by_service)
            except Exception:
                chosen = None

            if chosen:
                generador_rostering.generar_demanda_mensual_24_7(chosen['ft'], chosen['pt'], write_demanda=False)
                self._append_ejecucion("Optimización - Aplicada", f"Plantilla aplicada: FT={chosen['ft']} PT={chosen['pt']}")
                # recalcular planificación final con iteraciones completas
                self.execute_planning()

        except Exception as e:
            self._append_ejecucion("Optimización - Error", str(e))
            messagebox.showerror("Error en optimización", str(e))
        finally:
            self.is_running = False
            self._set_state("ready")

    def _run_optimization_thread(self, base_ft, base_pt, max_iter_opt):
        ratio_ft = base_ft / max(1, (base_ft + base_pt))
        limite_inf = 10
        limite_sup = base_ft + base_pt + 150
        mejor_solucion = None

        try:
            while limite_inf <= limite_sup:
                total_prueba = (limite_inf + limite_sup) // 2
                ft_prueba = int(total_prueba * ratio_ft)
                pt_prueba = total_prueba - ft_prueba

                self._schedule_ui(
                    self._set_progress_message,
                    f"Buscando óptimo... Probando con {total_prueba} conductores ({ft_prueba} FT, {pt_prueba} PT)"
                )

                generador_rostering.generar_demanda_mensual_24_7(ft_prueba, pt_prueba, write_demanda=False)
                ids_c, ids_v, costos_b, df_v = cargar_datos_proyecto()

                motor = main_rostering_admm.MotorADMMTransUrban(ids_c, ids_v, costos_b, df_v)
                main_rostering_admm.CONFIG["max_iteraciones"] = max_iter_opt
                motor.optimizar()

                stats = motor.calcular_kpis()
                cobertura = stats.get('cobertura', 0)

                if cobertura >= 99.0:
                    mejor_solucion = (ft_prueba, pt_prueba)
                    limite_sup = total_prueba - 1
                else:
                    limite_inf = total_prueba + 1

            if mejor_solucion:
                self._schedule_ui(self.ft_var.set, mejor_solucion[0])
                self._schedule_ui(self.pt_var.set, mejor_solucion[1])
                self._schedule_ui(self.ejecutar_optimizacion_admm_en_fondo)
            else:
                self._schedule_ui(
                    messagebox.showwarning,
                    "Demanda demasiado alta",
                    "No se encontró una solución con al menos 99.0% de cobertura."
                )

        except Exception as e:
            self._schedule_ui(self._append_ejecucion, "Optimización - Error", str(e))
            self._schedule_ui(messagebox.showerror, "Error en optimización", str(e))
        finally:
            self.is_running = False
            self._schedule_ui(self._set_state, "ready")

    def ejecutar_optimizacion_admm_en_fondo(self):
        # Leer valores de los sliders
        num_ft = self.ft_var.get()
        num_pt = self.pt_var.get()
        
        self._schedule_ui(self._append_ejecucion, "ADMM", f"🚀 Generando plantilla con {num_ft} FT y {num_pt} PT...")
        
        # 1. Generar la plantilla nueva
        import generador_rostering
        generador_rostering.generar_demanda_mensual_24_7(num_ft, num_pt, write_demanda=False)
        
        # 2. Lanzar el hilo (Daemon)
        threading.Thread(target=self._tarea_trabajador_admm, daemon=True).start()

    def _build_admm_controls(self, parent):
        """Añade el botón de acceso al motor ADMM al panel izquierdo"""
        # Creamos un contenedor para el botón al final del panel
        admm_container = tk.Frame(parent, bg=parent.cget('bg'))
        admm_container.pack(side="bottom", fill="x", padx=15, pady=20)

        # Botón con estilo para abrir el modal
        self.btn_abrir_admm = ttk.Button(
            admm_container, 
            text="🚀 Configurar Motor ADMM", 
            command=self._show_admm_modal
        )
        self.btn_abrir_admm.pack(fill="x", ipady=5)

    def _show_admm_modal(self):
        """Crea la ventana flotante para el Motor ADMM"""
        # Crear ventana secundaria
        self.admm_window = tk.Toplevel(self.root)
        self.admm_window.title("Panel de Control TransUrban ADMM")
        self.admm_window.geometry("420x280")
        self.admm_window.resizable(False, False)
        
        # Bloquear la ventana principal hasta que se cierre esta
        self.admm_window.transient(self.root)
        self.admm_window.grab_set()

        # Centrar la ventana respecto a la principal
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 140
        self.admm_window.geometry(f"+{int(x)}+{int(y)}")

        # --- Interfaz de la Ventana ---
        tk.Label(self.admm_window, text="⚙️ Optimización de Rostering", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
        tk.Label(self.admm_window, text="Ajuste la plantilla para el cálculo final", font=("Segoe UI", 9)).pack(pady=(0, 10))

        # Sliders
        f_sliders = tk.Frame(self.admm_window)
        f_sliders.pack(fill="x", padx=30)

        # Full-Time
        tk.Label(f_sliders, text="Full-Time:").grid(row=0, column=0, sticky="w", pady=5)
        self.ft_var = tk.IntVar(value=250)
        ttk.Scale(f_sliders, from_=100, to_=400, variable=self.ft_var, orient="horizontal").grid(row=0, column=1, sticky="ew", padx=10)
        tk.Label(f_sliders, textvariable=self.ft_var, width=4).grid(row=0, column=2)

        # Part-Time
        tk.Label(f_sliders, text="Part-Time:").grid(row=1, column=0, sticky="w", pady=5)
        self.pt_var = tk.IntVar(value=150)
        ttk.Scale(f_sliders, from_=50, to_=300, variable=self.pt_var, orient="horizontal").grid(row=1, column=1, sticky="ew", padx=10)
        tk.Label(f_sliders, textvariable=self.pt_var, width=4).grid(row=1, column=2)
        f_sliders.columnconfigure(1, weight=1)

        # Botón Ejecutar
        self.admm_btn_run = ttk.Button(self.admm_window, text="▶️ Lanzar Optimización Final", command=self._preparar_y_ejecutar_admm)
        self.admm_btn_run.pack(fill="x", padx=30, pady=15)

        # Progreso y Estado
        self.admm_progress = ttk.Progressbar(self.admm_window, orient="horizontal", mode="determinate")
        self.admm_progress.pack(fill="x", padx=30)

        self.admm_status_label = tk.Label(self.admm_window, text="Estado: Esperando comando...", font=("Segoe UI", 8, "italic"))
        self.admm_status_label.pack(pady=5)

    def _preparar_y_ejecutar_admm(self):
        """Prepara el motor y actualiza la UI del modal"""
        self.admm_btn_run.config(state="disabled")
        self.admm_status_label.config(text="⚙️ Procesando ADMM... (Mantenga esta ventana abierta)", fg="#af101a")
        
        # Llamar a tu función que maneja el hilo (threading)
        self.ejecutar_optimizacion_admm_en_fondo()

    def _tarea_trabajador_admm(self):
        """Trabajo pesado: Carga, Optimiza y Exporta"""
        try:
            from Loader import cargar_datos_proyecto
            from main_rostering_admm import MotorADMMTransUrban
            
            # 1. Cargar datos (los que generaste con el Pareto)
            ids_c, ids_v, costos_b, df_v = cargar_datos_proyecto()
            
            # 2. Configurar y correr el motor
            motor = MotorADMMTransUrban(ids_c, ids_v, costos_b, df_v)
            motor.optimizar() # Esto tomará unos minutos
            
            # 3. Guardar resultados
            motor.exportar_resultados_csv()
            stats = motor.calcular_kpis()
            
            # --- NUEVO: CONECTAR AL FRONTEND ---
            
            # Adaptar los resultados del motor ADMM al formato que la UI espera
            # La UI espera que self.last_roster_state tenga el formato de datos por día y bloque.
            # Convertimos rutas_actuales (que tiene IDs como 'D1_B2_04_08_Bus1')
            roster_adaptado = {}
            for conductor, viajes in motor.rutas_actuales.items():
                bloques_dia = {}
                for viaje_id in viajes:
                    partes = viaje_id.split('_')
                    if len(partes) >= 2:
                        dia = int(partes[0].replace('D', ''))
                        bloque = int(partes[1].replace('B', ''))
                        bloques_dia.setdefault(dia, []).append(bloque)
                
                tipo = "Full-Time" if conductor.startswith("FT") else "Part-Time"
                roster_adaptado[conductor] = {
                    'tipo': tipo,
                    'bloques_por_dia': bloques_dia,
                    'slots_asignados': list(viajes)
                }

            self.last_roster_state = roster_adaptado
            
            # Adaptamos el consenso global (viajes cubiertos) para las métricas
            self.last_roster_coverage = motor.consenso_global
            
            # Crear reporte para la pestaña de Resultados
            reporte_texto = (
                f"✅ OPTIMIZACIÓN ADMM FINALIZADA\n\n"
                f"Resultados Globales:\n"
                f" - Cobertura del Sistema: {stats['cobertura']:.1f}%\n"
                f" - Conflictos restantes: {stats['conflictos']}\n"
                f" - Conductores utilizados: {len(motor.rutas_actuales)}\n"
                f" - Viajes procesados: {len(motor.viajes)}\n\n"
                f"El Roster final ha sido exportado a 'datos_rostering/ROSTER_FINAL_TRANSURBAN.csv'.\n"
                f"Revise la pestaña 'Cronograma' para ver las asignaciones diarias detalladas."
            )

            # Enviar actualizaciones a la UI
            self._schedule_ui(self._write_results, reporte_texto)
            self._schedule_ui(self._refresh_schedule_tab)
            self._schedule_ui(self._set_state, "ready")

            conductor_keys = sorted(roster_adaptado.keys())
            if conductor_keys and hasattr(self, 'driver_view_combobox'):
                self._schedule_ui(self.driver_view_combobox.config, values=conductor_keys)
                self._schedule_ui(self.driver_view_var.set, conductor_keys[0])
                self._schedule_ui(self._update_driver_view)
            
            self._schedule_ui(self._append_ejecucion, "ÉXITO", f"✅ Roster generado: {stats['cobertura']:.1f}% cobertura.")
            self._schedule_ui(messagebox.showinfo, "TransUrban", "¡Optimización ADMM terminada y resultados cargados en la interfaz!")

        except Exception as e:
            self._schedule_ui(self._set_state, "error")
            self._schedule_ui(self._append_ejecucion, "ERROR", f"❌ Error en ADMM: {str(e)}")
            import traceback
            traceback.print_exc()


# ==========================================
# PUNTO DE ENTRADA BLINDADO
# ==========================================
if __name__ == '__main__':
    print("Paso 1: Entrando al bloque main...")
    try:
        import tkinter as tk
        from tkinter import messagebox
        print("Paso 2: Tkinter importado. Creando ventana...")
        
        root = tk.Tk()
        print("Paso 3: Ventana base creada. Cargando la App...")
        
        # ¡AQUÍ USAMOS EL NOMBRE REAL DE TU CLASE!
        app = TransurbanPlanningApp(root) 
        
        print("Paso 4: App cargada en memoria. Iniciando motor gráfico...")
        root.mainloop()
        
    except Exception as e:
        print("\n❌ ¡ERROR FATAL DETECTADO! ❌")
        import traceback
        traceback.print_exc()
    
    # Esto evitará que la consola parpadee y se cierre
    input("\nPresiona ENTER para cerrar la terminal...")
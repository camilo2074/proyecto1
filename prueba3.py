import asyncio, threading, tempfile, os
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk

from pybricksdev.ble import find_device
from pybricksdev.connections.pybricks import PybricksHubBLE



# -------------------- PROGRAMA ENVIADO AL HUB -------------------- 

def create_program(comando: str) -> str:
    actions = {
        "rojo": """
if motorB.angle() != 0:
    motorB.run_target(600, 0)
motorA.run_angle(600, -180)

""",
        "azul": """
        
if motorB.angle() != 180:
    motorB.run_target(600, 180)
motorA.run_angle(600,-180)

""",

        "amarillo": """    
if motorC.angle() != 180:
    motorC.run_target(600, 180)
motorA.run_angle(600, 180)

""",

        "verde": """
if motorC.angle() != 0:
    motorC.run_target(600, 0)
motorA.run_angle(600, 180)

""",

        "Leer": """
sensor = ColorSensor(Port.B)
do{
    color=sensor.color()
}while color==None
print(color)
"""
    }
    if comando == "auto":
        with open("automatico.py", "r", encoding="utf-8") as f:
            return f.read() 
    else:
        drive_code = actions.get(comando, "")
        code= f"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()

motorA = Motor(Port.A)
motorB = Motor(Port.F)
motorC = Motor(Port.E)
{drive_code}

wait(500)
print("Comando '{comando}' ejecutado.")
        """
        return code

async def execute_command(worker, comando: str, log_cb=None):
    program = create_program(comando)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
        tf.write(program)
        temp_path = tf.name

    try:
        if log_cb:
            log_cb(f"Ejecutando: {comando}")
        # Para recibir datos, print_output debe ser True
        if "Leer" in comando:
            try:
                color=await worker.hub.run(temp_path, wait=True)
                color_str = color.strip().lower()
                worker.log(f"Color detectado: {color_str}")
                if worker.color_canvas:
                    worker.color_canvas.configure(bg=color_str)
                if worker.color_label:
                    worker.color_label.configure(text=f"Color detectado: {color_str}")
            except Exception as e:
                worker.log(f"Error leyendo color: {e}")
        else:
            await worker.hub.run(temp_path, wait=True, print_output=True)

        #await hub.run(temp_path, wait=True, print_output=True)
        if log_cb:
            log_cb(f"Ejecutado: {comando}")


    except Exception as e:
        if log_cb:
            log_cb(f"Error ejecutando comando: {e}")

    finally:
        try:
            os.unlink(temp_path)
        except:
            pass



# -------------------- WORKER BLE -------------------- 
#conexion
class BLEWorker:
    def __init__(self, log_queue: Queue, color_canvas=None, color_label=None):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.queue = None
        self.hub = None
        self.running = threading.Event()
        self.log_queue = log_queue
        self.color_canvas = color_canvas
        self.color_label = color_label
    
    def _create_loop_and_thread(self):
        """Crea un nuevo event loop y un nuevo hilo."""
        self.running.clear()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.queue = None
        self.hub = None

    def log(self, msg: str):
        self.log_queue.put(msg)

    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        self.loop.create_task(self._runner())
        self.loop.run_forever()

    async def abort_action(self):
        try:
            await self.hub.stop()
            print("✅ Acción abortada.")
        except Exception as e:
            print(f"⚠️ Error al abortar: {e}")

    async def _runner(self):
        try:
            self.log("Buscando hub Bluetooth…")
            device = await find_device("sp2")
            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            self.log("Conectado al Hub.")
            self.running.set()

            while True:
                comando = await self.queue.get()
                await execute_command(self, comando, self.log) 

        except asyncio.CancelledError:
            self.log("Tarea cancelada.")
        except asyncio.TimeoutError:
            self.log("Error: tiempo de espera agotado al buscar el hub.")
        except Exception as e:
            self.log(f"Error en worker: {e}")
        finally:
            if self.hub:
                try:
                    await self.hub.disconnect()
                    self.log("Hub desconectado.")
                except Exception as e:
                    self.log(f"Error al desconectar: {e}")
            self.running.clear()

    def start(self):
        try:
            # Si el thread no existe o ya murió → crear uno nuevo
            if not self.thread.is_alive():
                self._create_loop_and_thread()

            self.thread.start()

        except RuntimeError as e:
            if not "threads can only be started once" in str(e):
            # Error típico: "threads can only be started once"
                self.log(f"Error al iniciar el worker: {e}")

            # Intentar recuperarse automáticamente:
            self._create_loop_and_thread()
            self.thread.start()

        except Exception as e:
            # Cualquier otro error inesperado
            self.log(f"Error inesperado en start(): {e}")

    def stop(self):
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, comando: str):
        if self.loop.is_running() and self.queue is not None:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, comando)

# -------------------- GUI -------------------- 

class LegoGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Control LEGO – Motores A/B/C")
        self.root.geometry("700x600")

        self.log_queue = Queue()
        self._build_ui()
        self.worker = BLEWorker(self.log_queue, self.color_canvas, self.color_label)
        self._poll_logs()

    def _build_ui(self):
        
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill='x')

        ttk.Button(top, text="Conectar", command=self.on_connect).pack(side='left', padx=5)
        ttk.Button(top, text="Desconectar", command=self.on_disconnect).pack(side='left', padx=5)

        self.status = ttk.Label(top, text="Estado: sin conexión")
        self.status.pack(side='right')

        body = ttk.Frame(self.root, padding=20)
        body.pack(fill='both', expand=True)

        # -------- BOTONES NUEVOS -----------------------------------------
               # --- Main body (2 columnas) ---

        label_titulo = tk.Label(body, text="COLOR DETECTADO", font=("Arial", 14, "bold"), bg="gray", fg="white")
        label_titulo.pack(fill="x", pady=(10, 5))


        # Visual de color (un canvas cuadrado)
        self.color_canvas = tk.Canvas(body,height=100, bg="#ffffff", bd=2, relief="sunken")
        self.color_canvas.pack(pady=6,padx=100,fill='x')
        # texto que muestra el nombre del color
        self.color_label = ttk.Label(body, text="No detectado", font=("Helvetica", 12, "bold"))
        self.color_label.pack(pady=(6, 12))
        # Frame para los botones
        lbl_motores = ttk.Label(body, text="Control de Motores", style="Small.TLabel")
        lbl_motores.pack()
        
        Frame_btn = ttk.Frame(body, padding=20)
        Frame_btn.pack(fill='both', expand=True)
        btn_coman=[
            ("🔴 ROJO\n(A→ +180°, B→0°)","#d9534f","white","#b94a42",lambda: self.worker.send_command("rojo"),0,0),
            ("🔵 AZUL\n(A→ +180°, B→180°)","#0275d8","white","#025aa5",lambda: self.worker.send_command("azul"),0,1),
            ("🟡 AMARILLO\n(A→ -180°, C→0°)","#f0ad4e","black","#d08b36",lambda: self.worker.send_command("amarillo"),0,2),
            ("🟢 VERDE\n(A→ -180°, C→180°)","#5cb85c","white","#4cae4c",lambda: self.worker.send_command("verde"),0,3),
            ("LEER COLOR","#00e1ff","black","#0093a7",lambda: self.worker.send_command("Leer"),1,0),
            ("AUTOMATICO","#00e1ff","black","#0093a7",lambda: self.worker.send_command("auto"),1,1),
            ("ABORTAR ACCION","#00e1ff","black","#0093a7",lambda: self.worker.abort_action(),1,2),
            ("SALIR","#00e1ff","black","#0093a7",self.root.quit,1,3)
        ]
        
        
        #botones de ventana menu
        for texto, fondo, clrFuente, fondoActivado, accion, fila, columna in btn_coman:
            btn = tk.Button(Frame_btn, text=texto, width=18, height=3,
                             bg=fondo, fg=clrFuente, activebackground=fondoActivado,
                             command=accion)
            btn.grid(row=fila, column=columna, padx=10, pady=10, sticky="nsew")
        # --------- LOG ---------

        logf = ttk.Labelframe(body, text="Registro")
        logf.pack(fill='both', expand=True, padx=10, pady=10)

        self.log_text = tk.Text(logf, height=7, wrap='word')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.configure(state='disabled')

    # -------- Conexión --------

    def on_connect(self):
        self.status.configure(text="Estado: conectando…")
        self.worker.start()
        
        def wait_ready():
            if self.worker.running.is_set():
                self.status.configure(text="Estado: conectado")
            else:
                self.root.after(200, wait_ready)

        wait_ready()

    def on_disconnect(self):
        self.worker.stop()
        self.status.configure(text="Estado: sin conexión")
        self._log("Desconectado.")

    # -------- Logs --------

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert('end', msg + "\n")
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
        except Empty:
            pass

        self.root.after(150, self._poll_logs)


def main():
    root = tk.Tk()
    app = LegoGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()


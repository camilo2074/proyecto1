import asyncio, threading, tempfile, os
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk
import sys
import io
from pybricksdev.ble import find_device
from pybricksdev.connections.pybricks import PybricksHubBLE



# -------------------- PROGRAMA ENVIADO AL HUB --------------------     

def create_program(comando: str) -> str:
    actions = {
        "verde": """
target_B = 0
current_B = motorB.angle()
diff_B = (target_B - current_B) % 360
if diff_B > 180:
    diff_B = diff_B - 360
if abs(diff_B) > TOLERANCE:
    motorB.run_target(600, target_B)
motorA.run_angle(600, -180)
""",
        "amarillo": """
target_B = 180
current_B = motorB.angle()
diff_B = (target_B - current_B) % 360
if diff_B > 180:
    diff_B = diff_B - 360
if abs(diff_B) > TOLERANCE:
    motorB.run_target(600, target_B)
motorA.run_angle(600,-180)
""",
        "azul": """
target_C = 180
current_C = motorC.angle()
diff_C = (target_C - current_C) % 360
if diff_C > 180:
    diff_C = diff_C - 360
if abs(diff_C) > TOLERANCE:
    motorC.run_target(600, target_C)
motorA.run_angle(600, 180)
""",

        "rojo": """
target_C = 0
current_C = motorC.angle()
diff_C = (target_C - current_C) % 360
if diff_C > 180:
    diff_C = diff_C - 360
if abs(diff_C) > TOLERANCE:
    motorC.run_target(600, target_C)
motorA.run_angle(600, 180)
""",

        "Leer": """
sensor = ColorSensor(Port.B)
color = sensor.color()
print(color)
""",

        "Eliminar": """
motorA.run_angle(100, 180)
#motorA.track_target(motorA.angle()-180)
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
TOLERANCE = 20
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
        # Para recibir datos, capturar el output impreso
        if "Leer" in comando:
            try:
                # Redirigir stdout para capturar lo que imprime hub.run()
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                
                try:
                    await worker.hub.run(temp_path, wait=True, print_output=True)
                    color_output = sys.stdout.getvalue()
                finally:
                    sys.stdout = old_stdout
                
                # Parsear la salida para extraer el color
                lines = color_output.strip().split('\n')
                color_str = ""
                for line in lines:
                    if "Color." in line:
                        color_str = line.strip()
                        break
                
                if color_str:
                    # Extraer el nombre del color: "Color.YELLOW" -> "yellow"
                    if "Color." in color_str:
                        color_name = color_str.split("Color.")[1].lower()
                    else:
                        color_name = color_str.lower()
                else:
                    color_name = "desconocido"
                
                worker.log(f"Color detectado: {color_name}")
                if worker.color_canvas:
                    worker.color_canvas.configure(bg=color_name)
                if worker.color_label:
                    worker.color_label.configure(text=f"Color detectado: {color_name}")
                
            except Exception as e:
                worker.log(f"Error leyendo color: {e}")
        else:
            await worker.hub.run(temp_path, wait=True, print_output=True)
            worker.color_canvas.configure(bg="#ffffff")
            worker.color_label.configure(text=f"Color detectado: No detectado")


        #await hub.run(temp_path, wait=True, print_output=True)
        if log_cb:
            log_cb(f"Tarea: {comando}")


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
        #Crea un nuevo event loop y un nuevo hilo.
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

        # -------- BOTONES -----------------------------------------

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
            ("ROJO","#d9534f","white","#b94a42",lambda: self.worker.send_command("rojo")),
            ("AZUL","#0275d8","white","#025aa5",lambda: self.worker.send_command("azul")),
            ("AMARILLO","#f0ad4e","black","#d08b36",lambda: self.worker.send_command("amarillo")),
            ("VERDE","#5cb85c","white","#4cae4c",lambda: self.worker.send_command("verde")),
            ("LEER COLOR","#00e1ff","black","#0093a7",lambda: self.worker.send_command("Leer")),
            ("AUTOMATICO","#00e1ff","black","#0093a7",lambda: self.worker.send_command("auto")),
            ("ELIMNIAR PIEZA","#00e1ff","black","#0093a7",lambda: self.worker.send_command("Eliminar")),
            ("SALIR","#00e1ff","black","#0093a7",self.root.quit)
        ]

        #botones de ventana menu
        fila=0
        columna=0
        for texto, fondo, clrFuente, fondoActivado, accion in btn_coman:
            if columna==4:
                columna=0
                fila+=1
            btn = tk.Button(Frame_btn, text=texto, width=18, height=3,
                             bg=fondo, fg=clrFuente, activebackground=fondoActivado,
                             command=accion)
            btn.grid(row=fila, column=columna, padx=10, pady=10, sticky="nsew")
            columna+=1
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


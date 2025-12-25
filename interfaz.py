from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk
from pybricksdev.ble import find_device
from pybricksdev.connections.pybricks import PybricksHubBLE
import BLEWorker


# -------------------- GUI -------------------- 

class LegoGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Control LEGO – Motores A/B/C")
        self.root.geometry("700x600")

        self.log_queue = Queue()
        self._build_ui()
        self.worker = BLEWorker.BLEWorker(self.log_queue, self.color_canvas, self.color_label)
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
            ("AUTOMÁTICO","#00e1ff","black","#0093a7",lambda: self.worker.send_command("auto")),
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


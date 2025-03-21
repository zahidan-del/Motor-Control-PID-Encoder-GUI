import customtkinter as ctk
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time

class PIDControllerApp(ctk.CTk):
    def _init_(self):
        super()._init_()
        self.title("PID Controller GUI")
        self.geometry("1200x1000")
        self.start_time = None
        self.serial_port = None
        self.stop_thread = False
        self.target_rpm = 0
        self.current_line = ""
        self.rpm_data = []
        self.time_data = []
        self.stable_start_time = None  # Waktu mulai stabil
        self.settling_time = 0  # Nilai settling time terakhir
        self.in_tolerance = False  # Status apakah dalam toleransi
        self.settling_calculated = False  # Apakah settling time sudah dihitung

        # Frame kiri (Kontrol)
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        self.create_frame_pid(left_frame)
        self.create_frame_motor(left_frame)
        self.create_frame_com(left_frame)
        self.create_frame_parameters(left_frame)

        # Frame Kanan (Grafik)
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.figure = Figure(figsize=(9, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Grafik RPM Motor")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("RPM")
        self.canvas = FigureCanvasTkAgg(self.figure, master=right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # Frame kontrol PID
    def create_frame_pid(self, parent):
        pid_frame = ctk.CTkFrame(parent)
        pid_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(pid_frame, text="Kontrol PID", font=("Bahnschrift", 18, "bold"),
                     text_color="White", fg_color="#3b8ed0", corner_radius=15).grid(row=0, column=0, padx=5, pady=5)

        for i, param in enumerate(["Kp ", "Ki ", "Kd "]):
            ctk.CTkLabel(pid_frame, text=f"{param}:").grid(row=i + 1, column=0, padx=5, pady=5)
            entry = ctk.CTkEntry(pid_frame, width=140)
            entry.grid(row=i + 1, column=1, padx=5, pady=5)
            ctk.CTkButton(
                pid_frame, text=f"Kirim {param}", command=lambda p=param, e=entry: self.send_data(f"{p}:{e.get()}")
            ).grid(row=i + 1, column=2, padx=5, pady=5)

    # Frame kontrol motor
    def create_frame_motor(self, parent):
        motor_frame = ctk.CTkFrame(parent)
        motor_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(motor_frame, text="Kontrol Motor", font=("Bahnschrift", 15, "bold"),
                     text_color="White", fg_color="#3b8ed0", corner_radius=15).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(motor_frame, text="Target RPM :").grid(row=1, column=0, padx=5, pady=5)
        self.rpm_entry = ctk.CTkEntry(motor_frame, width=140)
        self.rpm_entry.grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(motor_frame, text="Kirim RPM", command=self.send_rpm).grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(motor_frame, text="Arah :").grid(row=2, column=0, padx=5, pady=5)
        self.direction_combobox = ctk.CTkComboBox(motor_frame, values=["CW", "CCW", "S"])
        self.direction_combobox.grid(row=2, column=1, padx=5, pady=5)
        self.direction_combobox.set("")
        (ctk.CTkButton(motor_frame, text="Tentukan arah", command=self.set_direction).grid
                                    (row=2, column=2, padx=5, pady=5))

    # Frame port COM
    def create_frame_com(self, parent):
        com_frame = ctk.CTkFrame(parent)
        com_frame.pack(pady=10, padx=10, fill="x")

        (ctk.CTkLabel(com_frame, text="Port COM", font=("Bahnschrift", 15, "bold"),
                     text_color="White", fg_color="#3b8ed0", corner_radius=15).grid
                    (row=0, column=0, padx=5, pady=5, sticky="w"))
        self.combobox = ctk.CTkComboBox(com_frame, values=self.get_com_ports())
        self.combobox.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.combobox.set("")
        self.connect_button = ctk.CTkButton(com_frame, text="Connect", command=self.connect_serial)
        self.connect_button.grid(row=1, column=1, padx=5, pady=5)
        self.disconnect_button = ctk.CTkButton(com_frame, text="Disconnect",
                                               command=self.disconnect_serial, state="disabled")
        self.disconnect_button.grid(row=1, column=2, padx=5, pady=5)

    # Frame parameters
    def create_frame_parameters(self, parent):
        parameters_frame = ctk.CTkFrame(parent)
        parameters_frame.pack(pady=10, padx=10, fill="x")

        (ctk.CTkLabel(parameters_frame, text="Parameters", font=("Bahnschrift", 15, "bold"),
                     text_color="White", fg_color="#3b8ed0", corner_radius=15).grid
                    (row=0, column=0, padx=5, pady=5, sticky="w"))

        self.parameter_labels = {}
        parameter_names = ["Peak Time", "Rise Time", "Overshoot", "Settling Time", "Steady State", "Error"]

        for i, param in enumerate(parameter_names):
            ctk.CTkLabel(parameters_frame, text=f"{param}:").grid(row=i + 1, column=0, padx=5, pady=5, sticky="w")
            label = ctk.CTkLabel(parameters_frame, text="-")
            label.grid(row=i + 1, column=1, padx=5, pady=5, sticky="w")
            self.parameter_labels[param] = label

    #Fungsi pada port COM
    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect_serial(self):
        port = self.combobox.get()
        if port:
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.connect_button.configure(state="disabled")
                self.disconnect_button.configure(state="normal")
                self.start_reading()
            except Exception as e:
                ctk.CTkMessagebox.show_error(title="Connection Error", message=f"Failed to connect: {e}")

    def disconnect_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.stop_thread = True
            self.serial_port.close()
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write(f"{data}\n".encode())
            print(f"Debug: Sent data -> {data}")  # Debug log

    #Fungsi RPM
    def send_rpm(self):
        self.target_rpm = float(self.rpm_entry.get())
        self.send_data(f"RPM:{self.target_rpm}")

    #Fungsi arah
    def set_direction(self):
        direction = self.direction_combobox.get()
        if direction:
            self.send_data(f"DIR:{direction}")

    #Pembacaan input
    def start_reading(self):
        self.stop_thread = False
        threading.Thread(target=self.read_serial_data, daemon=True).start()

    def read_serial_data(self):
        while not self.stop_thread:
            if self.serial_port and self.serial_port.is_open:
                line = self.serial_port.readline().decode().strip()
                self.current_line = line  # Simpan data terbaru
                print(f"Debug: Received line: {line}")  # Tambahkan debug log

                if line.startswith("RPM:") and self.target_rpm > 0 and self.direction_combobox.get():
                    try:
                        rpm = float(line.split(":")[1])

                        # Inisialisasi waktu mulai jika belum dilakukan
                        if self.start_time is None:
                            self.start_time = time.time()

                        # Hitung waktu relatif
                        elapsed_time = time.time() - self.start_time
                        print(f"Debug: Parsed RPM={rpm}, Time={elapsed_time}")  # Debug log parsing data
                        self.rpm_data.append(rpm)
                        self.time_data.append(elapsed_time)

                        # Batasi jumlah data untuk grafik
                        if len(self.rpm_data) > 1000:
                            self.rpm_data.pop(0)
                            self.time_data.pop(0)

                        # Perbarui grafik dan hitung parameter
                        self.after(0, self.update_graph)
                        self.after(0, self.calculate_parameters)
                    except ValueError:
                        print("Debug: Error parsing RPM value")  # Log jika parsing gagal

    def calculate_parameters(self):
        if self.current_line.startswith("RPM:") and self.target_rpm > 0 and self.direction_combobox.get():
            max_rpm = max(self.rpm_data)
            overshoot = ((max_rpm - self.target_rpm) / self.target_rpm) * 100
            steady_state = self.rpm_data[-1]
            peak_time = self.time_data[self.rpm_data.index(max_rpm)]
            rise_time = next((t for r, t in zip(self.rpm_data, self.time_data) if r >= self.target_rpm), 0)
            error = abs(self.target_rpm - steady_state) / self.target_rpm * 100 if self.target_rpm != 0 else 0

            # Toleransi 5% dari target RPM
            tolerance = 0.05 * self.target_rpm

            if abs(steady_state - self.target_rpm) <= tolerance:
                if not self.in_tolerance:
                    # Baru masuk toleransi, mulai hitung waktu stabil
                    self.stable_start_time = time.time()
                    self.in_tolerance = True
                    self.settling_calculated = False  # Reset flag saat masuk toleransi
                elif time.time() - self.stable_start_time >= 5 and not self.settling_calculated:
                    # Stabil selama 5 detik, hitung settling time hanya sekali
                    self.settling_time = self.time_data[-1]
                    self.settling_calculated = True
            else:
                # Keluar dari toleransi, reset status stabil
                self.in_tolerance = False
                self.stable_start_time = None
                self.settling_calculated = False

            # Perbarui label
            self.parameter_labels["Peak Time"].configure(text=f"{peak_time:.2f} s")
            self.parameter_labels["Rise Time"].configure(text=f"{rise_time:.2f} s")
            self.parameter_labels["Overshoot"].configure(text=f"{overshoot:.2f} %")
            self.parameter_labels["Settling Time"].configure(text=f"{self.settling_time:.2f} s")
            self.parameter_labels["Steady State"].configure(text=f"{steady_state:.2f} RPM")
            self.parameter_labels["Error"].configure(text=f"{error:.2f} %")

            

    # Update Grafik
    def update_graph(self):
        self.ax.clear()
        self.ax.plot(self.time_data, self.rpm_data, label="RPM", color="blue")
        self.ax.axhline(self.target_rpm, linestyle="--", label="Target RPM", color="green")
        if len(self.rpm_data) == len(self.time_data):  # Ensure the data is synced
            error = [(abs(self.target_rpm - rpm) / self.target_rpm) * 100
                     if self.target_rpm != 0 else 0 for rpm in self.rpm_data]
            self.ax.plot(self.time_data, error, label="Error", color="red")
        self.ax.set_title("Motor RPM and Error Signal")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("RPM / Error")
        self.ax.grid(True)
        self.ax.set_ylim(bottom=0)
        self.ax.legend()

        # Hitung lagi parameters
        self.calculate_parameters()

        self.canvas.draw()

if _name_ == "_main_":
    ctk.set_appearance_mode("Light")
    app = PIDControllerApp()
    app.mainloop()
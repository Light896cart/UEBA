"""Вкладка сбора данных"""
import customtkinter as ctk
import threading
import time
import os
import sys

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class CollectTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.is_running = False
        self.worker_thread = None
        self._build_ui()

    def _build_ui(self):
        # Заголовок
        ctk.CTkLabel(
            self,
            text="📥 Сбор данных",
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(anchor="w", pady=(0, 20))

        # Настройки
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            settings_frame,
            text="⚙️ Настройки сбора",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Интервал
        interval_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        interval_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(interval_frame, text="Интервал сбора (сек):").pack(side="left")
        self.interval_entry = ctk.CTkEntry(interval_frame, width=100)
        self.interval_entry.insert(0, "60")
        self.interval_entry.pack(side="left", padx=10)

        # Длительность
        duration_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        duration_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(duration_frame, text="Длительность (часов):").pack(side="left")
        self.duration_entry = ctk.CTkEntry(duration_frame, width=100)
        self.duration_entry.insert(0, "1")
        self.duration_entry.pack(side="left", padx=10)

        ctk.CTkLabel(
            duration_frame,
            text="(Для теста достаточно 1 часа. Для реального обучения — 24 часа)",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=10)

        # Кнопки управления
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=20)

        self.start_btn = ctk.CTkButton(
            buttons_frame,
            text="▶️ Начать сбор",
            command=self.start_collection,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            height=40,
            width=150
        )
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(
            buttons_frame,
            text="⏹️ Остановить",
            command=self.stop_collection,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40,
            width=150,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)

        # Статистика
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            stats_frame,
            text="📊 Статистика сбора",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="Собрано строк: 0\nВремя работы: 00:00:00",
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        self.stats_label.pack(anchor="w", padx=20, pady=10)

        # Лог
        self.log_text = ctk.CTkTextbox(stats_frame, height=200)
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def start_collection(self):
        if self.is_running:
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.app.set_status("Сбор данных...", "#2ecc71")
        self.log(f"[{time.strftime('%H:%M:%S')}] Сбор данных запущен")

        # Запускаем в отдельном потоке
        self.worker_thread = threading.Thread(target=self._collection_worker, daemon=True)
        self.worker_thread.start()

        # Запускаем обновление статистики
        self._update_stats()

    def stop_collection(self):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.app.set_status("Готов", "gray")
        self.log(f"[{time.strftime('%H:%M:%S')}] Сбор данных остановлен")

    def _collection_worker(self):
        """Фоновый поток сбора данных (без использования signal)"""
        import psutil
        import csv
        from datetime import datetime

        OUTPUT_FILE = "data/ueba_training_data.csv"
        os.makedirs("data", exist_ok=True)

        try:
            interval = int(self.interval_entry.get())
            file_exists = os.path.isfile(OUTPUT_FILE)

            # "Прогрев" CPU
            psutil.cpu_percent(interval=None)
            for proc in psutil.process_iter(['cpu_percent']): pass
            time.sleep(1)

            prev_disk_io = psutil.disk_io_counters()
            prev_net_io = psutil.net_io_counters()
            prev_pids = set()

            self.collected_rows = 0

            with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                if not file_exists:
                    writer.writerow([
                        'timestamp', 'cpu_percent', 'ram_percent',
                        'disk_read_delta', 'disk_write_delta',
                        'net_bytes_sent_delta', 'net_bytes_recv_delta',
                        'tcp_established', 'tcp_syn_sent', 'tcp_time_wait',
                        'top_process_cpu_percent', 'cpu_concentration_ratio', 'process_spawn_rate',
                        'is_anomaly_label'
                    ])
                    f.flush()

                self.log(f"[{time.strftime('%H:%M:%S')}] Интервал сбора: {interval} сек.")
                self.log(f"[{time.strftime('%H:%M:%S')}] Файл: {OUTPUT_FILE}")

                while self.is_running:
                    iter_start = time.time()

                    try:
                        # 1. Базовые метрики
                        cpu = psutil.cpu_percent(interval=None)
                        ram = psutil.virtual_memory().percent

                        # 2. Диски (дельта)
                        curr_disk_io = psutil.disk_io_counters()
                        disk_read_d = max(0, curr_disk_io.read_bytes - (prev_disk_io.read_bytes if prev_disk_io else 0))
                        disk_write_d = max(0,
                                           curr_disk_io.write_bytes - (prev_disk_io.write_bytes if prev_disk_io else 0))
                        prev_disk_io = curr_disk_io

                        # 3. Сеть (дельта)
                        curr_net_io = psutil.net_io_counters()
                        net_sent_d = max(0, curr_net_io.bytes_sent - (prev_net_io.bytes_sent if prev_net_io else 0))
                        net_recv_d = max(0, curr_net_io.bytes_recv - (prev_net_io.bytes_recv if prev_net_io else 0))
                        prev_net_io = curr_net_io

                        # 4. TCP соединения
                        tcp_stats = {'ESTABLISHED': 0, 'SYN_SENT': 0, 'TIME_WAIT': 0}
                        try:
                            for conn in psutil.net_connections(kind='inet'):
                                if conn.status in tcp_stats:
                                    tcp_stats[conn.status] += 1
                        except Exception:
                            pass

                        # 5. Процессы (умные фичи)
                        top_cpu = 0.0
                        current_pids = set()
                        for proc in psutil.process_iter(['pid', 'cpu_percent']):
                            try:
                                current_pids.add(proc.info['pid'])
                                cpu_val = proc.info['cpu_percent'] or 0
                                if cpu_val > top_cpu:
                                    top_cpu = cpu_val
                            except Exception:
                                continue

                        concentration = (top_cpu / cpu) if cpu > 0 else 0.0
                        spawn_rate = len(current_pids - prev_pids)
                        prev_pids = current_pids

                        # 6. Запись в CSV
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            cpu, ram,
                            disk_read_d, disk_write_d,
                            net_sent_d, net_recv_d,
                            tcp_stats['ESTABLISHED'], tcp_stats['SYN_SENT'], tcp_stats['TIME_WAIT'],
                            round(top_cpu, 2), round(concentration, 4), spawn_rate,
                            0  # is_anomaly_label
                        ])
                        f.flush()
                        os.fsync(f.fileno())

                        self.collected_rows += 1

                        # 7. Точный тайминг
                        elapsed = time.time() - iter_start
                        time.sleep(max(0, interval - elapsed))

                    except Exception as e:
                        self.log(f"[!] Ошибка при сборе метрик: {e}. Пропускаем итерацию.")
                        time.sleep(interval)

        except Exception as e:
            self.log(f"[ERROR] {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.is_running = False
            self.after(0, self._collection_finished)

    def _collection_finished(self):
        """Завершение сбора данных (вызывается из главного потока)"""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.app.set_status("Готов", "gray")
        self.log(f"[{time.strftime('%H:%M:%S')}] Сбор данных завершен.")
        self.log(f"[{time.strftime('%H:%M:%S')}] Всего собрано строк: {self.collected_rows}")

    def _update_stats(self):
        """Обновление статистики в UI"""
        if not self.is_running:
            return

        rows = getattr(self, 'collected_rows', 0)
        self.stats_label.configure(
            text=f"Собрано строк: {rows}\nФайл: data/ueba_training_data.csv"
        )

        # Повторяем каждые 2 секунды
        self.after(2000, self._update_stats)
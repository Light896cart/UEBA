"""Вкладка мониторинга с отображением алертов в реальном времени"""
import customtkinter as ctk
import threading
import time
import json
import os
import sys
from datetime import datetime

# Убрали импорт из history_tab, чтобы избежать циклических зависимостей в потоках.
# Путь к истории теперь задается явно, это надежнее.
HISTORY_FILE = "data/alerts_history.json"


class MonitorTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.is_running = False
        self.alerts = []
        self._build_ui()

    def _build_ui(self):
        # Заголовок
        ctk.CTkLabel(
            self,
            text="🔍 Мониторинг в реальном времени",
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(anchor="w", pady=(0, 20))

        # Верхняя панель с кнопками и статусом
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", pady=10)

        self.start_btn = ctk.CTkButton(
            top_frame,
            text="▶️ Запустить мониторинг",
            command=self.start_monitoring,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            height=40,
            width=200
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            top_frame,
            text="⏹️ Остановить",
            command=self.stop_monitoring,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40,
            width=200,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        # Статус
        self.status_frame = ctk.CTkFrame(top_frame)
        self.status_frame.pack(side="right", padx=10)

        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="⚪ Остановлен",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_indicator.pack(padx=15, pady=10)

        # Основная область: 2 колонки
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(fill="both", expand=True, pady=10)
        main_area.grid_columnconfigure(0, weight=1)
        main_area.grid_columnconfigure(1, weight=1)
        main_area.grid_rowconfigure(0, weight=1)

        # Левая колонка — текущие метрики
        metrics_frame = ctk.CTkFrame(main_area)
        metrics_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            metrics_frame,
            text="📊 Текущие метрики",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.metrics_text = ctk.CTkTextbox(metrics_frame, font=ctk.CTkFont(size=12))
        self.metrics_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Правая колонка — алерты
        alerts_frame = ctk.CTkFrame(main_area)
        alerts_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            alerts_frame,
            text="🚨 Обнаруженные аномалии",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.alerts_text = ctk.CTkTextbox(alerts_frame, font=ctk.CTkFont(size=12))
        self.alerts_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def start_monitoring(self):
        if self.is_running:
            return

        # Двойная проверка артефактов перед запуском
        if not os.path.exists("artifacts/ueba_autoencoder.pth"):
            self._safe_log_alert("[ERROR] Модель не обучена. Сначала выполните обучение.")
            return
        if not os.path.exists("artifacts/scaler.pkl"):
            self._safe_log_alert("[ERROR] Файл нормализации (scaler.pkl) не найден.")
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_indicator.configure(text="🟢 Активен", text_color="#2ecc71")
        self.app.set_status("Мониторинг активен", "#2ecc71")

        self.worker_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.worker_thread.start()

    def stop_monitoring(self):
        self.is_running = False
        # UI обновится сам через finally в потоке, но на всякий случай продублируем
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_indicator.configure(text="⚪ Остановлен", text_color="gray")
        self.app.set_status("Готов", "gray")

    def _monitor_worker(self):
        """Фоновый поток мониторинга (Пуленепробиваемая версия)"""
        try:
            import torch
            import torch.nn as nn # <-- ВАЖНО: добавили nn для локального класса
            import numpy as np
            import pandas as pd
            import joblib
            import psutil

            # 1. ЛОКАЛЬНОЕ определение модели.
            # Это ГЛАВНЫЙ ФИКС, который предотвращает краш при импортах в потоке/PyInstaller
            class UEBAutoencoder(nn.Module):
                def __init__(self, input_dim):
                    super(UEBAutoencoder, self).__init__()
                    self.encoder = nn.Sequential(
                        nn.Linear(input_dim, 8), nn.ReLU(), nn.Dropout(0.1),
                        nn.Linear(8, 4), nn.ReLU()
                    )
                    self.decoder = nn.Sequential(
                        nn.Linear(4, 8), nn.ReLU(), nn.Dropout(0.1),
                        nn.Linear(8, input_dim)
                    )
                def forward(self, x):
                    return self.decoder(self.encoder(x))

            # 2. Загрузка артефактов
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            checkpoint = torch.load("artifacts/ueba_autoencoder.pth", map_location=device, weights_only=False)

            model = UEBAutoencoder(checkpoint['input_dim']).to(device)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()

            scaler = joblib.load("artifacts/scaler.pkl")
            with open("artifacts/threshold.json") as f:
                threshold = json.load(f)['threshold']

            # 3. Прогрев
            psutil.cpu_percent(interval=None)
            for proc in psutil.process_iter(['cpu_percent']): pass
            time.sleep(1)

            prev_disk_io = psutil.disk_io_counters()
            prev_net_io = psutil.net_io_counters()
            prev_pids = set()

            # 4. Цикл мониторинга
            while self.is_running:
                iter_start = time.time()

                # Сбор метрик
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent

                curr_disk_io = psutil.disk_io_counters()
                disk_read_d = max(0, curr_disk_io.read_bytes - (prev_disk_io.read_bytes if prev_disk_io else 0))
                disk_write_d = max(0, curr_disk_io.write_bytes - (prev_disk_io.write_bytes if prev_disk_io else 0))
                prev_disk_io = curr_disk_io

                curr_net_io = psutil.net_io_counters()
                net_sent_d = max(0, curr_net_io.bytes_sent - (prev_net_io.bytes_sent if prev_net_io else 0))
                net_recv_d = max(0, curr_net_io.bytes_recv - (prev_net_io.bytes_recv if prev_net_io else 0))
                prev_net_io = curr_net_io

                tcp_stats = {'ESTABLISHED': 0, 'SYN_SENT': 0, 'TIME_WAIT': 0}
                try:
                    for conn in psutil.net_connections(kind='inet'):
                        if conn.status in tcp_stats:
                            tcp_stats[conn.status] += 1
                except Exception:
                    pass

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

                # Формируем вектор (DataFrame для корректной работы scaler)
                metrics_df = pd.DataFrame([{
                    'cpu_percent': float(cpu), 'ram_percent': float(ram),
                    'disk_read_delta': float(disk_read_d), 'disk_write_delta': float(disk_write_d),
                    'net_bytes_sent_delta': float(net_sent_d), 'net_bytes_recv_delta': float(net_recv_d),
                    'tcp_established': float(tcp_stats['ESTABLISHED']),
                    'tcp_syn_sent': float(tcp_stats['SYN_SENT']),
                    'tcp_time_wait': float(tcp_stats['TIME_WAIT']),
                    'top_process_cpu_percent': float(top_cpu),
                    'cpu_concentration_ratio': float(concentration),
                    'process_spawn_rate': float(spawn_rate)
                }])

                # Нормализация и инференс
                scaled = scaler.transform(metrics_df)
                with torch.no_grad():
                    tensor_in = torch.from_numpy(scaled).float().to(device)
                    pred = model(tensor_in).cpu().numpy()

                mse = float(np.mean(np.power(scaled - pred, 2)))

                # 5. Безопасное обновление UI (чистый синтаксис self.after без lambda)
                metrics_str = (
                    f"Время: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"Anomaly Score: {mse:.6f}\n"
                    f"Порог: {threshold:.6f}\n"
                    f"{'─' * 20}\n"
                    f"CPU: {cpu:.1f}% | RAM: {ram:.1f}%\n"
                    f"Топ-процесс CPU: {top_cpu:.1f}% (Конц.: {concentration:.2f})\n"
                    f"{'─' * 20}\n"
                    f"Диск: R {disk_read_d / 1024 / 1024:.1f} MB | W {disk_write_d / 1024 / 1024:.1f} MB\n"
                    f"Сеть: ↑ {net_sent_d / 1024:.1f} KB | ↓ {net_recv_d / 1024:.1f} KB\n"
                    f"{'─' * 20}\n"
                    f"TCP: EST {tcp_stats['ESTABLISHED']} | SYN {tcp_stats['SYN_SENT']} | WAIT {tcp_stats['TIME_WAIT']}\n"
                    f"Новых процессов: {spawn_rate}"
                )
                self.after(0, self._update_metrics_ui, metrics_str)

                # 6. Обнаружение аномалии
                if mse > threshold:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    threat = self._classify_threat({
                        'cpu_percent': cpu,
                        'top_process_cpu_percent': top_cpu,
                        'cpu_concentration_ratio': concentration,
                        'net_bytes_sent_delta': net_sent_d,
                        'tcp_syn_sent': tcp_stats['SYN_SENT'],
                        'disk_write_delta': disk_write_d,
                        'process_spawn_rate': spawn_rate
                    })

                    alert_data = {
                        'time': timestamp,
                        'score': mse,
                        'threshold': threshold,
                        'threat': threat,
                        'details': {
                            'CPU': f"{cpu:.1f}%",
                            'RAM': f"{ram:.1f}%",
                            'Сеть (отпр.)': f"{net_sent_d / 1024:.1f} KB",
                            'SYN_SENT': tcp_stats['SYN_SENT'],
                            'Новых процессов': spawn_rate
                        }
                    }

                    # Сохраняем в файл истории
                    self.after(0, self._save_alert_to_history, alert_data)

                    # Обновляем UI с алертом
                    alert_msg = f"[{timestamp}] 🚨 АНОМАЛИЯ!\nScore: {mse:.6f}\nКлассификация: {threat}\n{'─' * 20}\n"
                    self.after(0, self._update_alerts_ui, alert_msg)

                # Точный тайминг
                elapsed = time.time() - iter_start
                time.sleep(max(0, 5 - elapsed))

        except Exception as e:
            import traceback
            error_msg = f"[ERROR] Критический сбой мониторинга:\n{e}\n\n{traceback.format_exc()}"
            self.after(0, self._update_alerts_ui, error_msg)
        finally:
            self.is_running = False
            self.after(0, self._stop_monitoring_ui)

    # ================= ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =================

    def _update_metrics_ui(self, text):
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("1.0", text)

    def _update_alerts_ui(self, text):
        self.alerts_text.insert("end", text)
        self.alerts_text.see("end")

    def _save_alert_to_history(self, alert_data):
        try:
            os.makedirs("data", exist_ok=True)
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            history.append(alert_data)
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Не удалось сохранить алерт: {e}")

    def _stop_monitoring_ui(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_indicator.configure(text="⚪ Остановлен", text_color="gray")
        self.app.set_status("Готов", "gray")

    def _classify_threat(self, metrics):
        if metrics['cpu_percent'] > 70 and metrics['net_bytes_sent_delta'] < 10000000:
            return "🔴 Подозрение на скрытый майнер/ВПО"
        if metrics['tcp_syn_sent'] > 20:
            return f"🔴 Сканирование сети (SYN_SENT: {metrics['tcp_syn_sent']})"
        if metrics['net_bytes_sent_delta'] > 100000000:
            return f"🔴 Эксфильтрация данных ({metrics['net_bytes_sent_delta'] / 1024 / 1024:.1f} MB)"
        if metrics['disk_write_delta'] > 500000000 and metrics['process_spawn_rate'] > 5:
            return "🔴 Подозрение на шифровальщик"
        if metrics['cpu_percent'] > 50 and metrics['cpu_concentration_ratio'] < 0.3:
            return "🔴 Подозрение на ботнет"
        return "🟠 Неспецифичная аномальная активность"
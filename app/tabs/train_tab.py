"""Вкладка обучения модели с прогрессом и графиком"""
import customtkinter as ctk
import threading
import time
import os
import json
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Матplotlib для графика
import matplotlib

matplotlib.use('Agg')  # Без GUI окна
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class TrainTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.is_training = False
        self.cancel_training = False
        self.train_history = {'train_loss': [], 'val_loss': []}
        self._build_ui()

    def _build_ui(self):
        # Заголовок
        ctk.CTkLabel(
            self,
            text="🧠 Обучение Автоэнкодера",
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(anchor="w", pady=(0, 20))

        # Основная область: 2 колонки
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(fill="both", expand=True)
        main_area.grid_columnconfigure(0, weight=1)
        main_area.grid_columnconfigure(1, weight=1)
        main_area.grid_rowconfigure(1, weight=1)

        # ===== ЛЕВАЯ КОЛОНКА: Настройки и лог =====
        left_frame = ctk.CTkFrame(main_area)
        left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 5))

        # Параметры обучения
        params_label = ctk.CTkLabel(
            left_frame,
            text="⚙️ Параметры обучения",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        params_label.pack(anchor="w", padx=15, pady=(15, 10))

        params_grid = ctk.CTkFrame(left_frame, fg_color="transparent")
        params_grid.pack(fill="x", padx=15, pady=5)
        params_grid.grid_columnconfigure(1, weight=1)

        # Эпохи
        ctk.CTkLabel(params_grid, text="Эпохи (макс):").grid(row=0, column=0, sticky="w", pady=3)
        self.epochs_entry = ctk.CTkEntry(params_grid, width=100)
        self.epochs_entry.insert(0, "100")
        self.epochs_entry.grid(row=0, column=1, sticky="w", padx=10, pady=3)

        # Batch size
        ctk.CTkLabel(params_grid, text="Batch size:").grid(row=1, column=0, sticky="w", pady=3)
        self.batch_entry = ctk.CTkEntry(params_grid, width=100)
        self.batch_entry.insert(0, "32")
        self.batch_entry.grid(row=1, column=1, sticky="w", padx=10, pady=3)

        # Learning rate
        ctk.CTkLabel(params_grid, text="Learning rate:").grid(row=2, column=0, sticky="w", pady=3)
        self.lr_entry = ctk.CTkEntry(params_grid, width=100)
        self.lr_entry.insert(0, "0.001")
        self.lr_entry.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        # Patience (EarlyStopping)
        ctk.CTkLabel(params_grid, text="Patience (ES):").grid(row=3, column=0, sticky="w", pady=3)
        self.patience_entry = ctk.CTkEntry(params_grid, width=100)
        self.patience_entry.insert(0, "10")
        self.patience_entry.grid(row=3, column=1, sticky="w", padx=10, pady=3)

        # Кнопки управления
        buttons_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=15, pady=15)

        self.train_btn = ctk.CTkButton(
            buttons_frame,
            text="▶️ Начать обучение",
            command=self.start_training,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            height=40,
            width=180
        )
        self.train_btn.pack(side="left", padx=5)

        self.cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="⏹️ Отменить",
            command=self.cancel_train,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40,
            width=180,
            state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=5)

        # Прогресс-бар
        self.progress_label = ctk.CTkLabel(
            left_frame,
            text="Прогресс: 0 / 0 эпох",
            font=ctk.CTkFont(size=13)
        )
        self.progress_label.pack(anchor="w", padx=15, pady=(5, 0))

        self.progress_bar = ctk.CTkProgressBar(left_frame, height=20)
        self.progress_bar.pack(fill="x", padx=15, pady=5)
        self.progress_bar.set(0)

        # Лог обучения
        ctk.CTkLabel(
            left_frame,
            text="📜 Лог обучения",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(left_frame, height=200, font=ctk.CTkFont(size=11))
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # ===== ПРАВАЯ КОЛОНКА: График и результаты =====
        # График
        graph_frame = ctk.CTkFrame(main_area)
        graph_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            graph_frame,
            text="📈 График потерь (Loss)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Matplotlib фигура
        self.fig = Figure(figsize=(5, 3), dpi=100, facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_color('white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Результаты обучения
        results_frame = ctk.CTkFrame(main_area)
        results_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(5, 0))

        ctk.CTkLabel(
            results_frame,
            text="📊 Результаты обучения",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.results_text = ctk.CTkTextbox(results_frame, height=200, font=ctk.CTkFont(size=12))
        self.results_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Инициализация графика
        self._update_plot()

    def log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _update_plot(self):
        """Обновление графика потерь"""
        self.ax.clear()
        self.ax.set_facecolor('#2b2b2b')

        if self.train_history['train_loss']:
            epochs = range(1, len(self.train_history['train_loss']) + 1)
            self.ax.plot(epochs, self.train_history['train_loss'],
                         'o-', color='#3498db', label='Train Loss', linewidth=2)
            self.ax.plot(epochs, self.train_history['val_loss'],
                         's-', color='#e74c3c', label='Val Loss', linewidth=2)
            self.ax.legend(facecolor='#2b2b2b', labelcolor='white')
            self.ax.set_xlabel('Эпоха', color='white')
            self.ax.set_ylabel('MSE Loss', color='white')
            self.ax.set_title('Динамика обучения', color='white')
            self.ax.grid(True, alpha=0.3, color='gray')

        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('white')

        self.fig.tight_layout()
        self.canvas.draw()

    def start_training(self):
        """Запуск обучения"""
        # Проверка наличия данных
        if not os.path.exists("data/ueba_training_data.csv"):
            self.log("[ERROR] Данные не собраны. Сначала выполните сбор данных.")
            return

        if not os.path.exists("data/ueba_normalized_data.csv"):
            self.log("[INFO] Нормализованные данные не найдены. Запускаю нормализацию...")
            try:
                import preprocess_and_normalize
                preprocess_and_normalize.preprocess_data()
                self.log("[OK] Нормализация завершена.")
            except Exception as e:
                self.log(f"[ERROR] Ошибка нормализации: {e}")
                return

        self.is_training = True
        self.cancel_training = False
        self.train_history = {'train_loss': [], 'val_loss': []}
        self.train_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.results_text.delete("1.0", "end")
        self.app.set_status("Обучение...", "#f39c12")

        self.log(f"[{time.strftime('%H:%M:%S')}] Начало обучения...")

        # Запуск в отдельном потоке
        self.worker_thread = threading.Thread(target=self._training_worker, daemon=True)
        self.worker_thread.start()

    def cancel_train(self):
        """Отмена обучения"""
        self.cancel_training = True
        self.log(f"[{time.strftime('%H:%M:%S')}] Отмена обучения...")

    def _training_worker(self):
        """Фоновый поток обучения с АВТОМАТИЧЕСКОЙ нормализацией"""
        try:
            # 1. Локальные импорты для безопасности в потоке
            import torch
            import torch.nn as nn
            import torch.optim as optim
            import pandas as pd
            import numpy as np
            import joblib
            import json
            import os
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler

            # 2. Проверка сырых данных (база для всего)
            if not os.path.exists("data/ueba_training_data.csv"):
                self.after(0, lambda: self.log("[ERROR] Нет сырых данных (ueba_training_data.csv)!"))
                self.after(0, lambda: self.log("         Сначала выполните сбор данных во вкладке 'Сбор данных'."))
                return

            # 3. АВТОМАТИЧЕСКАЯ НОРМАЛИЗАЦИЯ (если файла нет)
            if not os.path.exists("data/ueba_normalized_data.csv"):
                self.after(0, lambda: self.log("[*] Нормализованные данные не найдены."))
                self.after(0, lambda: self.log("[*] Запускаю автоматическую нормализацию сырых данных..."))

                try:
                    # Читаем сырые данные
                    raw_df = pd.read_csv("data/ueba_training_data.csv")

                    # Список признаков (строго как в collector.py)
                    features = [
                        'cpu_percent', 'ram_percent', 'disk_read_delta', 'disk_write_delta',
                        'net_bytes_sent_delta', 'net_bytes_recv_delta',
                        'tcp_established', 'tcp_syn_sent', 'tcp_time_wait',
                        'top_process_cpu_percent', 'cpu_concentration_ratio', 'process_spawn_rate'
                    ]

                    # Очистка
                    X = raw_df[features].copy()
                    X = X.replace(-1, 0)  # Замена маркеров ошибок доступа
                    X = X.fillna(0)  # Замена пропусков

                    # Масштабирование
                    scaler = MinMaxScaler(feature_range=(0, 1))
                    X_scaled = scaler.fit_transform(X)

                    # Сохранение артефактов нормализации
                    os.makedirs("artifacts", exist_ok=True)
                    joblib.dump(scaler, "artifacts/scaler.pkl")
                    with open("artifacts/features.json", 'w') as f:
                        json.dump({'features': features}, f, indent=2)

                    # Сохранение нормализованного CSV
                    X_scaled_df = pd.DataFrame(X_scaled, columns=features)
                    X_scaled_df.to_csv("data/ueba_normalized_data.csv", index=False)

                    self.after(0, lambda: self.log(f"[+] Нормализация завершена! Обработано {len(X)} строк."))

                except Exception as norm_err:
                    self.after(0, lambda: self.log(f"[ERROR] Ошибка при автоматической нормализации: {norm_err}"))
                    return

            # 4. Загрузка уже нормализованных данных для обучения
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.after(0, lambda: self.log(f"[*] Устройство для обучения: {device}"))

            df = pd.read_csv("data/ueba_normalized_data.csv")
            X = df.values.astype(np.float32)
            features = list(df.columns)
            self.after(0, lambda: self.log(f"[*] Загружено {X.shape[0]} строк, {X.shape[1]} признаков"))

            # 5. Параметры из UI
            num_epochs = int(self.epochs_entry.get())
            batch_size = int(self.batch_entry.get())
            lr = float(self.lr_entry.get())
            patience = int(self.patience_entry.get())

            # 6. Подготовка DataLoader
            tensor_x = torch.from_numpy(X).to(device)
            dataset = TensorDataset(tensor_x, tensor_x)
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

            val_size = max(1, int(len(dataset) * 0.1))
            val_indices = list(range(len(dataset) - val_size, len(dataset)))
            val_subset = torch.utils.data.Subset(dataset, val_indices)
            val_loader = DataLoader(val_subset, batch_size=batch_size, shuffle=False)

            # 7. Определение модели (локально)
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

            input_dim = X.shape[1]
            model = UEBAutoencoder(input_dim).to(device)
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=lr)

            self.after(0, lambda: self.log(f"[*] Архитектура: {input_dim} → 8 → 4 → 8 → {input_dim}"))
            self.after(0, lambda: self.log(f"[*] Старт обучения..."))

            # 8. Цикл обучения
            best_val_loss = float('inf')
            patience_counter = 0
            best_model_state = None
            stopped_epoch = 0

            for epoch in range(num_epochs):
                if self.cancel_training:
                    self.after(0, lambda: self.log(f"\n[!] Обучение отменено пользователем."))
                    break

                # Training
                model.train()
                train_loss = 0.0
                for batch_x, _ in dataloader:
                    outputs = model(batch_x.to(device))
                    loss = criterion(outputs, batch_x.to(device))
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item() * batch_x.size(0)
                train_loss /= len(dataset)

                # Validation
                model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch_x, _ in val_loader:
                        outputs = model(batch_x.to(device))
                        loss = criterion(outputs, batch_x.to(device))
                        val_loss += loss.item() * batch_x.size(0)
                val_loss /= len(val_subset)

                self.train_history['train_loss'].append(train_loss)
                self.train_history['val_loss'].append(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_model_state = {k: v.clone() for k, v in model.state_dict().items()}
                else:
                    patience_counter += 1

                stopped_epoch = epoch + 1
                self.after(0, self._update_ui, epoch + 1, num_epochs, train_loss, val_loss)

                if patience_counter >= patience:
                    self.after(0, lambda ep=stopped_epoch: self.log(f"\n[!] EarlyStopping: остановлено на эпохе {ep}"))
                    break

            if self.cancel_training and best_model_state is None:
                return

            if best_model_state is not None:
                model.load_state_dict(best_model_state)

            # 9. Сохранение артефактов модели
            os.makedirs("artifacts", exist_ok=True)
            torch.save({
                'model_state_dict': model.state_dict(),
                'input_dim': input_dim,
                'features': features
            }, "artifacts/ueba_autoencoder.pth")
            self.after(0, lambda: self.log("[+] Модель сохранена в artifacts/ueba_autoencoder.pth"))

            # 10. Расчет порога
            model.eval()
            with torch.no_grad():
                predictions = model(tensor_x).cpu().numpy()

            mse = np.mean(np.power(X - predictions, 2), axis=1)
            mean_mse = float(np.mean(mse))
            std_mse = float(np.std(mse))
            max_mse = float(np.max(mse))
            threshold = mean_mse + 3 * std_mse

            with open("artifacts/threshold.json", 'w') as f:
                json.dump({
                    'threshold': threshold, 'mean_mse': mean_mse,
                    'std_mse': std_mse, 'max_mse': max_mse, 'features': features
                }, f, indent=2)

            anomalies_count = int(np.sum(mse > threshold))
            anomalies_percent = (anomalies_count / len(mse)) * 100

            # Вывод результатов
            results = f"""
═══════════════════════════════════════
✅ ОБУЧЕНИЕ ЗАВЕРШЕНО УСПЕШНО
═══════════════════════════════════════

Эпох пройдено: {stopped_epoch}
Лучшая val_loss: {best_val_loss:.6f}

Статистика ошибок восстановления:
  • Mean MSE: {mean_mse:.6f}
  • Std MSE:  {std_mse:.6f}
  • Max MSE:  {max_mse:.6f}

🎯 Порог аномальности: {threshold:.6f}
   (Mean + 3*Std)

Ложные срабатывания на ОВ: 
  {anomalies_count} из {len(mse)} ({anomalies_percent:.2f}%)

Артефакты сохранены:
  • artifacts/ueba_autoencoder.pth
  • artifacts/threshold.json
═══════════════════════════════════════
""".strip()

            self.after(0, self.results_text.delete, "1.0", "end")
            self.after(0, self.results_text.insert, "1.0", results)
            self.log(f"\n[+] Порог аномальности: {threshold:.6f}")
            self.log(f"[+] Готово к мониторингу!")

        except Exception as e:
            import traceback
            self.log(f"\n[ERROR] {e}")
            self.log(traceback.format_exc())
        finally:
            self.is_training = False
            self.after(0, self._training_finished)

    def _update_ui(self, epoch, total, train_loss, val_loss):
        """Обновление UI из главного потока"""
        self.progress_bar.set(epoch / total)
        self.progress_label.configure(text=f"Прогресс: {epoch} / {total} эпох")
        self.log(f"Epoch [{epoch}/{total}] | Train: {train_loss:.6f} | Val: {val_loss:.6f}")
        self._update_plot()

    def _training_finished(self):
        """Завершение обучения"""
        self.train_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        self.app.set_status("Готов", "gray")
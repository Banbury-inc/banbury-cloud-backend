import os
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
import matplotlib.pyplot as plt

class PredictionService:
    def __init__(self):
        pass
    
    def create_dataset(self, X, y, time_steps=1):
        Xs, ys = [], []
        for i in range(len(X) - time_steps):
            v = X.iloc[i:(i + time_steps)].values
            Xs.append(v)
            ys.append(y.iloc[i + time_steps])
        return np.array(Xs), np.array(ys)

    def build_and_train_model(self, X_train, y_train, time_steps, features):
        model = Sequential([
            LSTM(50, activation='relu', input_shape=(time_steps, features)),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=1)
        return model

    def predict_future_speed(self, model, df, scaler, time_steps, data_type):
        data = df[[data_type]].tail(time_steps).values
        last_X_scaled = scaler.transform(data)
        last_X = last_X_scaled.reshape(1, time_steps, 1)
        predicted_speed_scaled = model.predict(last_X)
        predicted_speed = scaler.inverse_transform(predicted_speed_scaled)[0][0]
        return predicted_speed

    def performance_data(self, devices, show_graph):
        future_datetime = datetime.strptime('2024-04-30 12:00:00', '%Y-%m-%d %H:%M:%S')
        performance_data = []

        # devices is a list containing a single device dictionary
        for device in devices['devices']:
            device_name = device.get('device_name', 'Unknown Device')
            print(f"Processing device: {device_name}")

            # Get network speeds and timestamps
            upload_speeds = []
            if 'upload_speed' in device:
                upload_speeds = [float(speed) for speed in device['upload_speed'] 
                               if speed is not None]
                print(f"Found {len(upload_speeds)} upload speeds")
            
            download_speeds = []
            if 'download_speed' in device:
                download_speeds = [float(speed) for speed in device['download_speed']
                                 if speed is not None] 
                print(f"Found {len(download_speeds)} download speeds")

            current_times = []
            if 'current_time' in device:
                current_times = [speed for speed in device['current_time']]
                print(f"Found {len(current_times)} timestamps")
            else:
                print("Warning: No data available for current times")
            # Try both timestamp formats
            timestamps = []
            for ts in current_times:
                if not ts:
                    continue
                try:
                    # Try first format with microseconds
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        # Try second format without microseconds
                        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        print(f"Skipping invalid timestamp: {ts}")
                        continue
                timestamps.append(dt)


            # Ensure all arrays are same length by taking minimum length
            min_length = min(len(timestamps), len(upload_speeds), len(download_speeds))
            timestamps = timestamps[:min_length]
            upload_speeds = upload_speeds[:min_length]
            download_speeds = download_speeds[:min_length]


            # Create and sort dataframes
            if len(timestamps) > 0 and len(upload_speeds) > 0:
                df_upload_speed = pd.DataFrame({
                    'timestamp': timestamps,
                    'speed': upload_speeds
                })
                df_upload_speed.sort_values('timestamp', inplace=True)
            else:
                print("Warning: No data available for upload speeds")
                df_upload_speed = pd.DataFrame(columns=['timestamp', 'speed'])

            if len(timestamps) > 0 and len(download_speeds) > 0:
                df_download_speed = pd.DataFrame({
                    'timestamp': timestamps,
                    'speed': download_speeds
                })
                df_download_speed.sort_values('timestamp', inplace=True)
            else:
                print("Warning: No data available for download speeds")
                df_download_speed = pd.DataFrame(columns=['timestamp', 'speed'])

            print(f"df_upload_speed: {df_upload_speed}")
            print(f"df_download_speed: {df_download_speed}")

            # Scale the features
            scaler = MinMaxScaler(feature_range=(0, 1))
            
            # Scale upload speeds
            if not df_upload_speed.empty:
                df_upload_speed['scaled_speed'] = scaler.fit_transform(df_upload_speed[['speed']])
            
            time_steps = max(2, min(5, len(df_upload_speed) // 2))  # Adjust time_steps based on data size

            # For upload speed prediction
            if not df_upload_speed.empty:
                X, y = self.create_dataset(df_upload_speed[['scaled_speed']], 
                                         df_upload_speed['scaled_speed'], 
                                         time_steps)
                
                model = self.train_model_with_data(X, y, time_steps, 1)
                if model is not None:
                    predicted_upload_speed = self.predict_future_speed(
                        model, df_upload_speed, scaler, time_steps, data_type='speed'
                    )
                else:
                    predicted_upload_speed = None
            else:
                predicted_upload_speed = None

            # Scale download speeds
            if not df_download_speed.empty:
                df_download_speed['scaled_speed'] = scaler.fit_transform(df_download_speed[['speed']])

            # For download speed prediction 
            if not df_download_speed.empty:
                X, y = self.create_dataset(df_download_speed[['scaled_speed']], 
                                         df_download_speed['scaled_speed'], 
                                         time_steps)
                
                model = self.train_model_with_data(X, y, time_steps, 1)
                if model is not None:
                    predicted_download_speed = self.predict_future_speed(
                        model, df_download_speed, scaler, time_steps, data_type='speed'
                    )
                else:
                    predicted_download_speed = None
            else:
                predicted_download_speed = None

            # Initialize predictions to None
            predicted_gpu_usage = None
            predicted_cpu_usage = None
            predicted_ram_usage = None
            
            individual_performance_data = {
                'device_name': device_name,
                'predicted_upload_speed': int(predicted_upload_speed) if predicted_upload_speed is not None else None,
                'predicted_download_speed': int(predicted_download_speed) if predicted_download_speed is not None else None,
                'predicted_gpu_usage': int(predicted_gpu_usage) if predicted_gpu_usage is not None else None,
                'predicted_cpu_usage': int(predicted_cpu_usage) if predicted_cpu_usage is not None else None,
                'predicted_ram_usage': int(predicted_ram_usage) if predicted_ram_usage is not None else None,
            }

            # Only plot if we have valid predictions
            if show_graph and predicted_upload_speed is not None and predicted_download_speed is not None:
                plt.figure(figsize=(10, 5))
                plt.plot(df_upload_speed['timestamp'], df_upload_speed['speed'], 
                        label='Historical Upload Speeds', marker='o')
                plt.plot(df_download_speed['timestamp'], df_download_speed['speed'], 
                        label='Historical Download Speeds', marker='o')
                plt.axvline(x=future_datetime, color='r', linestyle='--', label='Prediction Point')
                plt.plot(future_datetime, predicted_upload_speed, 'ro', 
                        label=f'Predicted Upload Speed: {predicted_upload_speed:.2f} Mbps')
                plt.plot(future_datetime, predicted_download_speed, 'ro', 
                        label=f'Predicted Download Speed: {predicted_download_speed:.2f} Mbps')
                plt.title(f"Network Speeds Prediction for {device_name}")
                plt.xlabel('Timestamp')
                plt.ylabel('Speed (Mbps)')
                plt.legend()
                plt.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()

            performance_data.append(individual_performance_data)

        return performance_data

    def train_model_with_data(self, X, y, time_steps, features):
        if len(X) < 2:  # If we have too few samples
            print("Not enough data points for prediction")
            return None
            
        # Adjust test_size based on data size
        test_size = min(0.2, 1/len(X))
        
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            model = self.build_and_train_model(X_train, y_train, time_steps, features)
            return model
        except Exception as e:
            print(f"Error training model: {str(e)}")
            return None

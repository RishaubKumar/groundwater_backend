"""
Machine Learning forecasting services for water level prediction and drought risk assessment.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import joblib
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import tensorflow as tf
from tensorflow import keras
from app.core.database import get_influx_client, get_db
from app.models.analytics import WaterLevelForecast, DroughtRiskAssessment, RechargeEstimate

logger = logging.getLogger(__name__)


class MLForecastingService:
    """Machine Learning service for forecasting and analytics."""
    
    def __init__(self):
        self.influx_client = get_influx_client()
        self.models = {}
        self.scalers = {}
        self.model_path = "models/"
        
    async def train_water_level_model(self, station_id: str, sensor_id: str) -> Dict[str, Any]:
        """Train a water level forecasting model for a specific sensor."""
        try:
            # Get historical data
            data = await self._get_training_data(station_id, sensor_id, days=365)
            
            if len(data) < 100:  # Need sufficient data
                logger.warning(f"Insufficient data for training: {station_id}/{sensor_id}")
                return {'status': 'insufficient_data'}
            
            # Prepare features and targets
            X, y = self._prepare_features(data)
            
            if X is None or len(X) < 50:
                return {'status': 'insufficient_features'}
            
            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            # Store model and scaler
            model_key = f"{station_id}_{sensor_id}"
            self.models[model_key] = model
            self.scalers[model_key] = scaler
            
            # Save model
            await self._save_model(model, scaler, model_key)
            
            return {
                'status': 'success',
                'mae': mae,
                'rmse': rmse,
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
        except Exception as e:
            logger.error(f"Error training water level model: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _get_training_data(self, station_id: str, sensor_id: str, days: int = 365) -> List[Dict[str, Any]]:
        """Get training data for model training."""
        try:
            query_api = self.influx_client.query_api()
            
            start_time = datetime.now() - timedelta(days=days)
            
            # Get sensor data
            sensor_query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> sort(columns: ["_time"])
            '''
            
            # Get weather data
            weather_query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "weather_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> sort(columns: ["_time"])
            '''
            
            sensor_result = query_api.query(sensor_query)
            weather_result = query_api.query(weather_query)
            
            # Process sensor data
            sensor_data = {}
            for table in sensor_result:
                for record in table.records:
                    timestamp = record.get_time()
                    value = record.get_value()
                    sensor_data[timestamp] = {'water_level': value}
            
            # Process weather data
            weather_data = {}
            for table in weather_result:
                for record in table.records:
                    timestamp = record.get_time()
                    field = record.get_field()
                    value = record.get_value()
                    
                    if timestamp not in weather_data:
                        weather_data[timestamp] = {}
                    weather_data[timestamp][field] = value
            
            # Combine data
            combined_data = []
            for timestamp in sorted(sensor_data.keys()):
                data_point = {
                    'timestamp': timestamp,
                    'water_level': sensor_data[timestamp]['water_level']
                }
                
                # Add weather data if available
                if timestamp in weather_data:
                    data_point.update(weather_data[timestamp])
                
                combined_data.append(data_point)
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return []
    
    def _prepare_features(self, data: List[Dict[str, Any]]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare features and targets for training."""
        try:
            if not data:
                return None, None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            # Create time-based features
            df['hour'] = df.index.hour
            df['day_of_year'] = df.index.dayofyear
            df['month'] = df.index.month
            df['is_weekend'] = df.index.weekday >= 5
            
            # Create lagged features
            for lag in [1, 2, 3, 6, 12, 24]:  # hours
                df[f'water_level_lag_{lag}h'] = df['water_level'].shift(lag)
            
            # Create rolling statistics
            for window in [6, 12, 24]:  # hours
                df[f'water_level_mean_{window}h'] = df['water_level'].rolling(window=window).mean()
                df[f'water_level_std_{window}h'] = df['water_level'].rolling(window=window).std()
            
            # Create weather features if available
            weather_features = ['temperature_c', 'rainfall_mm', 'humidity_percent', 'pressure_hpa']
            for feature in weather_features:
                if feature in df.columns:
                    # Fill missing values with forward fill
                    df[feature] = df[feature].fillna(method='ffill')
                    
                    # Create lagged weather features
                    for lag in [1, 6, 12, 24]:
                        df[f'{feature}_lag_{lag}h'] = df[feature].shift(lag)
            
            # Remove rows with NaN values
            df = df.dropna()
            
            if len(df) < 10:
                return None, None
            
            # Select features
            feature_columns = [col for col in df.columns if col != 'water_level']
            X = df[feature_columns].values
            y = df['water_level'].values
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return None, None
    
    async def _save_model(self, model, scaler, model_key: str):
        """Save trained model and scaler."""
        try:
            import os
            os.makedirs(self.model_path, exist_ok=True)
            
            # Save model
            model_file = f"{self.model_path}{model_key}_model.joblib"
            joblib.dump(model, model_file)
            
            # Save scaler
            scaler_file = f"{self.model_path}{model_key}_scaler.joblib"
            joblib.dump(scaler, scaler_file)
            
            logger.info(f"Saved model and scaler for {model_key}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    async def load_model(self, station_id: str, sensor_id: str) -> bool:
        """Load trained model and scaler."""
        try:
            model_key = f"{station_id}_{sensor_id}"
            model_file = f"{self.model_path}{model_key}_model.joblib"
            scaler_file = f"{self.model_path}{model_key}_scaler.joblib"
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                model = joblib.load(model_file)
                scaler = joblib.load(scaler_file)
                
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    async def predict_water_level(self, station_id: str, sensor_id: str, 
                                horizon_hours: int = 24) -> List[Dict[str, Any]]:
        """Predict water levels for the next horizon_hours."""
        try:
            model_key = f"{station_id}_{sensor_id}"
            
            # Load model if not in memory
            if model_key not in self.models:
                loaded = await self.load_model(station_id, sensor_id)
                if not loaded:
                    return []
            
            model = self.models[model_key]
            scaler = self.scalers[model_key]
            
            # Get recent data for prediction
            recent_data = await self._get_recent_data(station_id, sensor_id, hours=48)
            
            if not recent_data:
                return []
            
            predictions = []
            current_data = recent_data.copy()
            
            for hour in range(1, horizon_hours + 1):
                # Prepare features for this prediction
                X = self._prepare_prediction_features(current_data, hour)
                
                if X is None:
                    break
                
                # Scale features
                X_scaled = scaler.transform(X.reshape(1, -1))
                
                # Make prediction
                prediction = model.predict(X_scaled)[0]
                
                # Calculate confidence interval (simplified)
                confidence_interval = 0.1 * abs(prediction)  # 10% of prediction
                
                predictions.append({
                    'timestamp': (datetime.now() + timedelta(hours=hour)).isoformat(),
                    'predicted_level': float(prediction),
                    'confidence_lower': float(prediction - confidence_interval),
                    'confidence_upper': float(prediction + confidence_interval),
                    'horizon_hours': hour
                })
                
                # Update current_data with prediction for next iteration
                current_data.append({
                    'timestamp': datetime.now() + timedelta(hours=hour),
                    'water_level': prediction
                })
            
            # Store predictions in database
            await self._store_predictions(station_id, sensor_id, predictions)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting water level: {e}")
            return []
    
    async def _get_recent_data(self, station_id: str, sensor_id: str, hours: int = 48) -> List[Dict[str, Any]]:
        """Get recent data for prediction."""
        try:
            query_api = self.influx_client.query_api()
            
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> sort(columns: ["_time"])
            '''
            
            result = query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time(),
                        'water_level': record.get_value()
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting recent data: {e}")
            return []
    
    def _prepare_prediction_features(self, data: List[Dict[str, Any]], horizon_hours: int) -> Optional[np.ndarray]:
        """Prepare features for prediction."""
        try:
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            # Create time-based features for prediction time
            pred_time = datetime.now() + timedelta(hours=horizon_hours)
            df.loc[pred_time, 'hour'] = pred_time.hour
            df.loc[pred_time, 'day_of_year'] = pred_time.dayofyear
            df.loc[pred_time, 'month'] = pred_time.month
            df.loc[pred_time, 'is_weekend'] = pred_time.weekday() >= 5
            
            # Create lagged features
            for lag in [1, 2, 3, 6, 12, 24]:
                df[f'water_level_lag_{lag}h'] = df['water_level'].shift(lag)
            
            # Create rolling statistics
            for window in [6, 12, 24]:
                df[f'water_level_mean_{window}h'] = df['water_level'].rolling(window=window).mean()
                df[f'water_level_std_{window}h'] = df['water_level'].rolling(window=window).std()
            
            # Get the last row (most recent data)
            last_row = df.iloc[-1]
            
            # Select feature columns
            feature_columns = [col for col in df.columns if col != 'water_level']
            X = last_row[feature_columns].values
            
            # Handle NaN values
            X = np.nan_to_num(X, nan=0.0)
            
            return X
            
        except Exception as e:
            logger.error(f"Error preparing prediction features: {e}")
            return None
    
    async def _store_predictions(self, station_id: str, sensor_id: str, predictions: List[Dict[str, Any]]):
        """Store predictions in database."""
        try:
            db = next(get_db())
            
            for pred in predictions:
                forecast = WaterLevelForecast(
                    station_id=station_id,
                    forecast_date=datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00')),
                    predicted_level=pred['predicted_level'],
                    confidence_interval_lower=pred['confidence_lower'],
                    confidence_interval_upper=pred['confidence_upper'],
                    model_name='random_forest',
                    model_version='1.0',
                    forecast_horizon_days=pred['horizon_hours'] / 24
                )
                
                db.add(forecast)
            
            db.commit()
            logger.info(f"Stored {len(predictions)} predictions for {station_id}/{sensor_id}")
            
        except Exception as e:
            logger.error(f"Error storing predictions: {e}")
        finally:
            db.close()
    
    async def assess_drought_risk(self, station_id: str, sensor_id: str) -> Dict[str, Any]:
        """Assess drought risk for a station."""
        try:
            # Get recent water level data
            recent_data = await self._get_recent_data(station_id, sensor_id, days=90)
            
            if not recent_data:
                return {'risk_level': 'unknown', 'risk_score': 0.0}
            
            # Calculate risk indicators
            current_level = recent_data[-1]['water_level']
            historical_levels = [d['water_level'] for d in recent_data]
            
            # Calculate statistics
            mean_level = np.mean(historical_levels)
            std_level = np.std(historical_levels)
            min_level = np.min(historical_levels)
            
            # Calculate trend
            if len(historical_levels) > 7:
                recent_trend = np.polyfit(range(7), historical_levels[-7:], 1)[0]
            else:
                recent_trend = 0
            
            # Calculate risk score (0-1)
            risk_score = 0.0
            
            # Current level relative to historical average
            if current_level < mean_level - std_level:
                risk_score += 0.3
            elif current_level < mean_level:
                risk_score += 0.1
            
            # Trend analysis
            if recent_trend < -0.01:  # Declining trend
                risk_score += 0.2
            elif recent_trend < -0.005:
                risk_score += 0.1
            
            # Proximity to historical minimum
            if current_level < min_level * 1.1:  # Within 10% of minimum
                risk_score += 0.3
            elif current_level < min_level * 1.2:  # Within 20% of minimum
                risk_score += 0.1
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = 'critical'
            elif risk_score >= 0.5:
                risk_level = 'high'
            elif risk_score >= 0.3:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Calculate days to potential drought (simplified)
            if recent_trend < 0:
                days_to_drought = int((current_level - min_level) / abs(recent_trend) * 24)  # Convert to days
            else:
                days_to_drought = 999  # No immediate risk
            
            # Store assessment
            await self._store_drought_assessment(station_id, risk_level, risk_score, 
                                               current_level, mean_level, recent_trend, days_to_drought)
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'current_level': current_level,
                'historical_average': mean_level,
                'trend': 'decreasing' if recent_trend < 0 else 'increasing' if recent_trend > 0 else 'stable',
                'days_to_drought': days_to_drought
            }
            
        except Exception as e:
            logger.error(f"Error assessing drought risk: {e}")
            return {'risk_level': 'unknown', 'risk_score': 0.0}
    
    async def _store_drought_assessment(self, station_id: str, risk_level: str, risk_score: float,
                                      current_level: float, historical_average: float, 
                                      trend: float, days_to_drought: int):
        """Store drought risk assessment in database."""
        try:
            db = next(get_db())
            
            assessment = DroughtRiskAssessment(
                station_id=station_id,
                assessment_date=datetime.now(),
                risk_level=risk_level,
                risk_score=risk_score,
                days_to_drought=days_to_drought,
                current_level_m=current_level,
                historical_average_m=historical_average,
                trend='decreasing' if trend < 0 else 'increasing' if trend > 0 else 'stable',
                contributing_factors={
                    'current_vs_average': current_level - historical_average,
                    'trend_slope': trend,
                    'risk_score': risk_score
                }
            )
            
            db.add(assessment)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing drought assessment: {e}")
        finally:
            db.close()
    
    async def estimate_recharge(self, station_id: str, days: int = 30) -> Dict[str, Any]:
        """Estimate groundwater recharge for a station."""
        try:
            # Get water level and rainfall data
            water_data = await self._get_recent_data(station_id, 'water_level', days=days)
            rainfall_data = await self._get_rainfall_data(station_id, days=days)
            
            if not water_data or len(water_data) < 7:
                return {'recharge_mm': 0.0, 'method': 'insufficient_data'}
            
            # Calculate water level change
            water_levels = [d['water_level'] for d in water_data]
            level_change = water_levels[-1] - water_levels[0]
            
            # Calculate rainfall
            total_rainfall = sum([d['rainfall_mm'] for d in rainfall_data]) if rainfall_data else 0
            
            # Simple recharge estimation (water level rise + rainfall)
            recharge = max(0, level_change * 1000) + total_rainfall  # Convert m to mm
            
            # Store estimate
            await self._store_recharge_estimate(station_id, recharge, total_rainfall, level_change)
            
            return {
                'recharge_mm': recharge,
                'method': 'water_balance',
                'rainfall_mm': total_rainfall,
                'level_change_m': level_change,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error estimating recharge: {e}")
            return {'recharge_mm': 0.0, 'method': 'error'}
    
    async def _get_rainfall_data(self, station_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get rainfall data for a station."""
        try:
            query_api = self.influx_client.query_api()
            
            start_time = datetime.now() - timedelta(days=days)
            
            query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "weather_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> filter(fn: (r) => r["_field"] == "rainfall_mm")
            |> sort(columns: ["_time"])
            '''
            
            result = query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time(),
                        'rainfall_mm': record.get_value()
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting rainfall data: {e}")
            return []
    
    async def _store_recharge_estimate(self, station_id: str, recharge: float, 
                                     rainfall: float, level_change: float):
        """Store recharge estimate in database."""
        try:
            db = next(get_db())
            
            estimate = RechargeEstimate(
                station_id=station_id,
                date=datetime.now(),
                recharge_mm=recharge,
                method='water_balance',
                rainfall_mm=rainfall,
                pumping_mm=0.0,  # Would need pumping data
                evapotranspiration_mm=0.0,  # Would need ET data
                confidence_score=0.7  # Simplified confidence
            )
            
            db.add(estimate)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing recharge estimate: {e}")
        finally:
            db.close()

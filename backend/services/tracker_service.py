"""Tracker Service for monitoring positions"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TrackerService:
    """Servicio para rastrear posiciones activas"""
    
    EXPIRY_HOURS = 24
    
    @staticmethod
    def calculate_pnl(signal: Dict[str, Any], status: str, closed_price: float) -> float:
        """Calcula el P&L de una posición cerrada"""
        entry = signal.get("price", 0)
        direction = signal.get("direction", "")
        
        if status == "EXPIRED":
            if direction == "LONG":
                return ((closed_price - entry) / entry) * 100 if entry else 0
            else:
                return ((entry - closed_price) / entry) * 100 if entry else 0
        
        elif status == "WON":
            tp = signal.get("take_profit", 0)
            if direction == "LONG":
                return ((tp - entry) / entry) * 100 if entry else 0
            else:
                return ((entry - tp) / entry) * 100 if entry else 0
        
        elif status == "LOST":
            sl = signal.get("stop_loss", 0)
            if direction == "LONG":
                return ((sl - entry) / entry) * 100 if entry else 0
            else:
                return ((entry - sl) / entry) * 100 if entry else 0
        
        return 0
    
    @staticmethod
    def check_signal_closure(db_signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Verifica si una señal debe cerrarse"""
        direction = db_signal.get("direction", "")
        status = None
        closed_price = None
        
        if direction == "LONG":
            if current_price >= db_signal.get("take_profit", float('inf')):
                status = "WON"
                closed_price = db_signal.get("take_profit")
            elif current_price <= db_signal.get("stop_loss", 0):
                status = "LOST"
                closed_price = db_signal.get("stop_loss")
        
        elif direction == "SHORT":
            if current_price <= db_signal.get("take_profit", 0):
                status = "WON"
                closed_price = db_signal.get("take_profit")
            elif current_price >= db_signal.get("stop_loss", float('inf')):
                status = "LOST"
                closed_price = db_signal.get("stop_loss")
        
        # Verificar expiración
        if not status and db_signal.get("sent_at"):
            try:
                sent_time = datetime.fromisoformat(db_signal["sent_at"])
                elapsed_hours = (datetime.utcnow() - sent_time).total_seconds() / 3600
                
                if elapsed_hours > TrackerService.EXPIRY_HOURS:
                    status = "EXPIRED"
                    closed_price = current_price
            except Exception as e:
                logger.warning(f"Error checking expiration: {e}")
        
        return {
            "status": status,
            "closed_price": closed_price,
            "pnl": TrackerService.calculate_pnl(db_signal, status, closed_price) if status else None
        }

"""Broker Integrations Package — Stub"""

class BrokerFactory:
    """Stub broker factory."""

    @staticmethod
    def get_broker(broker_type: str = 'paper', config=None):
        if broker_type.lower() == 'angelone':
            from app.brokers.angelone.services.broker_service import AngelOneBroker
            return AngelOneBroker(config)
        
        if broker_type.lower() == 'paper':
            # Stub paper broker with get_balance
            class PaperBroker:
                def get_balance(self): return 10000.0
            return PaperBroker()
            
        raise NotImplementedError(f"Broker '{broker_type}' not yet implemented")

    @staticmethod
    def list_available():
        return ['paper', 'angelone']

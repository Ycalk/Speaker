
class Connector:
    class Utils:
        @staticmethod
        def get_celebrity(connector_instance, code: str) -> dict:
            return next(x for x in connector_instance.get_celebrities() if x["code"] == code)
        
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def get_celebrities(self) -> list[dict]:
        return [{'name': 'Test', 'code': 'test'}]
    
    def get_celebrity(self, code: str) -> dict:
        return next(x for x in self.get_celebrities() if x["code"] == code)
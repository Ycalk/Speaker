from listeners.listener import Listener


class GeneratingRequestListener (Listener):
    def handler(self, data):
        print('GeneratingRequestListener', data)
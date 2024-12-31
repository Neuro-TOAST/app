
class BatchBase:
    def __init__(self, app):
        # self.printer = None
        self.app = app

    # def set_printer(self, printer):
    #     self.printer = printer

    @property
    def workspace(self):
        return self.app.workspace

    def print(self, message):
        self.app.signals_queue.put(('print', str(message)))
        # if self.printer is not None:
        #   self.printer(message)
        # else:
        #   print('(subprocess) ' + message)

    @staticmethod
    def show_html(app):
        pass

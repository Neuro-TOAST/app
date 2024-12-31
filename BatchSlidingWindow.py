import os
import os.path as path
import numpy
import shutil
import BatchBase

class BatchSlidingWindow(BatchBase.BatchBase):
    def __init__(self, *parent):
        super().__init__(*parent)
        self.report_params = {}

    def load_signals(self, sigs_file):
        '''Nacte signaly z parcelace ulozene do CSV souboru a konvertuje je do numpy array.'''
        return numpy.loadtxt(sigs_file, float)

    def calc_corr(self, sigs):
        '''Vypocita korelacni matici zadanych signalu, dle konfigurace nuluje diagonalu, provede Fisher-Z transformaci a abs.'''
        rho = numpy.corrcoef(sigs.T)  # Pearson
        # rho[numpy.eye(rho.shape[0]) == 1] = 0  # dle docky, na diagoale maji byt nuly (The network matrices should not contain self-self connections.)
        # rho = numpy.arctanh(rho)  # fisher-z transform, pozor na to, hodnoty pak presahnou rozsah 0-1, coz jsou predpoklady mnoha funkci
        # rho = numpy.abs(rho)
        return rho

    def load_rho_window(self, sigs):
        '''Vybere signaly ze zadaneho sliding window'''
        return self.calc_corr(sigs)

    def load_subject_conns(self, sigs_file):
        '''Vypocita soubor sliding windows konkretniho participanta a session, vezme pouze horni trojuhelnikovou matici a reshapuje do vektoru.'''
        sliding_windows = []
        sigs = self.load_signals(sigs_file)
        self.report_params['rois_count'] = sigs.shape[1]
        for begin in range(0, sigs.shape[0] - self.wsize, self.wstep):
            matrix = self.load_rho_window(sigs[slice(begin, begin + self.wsize), :])
            triu_ind = numpy.triu_indices(matrix.shape[0], k=1)
            sliding_windows.append(matrix[triu_ind])
        self.report_params['edges_count'] = len(sliding_windows[0])
        return sliding_windows

    def configure(self, params):
        self.wsize = int(params['wsize'])
        self.wstep = int(params['wstep'])
        # NOTE: nyni jsou excludovane rois vyrazeny jiz v parcelaci a nacitaji se pouze validni data, vyhoda je, ze je to na jednom miste u parcelace
        # self.rois = [5, 6, 7]  # je treba sem dat vsechny rois - excluded rois

    def exec(self, params, subjects_model):
        self.configure(params['sliding-window'])
        n = len(subjects_model.get_active_subjs())
        self.report_params['subjects_count'] = n
        self.report_params['tr'] = params['fMRI']['TR']
        self.report_params['windows_in_series'] = {}
        for k, subj in enumerate(subjects_model.get_active_subjs()):
            sn = len(self.workspace.sessions(subj))
            for s, session in enumerate(self.workspace.sessions(subj)):
                sliding_conns = self.load_subject_conns(session.sigs_file())
                conn_filename = session.sliding_conn_file()
                os.makedirs(path.dirname(conn_filename), exist_ok=True)
                numpy.savetxt(conn_filename, sliding_conns)
                self.report_params['windows_in_series'][session.id()] = len(sliding_conns)
                self.print(f'({k+1}/{n}, {s+1}/{sn}) Calculated sliding windows for subject {subj} and session {session.name()}.')
        self.build_js_app()

    def build_js_app(self):
        src_js_path = path.join(path.dirname(path.realpath(__file__)), 'jsapps')
        dst_js_path = path.join(self.workspace.workdir, 'jsapps')
        os.makedirs(dst_js_path, exist_ok=True)
        for curr_file in ['bootstrap.min.css']:
            shutil.copyfile(path.join(src_js_path, curr_file), path.join(dst_js_path, curr_file))

        size_sec = self.wsize * self.report_params['tr']
        step_sec = self.wstep * self.report_params['tr']

        with open(path.join(dst_js_path, 'BatchSlidingWindow.html'), 'w') as writer:
            with open(path.join(src_js_path, 'BatchSlidingWindow.html')) as reader:
                content = reader.read()
                content = content.replace('{{window_size}}', str(self.wsize))
                content = content.replace('{{window_step}}', str(self.wstep))
                content = content.replace('{{size_sec}}', f'{size_sec:.02f}')
                content = content.replace('{{step_sec}}', f'{step_sec:.02f}')
                content = content.replace('{{rois_count}}', str(self.report_params['rois_count']))
                content = content.replace('{{edges_count}}', str(self.report_params['edges_count']))
                content = content.replace('{{subjects_count}}', str(self.report_params['subjects_count']))
                content = content.replace('{{windows_in_series}}', str(self.report_params['windows_in_series']))
                writer.write(content)

        self.app.signals_queue.put(('setTabsIndex', 3))
        self.app.signals_queue.put(('ui_open_page', path.join(dst_js_path, 'BatchSlidingWindow.html')))

    @staticmethod
    def show_html(app):
        report_file = path.join(app.workspace.workdir, 'jsapps', 'BatchSlidingWindow.html')
        if path.isfile(report_file):
            app.setTabsIndex(2)
            app.ui_open_page(report_file)
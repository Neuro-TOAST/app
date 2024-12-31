import os
import os.path as path
import numpy
import json
import statistics
import shutil
import BatchBase

class Table():
    def __init__(self):
        self.columns = []
        self.rows = []

    def add_row_dict(self, row):
        if not self.columns:
            self.columns = list(row.keys())
        else:
            assert(self.columns == list(row.keys()))
        self.rows.append(list(row.values()))

    def save(self, results_dir, session_id):
        os.makedirs(results_dir, exist_ok=True)
        with open(path.join(results_dir, f'results_{session_id}.tsv'), 'w') as writer:
            writer.write('\t'.join(self.columns) + '\n')
            for row in self.rows:
                writer.write('\t'.join(map(str, row)) + '\n')

class MergedJsTables:
    def __init__(self, workspace):
        self.workspace = workspace
        self.exported_columns = False
        with open(path.join(self.workspace.workdir, 'jsapps', f'analyse-states-data.js'), 'w') as writer:
            writer.write('let resultsData = {}\n')

    def write_session(self, session_id, table):
        with open(path.join(self.workspace.workdir, 'jsapps', f'analyse-states-data.js'), 'a+') as writer:
            if not self.exported_columns:
                self.exported_columns = True
                writer.write('let resultsColumns = ')
                writer.write(json.dumps(table.columns, indent=4))
                writer.write('\n')

            writer.write(f'resultsData[\'{session_id}\'] = ')
            writer.write(json.dumps(table.rows, indent=4))
            writer.write('\n')


class BatchAnalyseStates(BatchBase.BatchBase):
    def __init__(self, *parent):
        super().__init__(*parent)

    def load_states(self, subj_sess, clusters_count):
        states = numpy.loadtxt(subj_sess.subj_states(clusters_count), int)
        assert(numpy.max(states) <= clusters_count - 1 and numpy.min(states) >= 0)
        return list(states)


    def states_count(self, states, selected_count):
        '''Spocita cetnost jednotlivych stavu v celem zaznamu bez ohledu na prepinani,
        vysledek je vracen jako pomerna cast z cele delky zaznamu (suma hodnot je 1).'''
        result = {}
        for state in range(selected_count):
            result[f'count_{state}'] = states.count(state) / len(states)
        return result

    def states_interval_count(self, states, selected_count):
        '''Spocita cetnost vyskytu po sobe nasledujicich nemennych stavu,
        vysledek je vracen jako pocet bloku po sobe jdoucich skenu.'''
        buffer = []
        result = {}
        for state in states:
            if buffer and buffer[0] != state:
                result.setdefault(buffer[0], []).append(len(buffer))
                buffer = []
            buffer.append(state)
        if buffer:
            result.setdefault(buffer[0], []).append(len(buffer))
        return {f'interval_{state}': len(result.get(state, [])) for state in range(selected_count)}

    def states_interval_time(self, states, selected_count):
        '''Spocita prumernou delku po sobe nasledujicich nemennych stavu,
        vysledek je vracen jako pocet po sobe jdoucich skenu, pro cas v sekundach je treba nasobit TR.'''
        buffer = []
        result = {}
        for state in states:
            if buffer and buffer[0] != state:
                result.setdefault(buffer[0], []).append(len(buffer))
                buffer = []
            buffer.append(state)
        if buffer:
            result.setdefault(buffer[0], []).append(len(buffer))
        return {f'time_{state}': statistics.mean(result[state]) if state in result else 0 for state in range(selected_count)}

    def states_transitions_matrix(self, states):
        '''Spocita matici prechodu mezi stavy'''
        buffer = []
        result = {}
        for state in states:
            if len(buffer) > 0 and buffer[0] != state:
                result.setdefault(buffer[0], {}).setdefault(state, []).append(len(buffer))
                buffer = []
            buffer.append(state)
        if buffer:
            pass  # posledni stav ignoruji, nelze urcit, kam presel
        return result

    def print_transitions(self, transitions, count):
        matrix = numpy.zeros((count + 1, count + 1))
        for m in range(0, count):
            matrix[0, m + 1] = m
            matrix[m + 1, 0] = m
            for n in range(0, count):
                matrix[m + 1, n + 1] = len(transitions.get(m, {}).get(n, []))
        self.print(matrix)

    def flate_transitions(self, transitions, selected_count):
        out = {}
        for m in range(0, selected_count):
            for n in range(0, selected_count):
                out[f'from_{m}_to_{n}'] = len(transitions.get(m, {}).get(n, []))
        return out

    def exec(self, params, subjects_model):
        selected_count = int(params['analyse-states']['clusters-selected'])

        # for selected_count in list(range(2, 10)) + [selected_count_]:
        results = {}
        for session_spec in self.workspace.sessions_specs():
            results[session_spec.id()] = Table()

        param_labels = subjects_model.get_columns()
        for subj, row in subjects_model.get_active_rows():
            for session in self.workspace.sessions(subj):
                subj_data = dict(zip(param_labels, row))
                self.print(subj_data)

                self.print('')
                self.print(f' --- {subj} ---')
                states = self.load_states(session, selected_count)

                subj_line = {}
                subj_line.update(subj_data)

                result_states_count = self.states_count(states, selected_count)
                subj_line.update(result_states_count)
                # self.print('States count')
                # self.print(result_states_count)

                result_states_interval = self.states_interval_count(states, selected_count)
                subj_line.update(result_states_interval)
                # self.print('States interval count')
                # self.print(result_states_interval)

                result_states_time = self.states_interval_time(states, selected_count)
                subj_line.update(result_states_time)
                # self.print('States interval time')
                # self.print(result_states_time)


                transitions = self.states_transitions_matrix(states)
                result_transitions = self.flate_transitions(transitions, selected_count)
                subj_line.update(result_transitions)
                # self.print('Transitions')
                # self.print(result_transitions)

                self.print(subj_line)
                results[session.id()].add_row_dict(subj_line)

        merged_tables = MergedJsTables(self.workspace)
        for session_spec in self.workspace.sessions_specs():
            merged_tables.write_session(session_spec.id(), results[session_spec.id()])
            results[session_spec.id()].save(path.join(self.workspace.results_dir, f'states_{selected_count}'), session_spec.id())

        self.print('Analyse states finished')
        self.copy_js_app()

    def copy_js_app(self):
        src_js_path = path.join(path.dirname(path.realpath(__file__)), 'jsapps')
        dst_js_path = path.join(self.workspace.workdir, 'jsapps')
        os.makedirs(dst_js_path, exist_ok=True)
        for curr_file in ['BatchAnalyseStates.html', 'table_view.js', 'stats-ttest2.js', 'bootstrap.min.css']:
            shutil.copyfile(path.join(src_js_path, curr_file), path.join(dst_js_path, curr_file))

        self.app.signals_queue.put(('setTabsIndex', 3))
        self.app.signals_queue.put(('ui_open_page', path.join(dst_js_path, 'BatchAnalyseStates.html')))

    @staticmethod
    def show_html(app):
        report_file = path.join(app.workspace.workdir, 'jsapps', 'BatchAnalyseStates.html')
        if path.isfile(report_file):
            app.setTabsIndex(3)
            app.ui_open_page(report_file)

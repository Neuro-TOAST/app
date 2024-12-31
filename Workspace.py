import os.path as path
import json

class Session:
    def __init__(self, workspace, subj, session_name, fmri_file):
        self.workspace = workspace
        self._subj = subj
        self._name = session_name
        self._fmri_file = fmri_file

    def id(self):
        return self._name

    def name(self):
        return self._name

    def fmri_file(self):
        return self._fmri_file

    def sigs_file(self):
        return path.join(self.workspace.workdir, 'sigs', f'sigs_{self._subj}_{self.id()}.txt')

    def coverage_file(self):
        return path.join(self.workspace.workdir, 'sigs', f'coverage_{self._subj}_{self.id()}.txt')

    def sliding_conn_file(self):
        return path.join(self.workspace.workdir, 'sliding_conns', f'conns_{self._subj}_{self.id()}.txt')

    def subj_states(self, clusters_count):
        return path.join(self.workspace.states_dir, f'states_{clusters_count}', f'subj_label_{self._subj}_{self.id()}.txt')

class Workspace:
    def __init__(self, workspace_file):
        with open(workspace_file) as reader:
            src = json.loads(reader.read())
            if 'startup_pipeline' not in src or 'startup_subjects' not in 'startup_subjects' or 'workdir'  not in src or 'sessions_def' not in src:
                raise ValueError(f'Invalid format of workspace file {workspace_file}.')
            self.startup_pipeline = src['startup_pipeline']
            self.startup_subjects = src['startup_subjects']
            self.workdir = src['workdir']
            self.sessions_def = src['sessions_def']

    def save(self, dst_file):
        export = {
            'startup_pipeline': self.startup_pipeline,
            'startup_subjects': self.startup_subjects,
            'workdir': self.workdir,
            'sessions_def': self.sessions_def,
        }
        with open(dst_file, 'w') as writer:
            writer.write(json.dumps(export, indent=4))

    @property
    def states_dir(self):
        return path.join(self.workdir, 'states')

    @property
    def results_dir(self):
        return path.join(self.workdir, 'results')

    @property
    def src_jsapp_dir(self):
        return path.join(path.dirname(path.realpath(__file__)), 'jsapps')

    @property
    def dst_jsapp_dir(self):
        return path.join(self.workdir, 'jsapps')

    def sessions(self, subj):
        return [Session(self, subj, sname, sfile.replace('{subj}', subj)) for sactive, sname, sfile in self.sessions_def if sactive]

    def sessions_specs(self):
        return [Session(self, None, sname, None) for sactive, sname, sfile in self.sessions_def if sactive]

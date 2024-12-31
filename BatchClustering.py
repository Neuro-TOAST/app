import os
import os.path as path
import numpy
import time
import conn_clusters_score as clusters
import datahelpers
import subprocess
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score
import BatchBase

class KMeansResult:
    def __init__(self, labels, cluster_centers):
        self.labels_ = labels
        self.cluster_centers_ = cluster_centers
        self.n_iter_ = -1  # toto Matlab neuklada, umi byt ukecany, ale to bych musel zachytavat output a parsovat ho
        self.inertia_ = 0  # toto by slo dopocitat

class BatchClustering(BatchBase.BatchBase):
    def __init__(self, *parent):
        super().__init__(*parent)
        self.accuracy = []
        self.silhouette_means = []
        self.conns = None
        self.windows_per_subj = {}

    def save_subj_states(self, clusters_count):
        # ulozeni stavu prirazenych kazdemu subjektu
        offset = 0
        for subj_index, subj in enumerate(self.subjects_model.get_active_subjs()):
            for sess_index, session in enumerate(self.workspace.sessions(subj)):
                series_ind = slice(offset, offset + self.windows_per_subj[session.id()])
                k_clusters_filename = session.subj_states(clusters_count)
                os.makedirs(path.dirname(k_clusters_filename), exist_ok=True)
                numpy.savetxt(k_clusters_filename, self.kmeans_result.labels_[series_ind].astype(int), fmt='%i')
                offset += self.windows_per_subj[session.id()]

    def save_states(self, clusters_count):
        for m in range(clusters_count):
            state_filename = path.join(self.workspace.states_dir, f'states_{clusters_count}', 'state_{}_vector.txt'.format(m))
            numpy.savetxt(state_filename, self.kmeans_result.cluster_centers_[m,:])
            if self.local_params['source'] == 'connectivity':
                state_filename_matrix = path.join(self.workspace.states_dir, f'states_{clusters_count}', 'state_{}_matrix.txt'.format(m))
                numpy.savetxt(state_filename_matrix, datahelpers.vec_to_matrix(self.kmeans_result.cluster_centers_[m,:]))

    def kmeans_correlation(self, data, n_clusters, replicates, maxiter, empty='drop'):
        temp_dir = path.join(self.workspace.workdir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        script_filename = path.join(temp_dir, 'kmeans_corr.m')
        idx_filename = path.join(temp_dir, 'idx.txt')
        CP_filename = path.join(temp_dir, 'CP.txt')
        if path.isfile(idx_filename):
            os.unlink(idx_filename)
        if path.isfile(CP_filename):
            os.unlink(CP_filename)
        with open(script_filename, 'w') as writer:
            writer.write(f'nClusters = {n_clusters};\n')
            writer.write(f'replicates = {replicates};\n')
            writer.write(f'maxIter = {maxiter};\n')
            writer.write(f'empty = \'{empty}\';\n')
            writer.write('srcData = [\n')
            for line in data:
                writer.write('    ' + ' '.join([str(k) for k in line]) + '\n')
            writer.write('];\n')
            writer.write('\n\n')
            writer.write('''[idx, CP] = kmeans(srcData, nClusters, 'distance', 'correlation', 'replicates', replicates, 'empty', empty, 'maxiter', maxIter);\n''')
            writer.write(f'''writematrix(sortrows(CP), '{CP_filename}', 'Delimiter', 'tab')\n''')
            writer.write(f'''writematrix(idx, '{idx_filename}', 'Delimiter', 'tab')\n\n''')

        assert(not path.isfile(idx_filename))
        assert(not path.isfile(CP_filename))
        matlab_bin = 'e:/Apps/Matlab/R2022a/bin/matlab.exe'
        run_cmd = f'''"try, run('{script_filename}'), catch err, fprintf('%s / %s\\n', err.identifier, err.message), end, exit"'''
        cmd = [matlab_bin, '-nosplash', '-wait', '-batch', run_cmd]
        result = subprocess.run(cmd)
        assert(result.returncode == 0)
        assert(path.isfile(idx_filename))
        assert(path.isfile(CP_filename))
        idx = numpy.loadtxt(idx_filename)
        CP = numpy.loadtxt(CP_filename)
        assert(CP.shape[0] == n_clusters)
        assert(CP.shape[1] == data.shape[1])
        assert(len(CP.shape) == 2)
        assert(idx.shape[0] == data.shape[0])
        assert(len(idx.shape) == 1)
        return KMeansResult(labels=idx - 1, cluster_centers=CP)  # matlab indexuje od 1, python od 0, odecitam 1, abych normalizoval labely na indexovane od 0

    def calc_for_states_count(self, clusters_count):
        tinit = time.time()
        self.print(f'Running KMeans for {clusters_count} clusters')
        # n_init: Number of time the k-means algorithm will be run with different centroid seeds.
        #         The final results will be the best output of n_init consecutive runs in terms of inertia.
        # max_iter: Maximum number of iterations of the k-means algorithm for a single run.
        if self.local_params['source'] == 'signals':
            self.kmeans_result = self.kmeans_correlation(self.conns, clusters_count, 100, 1000)
        elif self.local_params['source'] == 'connectivity':
            self.kmeans_result = KMeans(n_clusters=clusters_count, random_state=0, n_init=1000, max_iter=100000).fit(self.conns)
        else:
            raise ValueError(f'Invalid value "{self.local_params["source"]}" for k-mean source. Supported only "connectivity" or "signals".')
        cluster_time = time.time() - tinit

        self.print(' - elapsed time: {:.1f} min'.format(cluster_time / 60))
        self.print(' - iterations: {}'.format(self.kmeans_result.n_iter_))
        self.print(' - distances from centers: {:.0f}'.format(self.kmeans_result.inertia_))
        self.accuracy.append((clusters_count, self.kmeans_result.inertia_))
        self.silhouette_means.append((clusters_count, silhouette_score(self.conns, self.kmeans_result.labels_)))
        self.print(' - elapsed time silhouette: {:.0f} s'.format(time.time() - tinit))

        self.save_subj_states(clusters_count)
        self.save_states(clusters_count)

        # vyber optimalniho poctu clusteru
        filename = path.join(self.workspace.workdir, 'jsapps', 'silhouette', f'kmeans-{clusters_count:02d}.png')
        os.makedirs(path.dirname(filename), exist_ok=True)
        silhouette_avg = clusters.plot_silhouette(filename, clusters_count, self.conns, self.kmeans_result.labels_)
        self.print(f' - the average silhouette_score: {silhouette_avg:.03f}\n')

    def calc_for_range(self, cfrom, cto):
        for k in range(cfrom, cto + 1):
            self.calc_for_states_count(k)

    def load_data(self):
        for subj in self.subjects_model.get_active_subjs():
            for session in self.workspace.sessions(subj):
                if self.local_params['source'] == 'connectivity':
                    subj_conn = numpy.loadtxt(session.sliding_conn_file(), float)
                elif self.local_params['source'] == 'signals':
                    subj_conn = numpy.loadtxt(session.sigs_file(), float)
                else:
                    raise ValueError(f'Invalid value "{self.local_params["source"]}" for k-mean source. Supported only "connectivity" or "signals".')
                self.windows_per_subj[session.id()] = subj_conn.shape[0]
                self.conns = subj_conn if self.conns is None else numpy.concatenate((self.conns, subj_conn))

    def generate_clusters_report(self):
        clusters.plot_silhouette_bars(path.join(self.workspace.workdir, 'jsapps', 'silhouette', 'comparison.png'), self.silhouette_means)
        with open(path.join(self.workspace.dst_jsapp_dir, 'BatchClustering.html'), 'w') as writer:
            with open(path.join(self.workspace.src_jsapp_dir, 'BatchClustering.html')) as reader:
                content = reader.read()
                content = content.replace('{{clusters_from}}', str(self.local_params['clusters-from']))
                content = content.replace('{{clusters_to}}', str(self.local_params['clusters-to']))
                writer.write(content)

    def exec(self, params, subjects_model):
        self.local_params = params['KMeans']
        self.print('Loading data for KMeans batch\n')
        self.subjects_model = subjects_model
        self.load_data()
        self.calc_for_range(self.local_params['clusters-from'], self.local_params['clusters-to'])
        self.print('KMeans finished')
        self.show_results()

    def show_results(self):
        self.generate_clusters_report()
        self.app.signals_queue.put(('setTabsIndex', 3))
        self.app.signals_queue.put(('ui_open_page', path.join(self.workspace.workdir, 'jsapps', 'BatchClustering.html')))

    @staticmethod
    def show_html(app):
        report_file = path.join(app.workspace.workdir, 'jsapps', 'BatchClustering.html')
        if path.isfile(report_file):
            app.setTabsIndex(3)
            app.ui_open_page(report_file)

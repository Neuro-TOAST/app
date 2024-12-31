import os
import os.path as path
import BatchBase
import numpy
import re
import json
from nilearn import datasets
from nilearn.maskers import NiftiLabelsMasker, NiftiSpheresMasker
from nilearn.masking import compute_epi_mask
from nibabel import Nifti1Image, save
from nilearn.image import load_img, resample_to_img, smooth_img


class Networks:
    def __init__(self, src_file):
        with open(src_file) as reader:
            seeds = json.load(reader)

            self.radius = seeds['spheres']['radius']
            self.coords = []
            self.labels = []
            for center in seeds['spheres']['centers']:
                if center['name'] in self.labels:
                    raise ValueError(f'Sphere name "{center["name"]}" is not unique.')
                self.coords.append(center['coords'])
                self.labels.append(center['name'])

            self.networks = []
            for network in seeds['networks']:
                indexes = [self.labels.index(ns) for ns in network['spheres']]
                self.networks.append({'name': network['name'], 'indices': indexes})


class BatchParcelation(BatchBase.BatchBase):
    def __init__(self, *parent):
        super().__init__(*parent)
        self.fmri_tr = None
        self.labels = []
        self.coverages = {}

    def exclude_rois(self, signals, excluded_indexes):
        '''
        signals: numpy, sloupce odpovidaji roi, excludovane sloupece se vynechaji
        excluded_indexes: indexy sloupcu, ktere se maji smazat
        '''
        return numpy.delete(signals, excluded_indexes, axis=1)

    def exclude_labels(self, labels, excluded_indexes):
        # TODO: labels se musi promazat konzistentne s rois
        output = []
        for index, label in enumerate(labels):
            if index not in excluded_indexes:
                output.append(label)
        return output

    def parcel_aal(self, subj_sess, fmri_file, excluded_indexes):
        '''Parceluje zadany fmri soubor, vrati prumerny signal danych oblasti.'''
        atlas = datasets.fetch_atlas_aal(data_dir=self.workspace.workdir)
        self.labels = self.exclude_labels(atlas.labels, excluded_indexes)

        # TODO: nemam zarucene, ze masker seradi mapu takovym zpusobem, jako je v atlasu, ve verzi 0.11.0.dev by mely byt nove seznamy, ktere to uvadeji
        # je treba to a) overit, b) implementovat po svem, c) prejit na novejsi verzi

        # 1.
        # maska pokryti signalu, zrejme mene prisna nez SPM
        # signal_mask = compute_epi_mask(fmri_file)
        brain_mask = 'q:/E/A/brainmask.nii'
        signal_mask = load_img(brain_mask)

        # 2.
        # samotny signal signal z fmri souboru, pouze z oblasti v masce
        masker = NiftiLabelsMasker(labels_img=atlas['maps'], mask_img=signal_mask, standardize=False, detrend=False, t_r=self.fmri_tr)
        # masker.fit(config_dev.fmri_file(subj))
        all_time_series = masker.fit_transform(fmri_file)  # pokud chci generovat report, musi se samostatne udelat fit & transform
        time_series = self.exclude_rois(all_time_series, excluded_indexes)

        # 3.
        # pokryti signalem, tj. pocet voxelu v kazde roi v signal mask (technicky vypocitano pomoci maskeru a sum strategie, maska musi byt 1/0)
        masker_coverage = NiftiLabelsMasker(labels_img=atlas['maps'], strategy='sum')
        rois_coverage = masker_coverage.fit_transform(signal_mask)
        rois_coverage = self.exclude_rois(rois_coverage, excluded_indexes)
        assert(rois_coverage.shape[1] == time_series.shape[1])

        # 4.
        # vypocet velikost rois, tj pocet voxelu (maska signalu se edituje na 1 (uplne vsude) a pak se aplikuje stejny masker jako vyse)
        # TODO: melo by jit aplikovat primo Nifti object, neni treba ukladat na disk
        ones_mask = Nifti1Image(numpy.ones(signal_mask.get_fdata().shape), signal_mask.affine, signal_mask.header)
        rois_size = masker_coverage.fit_transform(ones_mask)
        rois_size = self.exclude_rois(rois_size, excluded_indexes)
        assert(rois_size.shape[1] == time_series.shape[1])

        self.coverages[subj_sess] = list((rois_coverage / rois_size)[0,:])

        coverage = numpy.concatenate((rois_coverage, rois_size, rois_coverage / rois_size)).T
        return time_series, coverage

    def parcel_spheres(self, subj_sess, fmri_file, networks):
        '''Parceluje zadany fmri soubor, vrati prumerny signal danych oblasti.'''
        self.labels = networks.labels
        masker = NiftiSpheresMasker(seeds=networks.coords, radius=networks.radius, standardize=False, detrend=False, t_r=self.fmri_tr, allow_overlap=True)
        spheres_time_series = masker.fit_transform(fmri_file)

        time_series = numpy.empty([spheres_time_series.shape[0], len(networks.networks)])
        for k, network in enumerate(networks.networks):
            network_sigs = spheres_time_series[:,network['indices']]
            time_series[:,k] = numpy.nanmean(network_sigs, axis=1)

        return time_series, []

    def generate_coverage_report(self):
        out = 'let columns = [\n'
        out += '    { title:"Subject", field:"name", frozen:true },\n'
        for k, label in enumerate(self.labels):
            out += f'    {{ title:"{label} ({k+1})", field:"r{k+1}", sorter:"number", headerVertical:true }},\n'
        out += ']\n\n'

        out += 'let tabledata = [\n'
        for j, (subj, coverage) in enumerate(self.coverages.items()):
            out += f'    {{ name: "{subj}"'
            out += f', id: {j}'
            for k, value in enumerate(coverage):
                out += f', r{k+1}: {100 * value:.0f}'
            out += '},\n'
        out += ']\n'

        os.makedirs(path.join(self.workspace.workdir, 'reports'), exist_ok=True)
        with open(path.join(self.workspace.workdir, 'reports', 'table_data.js'), 'w') as writer:
            writer.write(out)

    def parse_excluded_indexes(self, input_str):
        indexes = set()
        for part in re.split(r'[,;\s]+', input_str.strip()):
            if part:  # prazdny vstup zpusobi prazdnou polozku
                assert(part.isnumeric())
                indexes.add(int(part))
        return list(indexes)

    def exec(self, params, subjects_model):
        local_params = params['Parcelation']
        self.print('Parcelation started')
        self.fmri_tr = params['fMRI']['TR']

        method = params['Parcelation']['Method']
        if method == 'AAL':
            excluded_indexes = self.parse_excluded_indexes(local_params['Excluded indexes'])
            # od 90 (indexovano od nuly) je v AAL mozecek, ten defaultne vyrazuji
            all_excluded_indexes = excluded_indexes + list(range(90, 116))
        elif method == 'Gao':
            networks = Networks('e:/Scripts/Dynamo/configs/Gao.networks.json')
        else:
            raise ValueError(f'Invalid parcelation method "{method}".')

        n = len(subjects_model.get_active_subjs())
        for k, subj in enumerate(subjects_model.get_active_subjs()):
            sn = len(self.workspace.sessions(subj))
            for s, session in enumerate(self.workspace.sessions(subj)):
                if path.isfile(session.fmri_file()):
                    if method == 'AAL':
                        time_series, coverage = self.parcel_aal(f'{subj}-{session.id()}', session.fmri_file(), all_excluded_indexes)
                    elif method == 'Gao':
                        time_series, coverage = self.parcel_spheres(f'{subj}-{session.id()}', session.fmri_file(), networks)
                    else:
                        raise ValueError(f'Invalid parcelation method "{method}".')

                    os.makedirs(path.dirname(session.sigs_file()), exist_ok=True)
                    numpy.savetxt(session.sigs_file(), time_series)
                    if method == 'AAL':
                        numpy.savetxt(session.coverage_file(), coverage)
                    self.print(f'({k+1}/{n}, {s+1}/{sn}) Saved aal signals for subject {subj} and session {session.name()}.')
                else:
                    self.print(f'({k+1}/{n}, {s+1}/{sn}) Fmri file {session.fmri_file()} for subject {subj} and session {session.name()} was not found.')
        self.generate_coverage_report()
        self.print('Parcelation finished')
        self.app.signals_queue.put(('setTabsIndex', 3))
        self.app.signals_queue.put(('ui_open_page', path.join(self.workspace.workdir, 'reports/index.html')))

    @staticmethod
    def show_html(app):
        report_file = path.join(app.workspace.workdir, 'reports/index.html')
        if path.isfile(report_file):
            app.setTabsIndex(3)
            app.ui_open_page(report_file)

# Technical Documentation of the fMRI TOAST Platform
## A Comprehensive Guide to Architecture, Data Models, and Computational Pipeline

This documentation describes the software architecture and mathematical-analytical implementations of a modular platform designed for processing functional magnetic resonance imaging (fMRI) data. The system is designed to extract, model, and statistically evaluate time-varying states of brain activity, fully integrating both the dynamic Functional Connectivity (dFC) approach and the analysis of instantaneous Co-activation Patterns (CAPs).

---

## 1. Global Architecture and Flow Control

The application is implemented in Python 3, utilizing an object-oriented design and a strict separation of configuration, presentation, and computational logic.

### 1.1. User Interface and Asynchronous Execution
* **PyQt6 GUI:** The main window (`MainWindow`) encapsulates visual components for project management, pipeline parameter configuration, and interactive result visualization using the integrated `QtWebEngineWidgets` web browser.
* **Multi-threaded Asynchronous Architecture:** To prevent freezing of the Graphical User Interface (GUI) during highly computationally demanding operations (e.g., spatial masking of 4D NIfTI files or iterative clustering), each step is executed in a separate asynchronous thread via the `threading` library.
* **Safe Inter-thread Communication:** Background computational modules are strictly prohibited from directly manipulating GUI elements. Communication is routed through a thread-safe `Queue` (`self.app.signals_queue`). The computational modules send standardized tuples to the queue, which the main GUI thread periodically retrieves and executes (e.g., printing to the log window, switching interface tabs, or rendering generated HTML reports).
* **`BatchBase` Class:** Serves as an abstract base class for all analytical modules. It ensures a unified mapping to the shared configuration workspace and encapsulates the `print()` method for safely passing text messages to the GUI log.

### 1.2. Tabular Data Models
* **MVC Architecture:** The management of subjects and fMRI sessions fully utilizes the Model-View-Controller architecture.
* **`SubjectsModel` Class:** Inherits from `QAbstractTableModel` and manages tabular data loaded from TSV files. It encapsulates the logic for checking (enabling/disabling) specific patients or controls, editing demographic data directly in the table, and exporting the updated state back to a TSV file.
* **`SessionsModel` Class:** Ensures dynamic mapping of fMRI sessions assigned to the current project, supporting interactive modifications of paths to source data.

---

## 2. Project Workspace and Declarative Pipeline

### 2.1. Workspace Management and Persistence
All operations are contextually bound to a `Workspace` object, which is initialized from a structured JSON configuration file. This object ensures:
* Persistent storage of paths to the working directory (`workdir`), subject definition files, and fMRI session structures.
* Automatic and deterministic generation of paths for intermediate and final files within a standardized directory structure.
* **Extracted BOLD signals:** `workdir/sigs/sigs_{subj}_{session}.txt`
* **Gray matter coverage (AAL):** `workdir/sigs/coverage_{subj}_{session}.txt`
* **Dynamic connectivity matrices:** `workdir/sliding_conns/conns_{subj}_{session}.txt`
* **Assigned state sequences:** `workdir/states/states_{K}/subj_label_{subj}_{session}.txt`

### 2.2. Declarative Parameter Definition
The configuration tree of the entire pipeline is defined using reusable components of the `UIConfigItem` class in `pipeline.py`. This approach enables:
* Input type validation directly at the definition level (support for integers, floats, text strings, and ComboBoxes).
* Direct mapping of a specific tree node (e.g., `Parcelation` or `KMeans`) to an executable batch class via the `runnable` property. Custom parameters are then passed to the computational modules as a structured dictionary.

---

## 3. Computational Pipeline Modules

### 3.1. Spatial Parcellation Module (`BatchParcelation.py`)
This module transforms 4D NIfTI fMRI data (spatiotemporal fMRI volumes) into 2D time series of mean BOLD signal amplitudes for defined Regions of Interest (ROIs). The method choice is governed by the `Method` parameter in the configuration.

**Method A: Anatomical Parcellation (`Method = 'AAL'`)**
* **Implementation:** Utilizes the `NiftiLabelsMasker` class from the `nilearn` library.
* **Algorithm:** Loads a standardized anatomical atlas (AAL) and calculates the mean BOLD signal across all time points (TRs) for each spatially defined ROI. Allows selective filtering via `Selected ROIs` and `Excluded indexes` parameters.
* **ROI Coverage Analysis:** Generates a binary mask of the subject's actual signal using `compute_epi_mask` and compares it with the atlas mask. The result is a coverage matrix defining the percentage volume of each ROI that was actually scanned and free of artifacts/signal drop-outs. An interactive HTML report is generated from this data.

**Method B: Spherical Parcellation of Functional Networks (`Method = 'Gao'`)**
* **Implementation:** Utilizes the `NiftiSpheresMasker` class from `nilearn`.
* **Algorithm:** Loads an external JSON configuration defining specific functional networks (e.g., Default Mode Network, Salience Network). For each defined network center, it extracts a signal from a sphere of a fixed radius in MNI space. This targets functionally validated nodes independently of macroanatomical boundaries.

---

### 3.2. Sliding Window Analysis Module (`BatchSlidingWindow.py`)
To realize dynamic Functional Connectivity (dFC), this module transforms static time series into sequences of connectivity matrices.

* **Sliding Window Algorithm:** The input 2D signal matrix (`time_points x ROI`) is segmented using a rectangular time window of length $W$ with a step size $S$.
* **Connectivity Calculation:** In each window, a symmetric matrix of linear dependencies is calculated using the Pearson correlation coefficient ($\rho$):
$$
\rho_{X,Y} = \frac{\operatorname{cov}(X,Y)}{\sigma_X \sigma_Y}
$$
The application intentionally does not perform a Fisher Z-transformation (preserving the properties of the original distribution) and keeps a value of 1 on the diagonal.
* **Vectorization:** Given the symmetry of the correlation matrix, only the upper triangle above the diagonal is extracted. The matrix of size `ROI x ROI` is transformed into a 1D vector of length $L$:
$$
L = \frac{\text{ROI} \cdot (\text{ROI} - 1)}{2}
$$
* **Output:** Generates a `number_of_windows x L` matrix for each session, representing the trajectory of network architecture over time.

---

### 3.3. Dual-Mode Clustering Engine and Evaluation (`BatchClustering.py`)
This module is the core analytical engine. It enables the extraction of recurring states and implements two fundamentally different neuroscientific approaches based on the `source` parameter.

**Mode A: Connectivity States (`source = 'connectivity'`)**
* **Input:** dFC vectors from the sliding windows.
* **Algorithm:** Concatenates vectors from all windows across all active subjects into a global matrix. Executes the native K-Means algorithm from `scikit-learn` using standard Euclidean distance.
* **Output:** Centroids represent average dFC states. The module saves these states as raw vectors and reconstructs them into square matrices for topological connectivity visualization.

**Mode B: Co-activation Patterns (`source = 'signals'`)**
* **Input:** Raw BOLD signal amplitude time series (frame-wise data). This bypasses the sliding window entirely.
* **MATLAB Automation:** Clustering instantaneous fMRI amplitudes requires specific spatial normalization and distance metrics. The module dynamically writes a `kmeans_corr.m` script to a temporary directory, serializes the input data, and executes a background MATLAB binary.
* **Correlation Distance:** The MATLAB calculation uses the correlation distance metric. For two spatial vectors $u$ and $v$ (amplitudes across all ROIs at a given time), the distance is:
$$
d(u,v) = 1 - \frac{(u - \bar{u})(v - \bar{v})^T}{\|u - \bar{u}\|_2 \|v - \bar{v}\|_2}
$$
This effectively groups spatial patterns based on structural similarity (shape), not absolute amplitude size.
* **Output:** The extracted centroids in this mode directly represent the Co-activation Patterns (CAPs).

**Mathematical Validation Apparatus**
The module evaluates data structure across a specified range of clusters $K \in \langle C_{from}, C_{to} \rangle$ and calculates advanced validation metrics:

* **SSE (Sum of Squared Errors / Inertia):** Expresses intra-cluster cohesion as the sum of squared distances of samples to their assigned centroids.
* **Point Biserial Correlation (PBC):** Measures the agreement between data topology and the resulting clustering:
$$
r_{pbc} = \frac{M_1 - M_0}{s_d} \sqrt{\frac{n_1 n_0}{n(n-1)}}
$$
* **Dunn Index:** The ratio of the minimum inter-cluster distance to the maximum intra-cluster variance:
$$
D = \frac{\min_{i \neq j} d(c_i, c_j)}{\max_{m} \text{diameter}(m)}
$$
* **Davies-Bouldin Index:** The average maximum ratio of intra-cluster dispersion to centroid distance for each cluster:
$$
DB = \frac{1}{K} \sum_{i=1}^K \max_{j \neq i} \left( \frac{\bar{d}_i + \bar{d}_j}{d(c_i, c_j)} \right)
$$
* **Calinski-Harabasz Index (Variance Ratio Criterion):** The ratio of between-cluster dispersion ($SSB$) to within-cluster dispersion ($SSW$):
$$
CH = \frac{\operatorname{Tr}(SSB)}{\operatorname{Tr}(SSW)} \times \frac{N - K}{K - 1}
$$
* **Silhouette Analysis:** Calculates average Silhouette scores across data and plots cluster silhouettes to PNG graphs for visual detection of the optimal "elbow".

---

### 3.4. Temporal State Dynamics Analysis Module (`BatchAnalyseStates.py`)
After assigning state sequences to individual time points or windows, this module performs microstructural analysis to extract clinically interpretable biomarkers.

* **Fractional Time (Occupancy Rate):** The percentage of total scan time a subject spent in a specific state.
* **Mean Dwell Time:** The average length of consecutive, unchanging segments in a specific state (measured in TRs or windows).
* **Transition Matrix (Transition Probabilities):** A directional matrix specifying empirical probabilities of switching from state $i$ to state $j$.
* **Statistical Export and Interactive Web App:** Metrics are exported to TSV files for external statistical software. The module also generates an interactive HTML application (`BatchAnalyseStates.html`) with embedded JavaScript (`stats-ttest2.js`). This allows users to define subject cohorts and run un-paired Two-sample t-tests directly in the UI to determine $p$-values for group differences.

---

## 4. Data Flow Summary

1.  **Input:** Raw fMRI 4D data (.nii) + TSV subject definitions + JSON workspace.
2.  **Phase 1 (`BatchParcelation`):** Dimensionality reduction. Output: Text matrices of BOLD amplitude time series.
3.  **Phase 2 (Optional for dFC - `BatchSlidingWindow`):** Calculation of rolling Pearson correlations. Output: Connectivity vectors over time.
4.  **Phase 3 (`BatchClustering`):**
    * *Connectivity mode:* K-Means (Euclidean) on window vectors $\rightarrow$ Output: Connectivity states.
    * *Signals mode:* MATLAB K-Means (Correlation distance) on BOLD frames $\rightarrow$ Output: Co-activation Patterns (CAPs).
    * *Validation:* Comprehensive HTML report with five metrics and Silhouette plots.
5.  **Phase 4 (`BatchAnalyseStates`):** Calculation of Fractional Time, Mean Dwell Time, and Transition matrices. Output: TSV exports and interactive HTML app for group t-tests.

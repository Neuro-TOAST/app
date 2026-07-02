# fMRI TOAST Platform
### Time-varying Brain State Analysis Tool

---

## 1. Introduction

**fMRI TOAST** is an open-source, configuration-driven analytical platform developed in Python 3 for advanced processing of functional Magnetic Resonance Imaging (fMRI) data.

### What is it for?
Traditional fMRI analysis typically treats brain connectivity as a static network, averaging signals over an entire 10-to-15-minute scan. However, the human brain is inherently dynamic—constantly switching between different network configurations to process thoughts, tasks, and emotions.

fMRI TOAST allows neuroscientists, clinicians, and researchers to break beyond static limitations and capture these fleeting, transient **"brain states"** as they evolve over time. It provides a complete, automated pipeline that takes raw 4D neuroimaging scans and translates them into clean, interactive, and statistically testable insights.

### Key Methodologies Supported:
1. **Dynamic Functional Connectivity (dFC / Sliding Window):** Analyzes how statistical correlations between brain regions change over time by sliding a moving time-window across the signal.
2. **Co-activation Patterns (CAPs):** Investigates frame-by-frame, instantaneous spatial patterns of brain activity, capturing high-amplitude events that time-averaged methods often smooth out.

Whether you are studying fundamental cognitive science or searching for neuroimaging biomarkers in clinical cohorts (e.g., Healthy Controls vs. Alzheimer's Disease or Mild Cognitive Impairment), fMRI TOAST streamlines your entire workflow.

---

## 2. Core Features

The platform processes your neuroimaging datasets through a sequential, modular pipeline:

* **Parcellation (`BatchParcelation`):** Reduces the dimensionality of raw 4D NIfTI files (`.nii`) by extracting 1D/2D blood-oxygen-level-dependent (BOLD) signal time series using anatomical atlases (e.g., AAL) or custom spherical Regions of Interest (ROIs).
* **Sliding Window (`BatchSlidingWindow`):** Computes rolling Pearson correlation matrices across moving time windows to track dynamic network connectivity (dFC).
* **Clustering (`BatchClustering`):** Aggregates time series data across all active subjects and applies K-Means clustering (using Euclidean distance for dFC in Python, or Correlation distance via an integrated MATLAB engine for CAPs). It automatically generates validation metrics (Silhouette, Dunn, Davies-Bouldin indices).
* **State Analysis (`BatchAnalyseStates`):** Computes advanced temporal metrics of brain state dynamics, including:
    * *Fractional Time:* The proportion of total scan time a subject spends in a specific brain state.
    * *Mean Dwell Time:* The average consecutive time a subject remains in a state before switching.
    * *Transition Matrices:* The empirical probability of transitioning from state *i* to state *j*.

---

## 3. Architecture and Interfaces

fMRI TOAST is designed with a strict separation of configuration, presentation, and computation logic, offering two ways to operate:

1.  **Graphical User Interface (GUI):** A desktop application built with PyQt6 (`app.py`). It utilizes a multi-threaded asynchronous architecture, ensuring the UI remains perfectly responsive during heavy computations. It features an integrated web browser view for immediate visualization of generated reports.
2.  **Command Line Interface (CLI):** A script-based entry point (`cmd_run.py`) built for automation, making it ideal for running large-scale sequential batch processing in the background or on high-performance computing servers.

---

## 4. Quick Start / How to Use

### Running via GUI
To open the interactive desktop application, execute:
```bash
python app.py
```

### Running via CLI
To run the automated analytical pipeline directly from the command line, provide the paths to the three required configuration files:
```bash
python cmd_run.py <workspace_config.json> <pipeline_config.json> <subjects_definition.tsv>
```

* **Subjects Definition (`.tsv`):** A tab-separated file specifying which subjects to include (`active` column) and their clinical group classifications (e.g., Controls vs. Patients).
* **Pipeline Configuration (`.json`):** Contains mathematical and hyperparameter variables (such as TR length, parcellation selection, and the cluster range $K$ for K-Means).
* **Workspace Configuration (`.json`):** Maps input paths, paths to your raw `.nii` files using placeholders (e.g., `{subj}`), and sets the target output directory (`workdir`).

---

## 5. Detailed Documentation

For a deep dive into the platform, please refer to the standalone markdown documentation files included in this repository:

* 📄 **[doc.md](doc.md):** **Technical Documentation.** Detailed software architecture diagrams, data models, mathematical formulations, and an in-depth breakdown of the computational phases.
* 📄 **[usage.md](usage.md):** **User & Configuration Guide.** Step-by-step instructions for command-line execution, exhaustive breakdowns of JSON/TSV configuration schemas, and an overview of the output directory structure (`sigs`, `sliding_conns`, `results`, `jsapps`).

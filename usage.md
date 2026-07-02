# fMRI Analytical Platform: Command Line Usage Guide

This guide details how to configure and execute the fMRI analytical platform from the command line. It assumes that the application, along with all its dependencies (Python, nilearn, scikit-learn, PyQt6, MATLAB engine, etc.), is already successfully installed on your system.

The pipeline is entirely configuration-driven. To run an analysis, you need to prepare three main files:
1. **Subjects Definition File (`.tsv`)**: Lists the participants and their clinical groups.
2. **Pipeline Configuration File (`.json`)**: Defines the mathematical and analytical parameters (TR, parcellation method, clustering parameters).
3. **Workspace Configuration File (`.json`)**: Binds the input data, pipeline configuration, and output directories together.

---

## 1. Preparing the Configuration Files

### 1.1. Subjects Definition File (`.tsv`)
This file is a Tab-Separated Values (TSV) document that dictates which subjects will be processed and how they are grouped for later statistical analysis.

**Format Requirements:**
* Must contain headers: `active`, `participant_id`, `group`.
* `active`: `1` to include the subject in the current run, `0` to skip them.
* `participant_id`: The exact string used to identify the subject in your filesystem (this will replace the `{subj}` placeholder in your workspace paths).
* `group`: An integer or string representing the clinical cohort (e.g., `1` for Healthy Controls, `2` for Mild Cognitive Impairment).

**Example: `clinical_dataset.tsv`**
```tsv
active	participant_id	group
1	sub-4691B	1
1	sub-4957A	1
1	sub-5042A	2
0	sub-5589A	2
```

### 1.2. Pipeline Configuration File (`.json`)
The pipeline configuration defines the exact scientific parameters used during the run. You can configure the pipeline to perform standard **Dynamic Functional Connectivity (Sliding Window)** or **Co-activation Patterns (CAPs)** simply by changing the `"source"` parameter in the `KMeans` block.

**Example A: Dynamic Functional Connectivity (Sliding Window) Configuration**

```json
{
    "fMRI": {
        "TR": "0.980"
    },
    "Parcelation": {
        "Method": "Gao",
        "Selected ROIs": "",
        "Excluded indexes": ""
    },
    "sliding-window": {
        "wsize": "50",
        "wstep": "10"
    },
    "KMeans": {
        "source": "connectivity",
        "clusters-from": "2",
        "clusters-to": "12"
    },
    "analyse-states": {
        "clusters-selected": "2"
    }
}
```

**Example B: Co-activation Patterns (CAPs) Configuration**

Notice that for CAPs, the `KMeans` `"source"` is set to `"signals"`. The sliding window parameters are kept in the file for schema consistency but are functionally bypassed during the CAPs clustering phase.

```JSON
{
    "fMRI": {
        "TR": "0.980"
    },
    "Parcelation": {
        "Method": "Gao",
        "Excluded indexes": ""
    },
    "sliding-window": {
        "wsize": "50",
        "wstep": "10"
    },
    "KMeans": {
        "source": "signals",
        "clusters-from": "2",
        "clusters-to": "12"
    },
    "analyse-states": {
        "clusters-selected": "2"
    }
}
```

**Complete Parameter Reference**

Based on the `pipeline.py` schema, here are all the possible configurations:

- `fMRI.TR` *(float)*: Repetition Time of the fMRI scan in seconds.
- `Parcelation.Method` *(string)*: Choose `"AAL"` for anatomical atlas-based extraction or `"Gao"` for functional spherical networks.
- `Parcelation.Selected ROIs` *(string, optional)*: Specific ROI labels to include. Leave blank to include all.
- `Parcelation.Excluded indexes` *(string, optional)*: Specific numerical indexes of ROIs to exclude (e.g., artifact-prone regions).
- `sliding-window.wsize` *(integer)*: Length of the sliding window measured in TRs (time points).
- `sliding-window.wstep` *(integer)*: The step size to advance the sliding window, measured in TRs.
- `KMeans.source` *(string)*: `"connectivity"` (dFC states via Euclidean distance) or `"signals"` (CAPs via Correlation distance in MATLAB).
- `KMeans.clusters-from` *(integer)*: The minimum number of states ($K$) to evaluate for validation metrics.
- `KMeans.clusters-to` *(integer)*: The maximum number of states ($K$) to evaluate.
- `analyse-states.clusters-selected` *(integer)*: The default number of states to visualize. *(Note: When running via the command line script provided below, the analysis module iterates over the entire `clusters-from` to `clusters-to` range automatically, overriding this default).*

### 1.3. Workspace Configuration File (`.json`)

The workspace JSON acts as the master registry. It points to your TSV and Pipeline files, defines where output should be saved, and maps the location of the raw NIfTI files.

**Crucial Note on Paths:** The `sessions_def` block uses a wildcard placeholder `{subj}`. The pipeline will automatically replace `{subj}` with the `participant_id` from your TSV file to locate individual patient files.

**Example:** `my_workspace.json`

```JSON
{
    "startup_pipeline": "/path/to/my/configs/sw.pipeline.json",
    "startup_subjects": "/path/to/my/configs/clinical_dataset.tsv",
    "workdir": "/path/to/output_results/experiment_01",
    "sessions_def": [
        [
            true,
            "swtse",
            "/path/to/raw_data/dataset_C/{subj}/swtse_r.nii"
        ]
    ]
}
```

- `startup_pipeline`: Absolute path to your pipeline `.json` file.
- `startup_subjects`: Absolute path to your subjects `.tsv` file.
- `workdir`: Absolute path to an empty directory where all results, HTML reports, extracted signals, and matrices will be generated.
`sessions_def`: A list of sessions. Each session is an array containing:
    1. `true` / `false` (whether this session is active for processing)
    2. A string ID for the session (e.g., `"swtse"`, `"rest"`)
    3. The path to the processed NIfTI file containing the `{subj}` wildcard.

## 2. Launching the Pipeline

The core logic for launching the batch processes is contained in `cmd_run.py`. Since `cmd_run.py` provides a `main()` function rather than executing directly upon call, the simplest way to run a specific configuration is to create a tiny "launcher" script.

### Step 2.1: Create a Launcher Script

Create a new file named `run_single.py` in the same directory as your application scripts:

```Python
# run_single.py
import cmd_run

# Define paths to your specific configuration files
workspace_file = "my_workspace.json"
pipeline_file = "sw.pipeline.json"
subjects_file = "clinical_dataset.tsv"

print("Starting fMRI Pipeline Processing...")
cmd_run.main(workspace_file, pipeline_file, subjects_file)
print("Processing Completed Successfully.")
```

*(Note: Advanced users who want to run mass batches over multiple combinations of datasets and methods can loop through an array of configurations and call `cmd_run.main()` sequentially, similar to the logic found in `toast_processing.py`).*

### Step 2.2: Execute via Terminal

Open your command line interface (Terminal, Command Prompt, or PowerShell), navigate to the folder containing your application, activate your Python virtual environment (if you are using one), and execute the script

```Bash
python run_single.py
```

## 3. Understanding the Execution Flow and Outputs

Once you launch the script, the platform will process the data in a strict sequence. You will see console outputs prefixed with `(print)` or similar logging messages indicating the progress.

1. **Parcellation (`BatchParcelation`):** Reads the 4D `.nii` files and extracts the 1D/2D text time series into `[workdir]/sigs/`.
2. **Sliding Window (`BatchSlidingWindow`):** (Executes always, but only its outputs are used if `KMeans.source` == "connectivity"). Computes dynamic Pearson matrices and saves them to `[workdir]/sliding_conns/`.
3. **Clustering (`BatchClustering`):** Aggregates data across all active subjects. Calculates K-Means states for every $K$ between `clusters-from` and `clusters-to`. Generates validation scores (Silhouette, Dunn, Davies-Bouldin) and an interactive HTML report in `[workdir]/jsapps/`.
4. **State Analysis (`BatchAnalyseStates`):** The command line script automatically loops through every $K$ value in your defined range. For each $K$, it calculates Fractional Time, Mean Dwell Time, and Transition matrices. Results are saved as `.tsv` files in `[workdir]/results/` and an interactive browser-based statistical tool is generated in `[workdir]/jsapps/`.

### Post-Processing Check
To explore your results, navigate to the `workdir` you defined in your workspace JSON. Open the HTML files located inside the `jsapps` folder in any modern web browser to view the generated interactive reports and perform immediate t-test statistics on your data cohorts.


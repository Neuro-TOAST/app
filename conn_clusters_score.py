import os
import os.path as path
import numpy
import json
import time
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy

def plot_silhouette_bars(filename, avgs):
    x = []
    heights = []
    labels = []
    for index, avg in enumerate(avgs):
        x.append(index)
        heights.append(avg[1])
        labels.append(avg[0])

    plt.figure(figsize=(10, 4))
    plt.title('Optimal clusters count according silhouette average')
    plt.grid(True, color='lightgrey', alpha=0.5)
    plt.bar(x, heights)
    plt.xticks(x, labels)
    plt.ylabel('Clusters count')
    plt.ylabel('Silhouette average')

    os.makedirs(path.dirname(filename), exist_ok=True)
    plt.savefig(filename)
    plt.close()

def plot_silhouette(filename, n_clusters, X, cluster_labels):
    fig, (ax1) = plt.subplots(1, 1)
    fig.set_size_inches(10, 7)

    silhouette_avg = silhouette_score(X, cluster_labels)
    # print("For n_clusters =", n_clusters, "The average silhouette_score is :", silhouette_avg)

    # Compute the silhouette scores for each sample
    sample_silhouette_values = silhouette_samples(X, cluster_labels)

    y_lower = 10
    for i in range(n_clusters):
        # Aggregate the silhouette scores for samples belonging to
        # cluster i, and sort them
        ith_cluster_silhouette_values = sample_silhouette_values[cluster_labels == i]

        ith_cluster_silhouette_values.sort()

        size_cluster_i = ith_cluster_silhouette_values.shape[0]
        y_upper = y_lower + size_cluster_i

        color = cm.nipy_spectral(float(i) / n_clusters)
        ax1.fill_betweenx(numpy.arange(y_lower, y_upper), 0, ith_cluster_silhouette_values, facecolor=color, edgecolor=color, alpha=0.7)

        # Label the silhouette plots with their cluster numbers at the middle
        ax1.text(-0.05, y_lower + 0.5 * size_cluster_i, str(i))

        # Compute the new y_lower for next plot
        y_lower = y_upper + 10  # 10 for the 0 samples

    ax1.set_title("The silhouette plot for the various clusters, avg={:.2f}.".format(silhouette_avg))
    ax1.set_xlabel("The silhouette coefficient values")
    ax1.set_ylabel("Cluster label")

    # The vertical line for average silhouette score of all the values
    ax1.axvline(x=silhouette_avg, color="red", linestyle="--")

    ax1.set_yticks([])  # Clear the yaxis labels / ticks
    ax1.set_xticks([-0.1, 0, 0.2, 0.4, 0.6, 0.8, 1])

    plt.suptitle(("Silhouette analysis for KMeans clustering on sample data with n_clusters = %d" % n_clusters), fontsize=14, fontweight='bold')

    os.makedirs(path.dirname(filename), exist_ok=True)
    plt.savefig(filename)
    plt.close()

    return silhouette_avg

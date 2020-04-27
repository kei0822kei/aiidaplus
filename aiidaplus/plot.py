#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
plot
----
provide various kinds of plot
"""

import numpy as np
from copy import deepcopy
from matplotlib import pyplot as plt
from phonopy.phonon.band_structure import BandPlot as PhonopyBandPlot
from phonopy.phonon.band_structure import get_band_qpoints_and_path_connections


# DEFAULT_COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']
DEFAULT_COLORS = ['r', 'b', 'm', 'y', 'g', 'c']
DEFAULT_MARKERS = ['o', 'v', ',', '^', 'h', 'D', '<', '*', '>', 'd']


def line_chart(ax, xdata, ydata, xlabel, ylabel, label=None, **kwargs):
    """
    plot line chart in ax

    Args:
        ax : matplotlib.axes._subplots.AxesSubplot
            ax made from 'fig.subplot(xxx)'
        xdata : list
            x data
        ydata : list
            y data
        xlabel : str
            x label
        ylabel : str
            y label
        kwargs: c, marker, facecolor

    Returns:
        dict: description

    Raises:
        ValueError: description

    Examples:
        description

        >>> print_test ("test", "message")
          test message

    Note:
        description
        Parameters
        ----------

        Returns
        -------
        ax : matplotlib.axes._subplots.AxesSubplot
            plotted ax

        Notes
        -----
    """
    if 'c' in kwargs.keys():
        c = kwargs['c']
    else:
        c_num = len(ax.get_lines()) % len(DEFAULT_COLORS)
        c = DEFAULT_COLORS[c_num]

    if 'marker' in kwargs.keys():
        marker = kwargs['marker']
    else:
        marker_num = len(ax.get_lines()) % len(DEFAULT_MARKERS)
        marker = DEFAULT_MARKERS[marker_num]

    if 'facecolor' in kwargs.keys():
        facecolor = kwargs['facecolor']
    else:
        facecolor_num = len(ax.get_lines()) % 2
        if facecolor_num == 0:
            facecolor = 'white'
        else:
            facecolor = c

    raw = np.array([xdata, ydata])
    idx = np.array(xdata).argsort()
    sort = raw[:,idx]
    ax.plot(sort[0,:], sort[1,:], linestyle='--', linewidth='0.5', c=c, label=label)
    ax.scatter(sort[0,:], sort[1,:], facecolor=facecolor, marker=marker, edgecolor=c)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

def line_chart_group(ax, xdata, ydata, xlabel, ylabel, gdata, glabel, **kwargs):
    uniques = np.unique(gdata)
    for unique in uniques:
        idxes = [ idx for idx in range(len(gdata)) if np.isclose(gdata[idx], unique) ]
        label = '{}: {}'.format(glabel, unique)
        line_chart(ax, np.array(xdata)[idxes], np.array(ydata)[idxes], xlabel, ylabel, label, **kwargs)
    ax.legend()


class BandPlot(PhonopyBandPlot):

    def __init__(self, ax, band_labels, distances, frequencies, connections, xscale=None):
        super().__init__(axs=[ax])
        self.band_labels = band_labels
        self.distances = distances
        self.frequencies = frequencies
        self.connections = connections
        self.ax = ax
        if xscale is None:
            self.set_xscale_from_data(self.frequencies, self.distances)
        else:
            self.xscale = xscale
        self.decorate(self.band_labels,
                      self.connections,
                      self.frequencies,
                      self.distances)

    def plot_band(self, color='r'):
        c_num = len(self.ax.get_lines()) % len(DEFAULT_COLORS)
        count = 0
        distances_scaled = [d * self.xscale for d in self.distances]
        for d, f, c in zip(distances_scaled,
                           self.frequencies,
                           self.connections):
            self.ax.plot(d, f, color=color, linewidth=1)
            self.ax.axvline(d[-1], color='k', linestyle='dashed', linewidth=0.5)
            if not c:
                count += 1

def _revise_band_labels(band_labels):
    new = []
    for i, l in enumerate(band_labels):
        if 'GAMMA' in l:
            new.append("$" + l.replace("GAMMA", r"\Gamma") + "$")
        elif 'SIGMA' in l:
            new.append("$" + l.replace("SIGMA", r"\Sigma") + "$")
        elif 'DELTA' in l:
            new.append("$" + l.replace("DELTA", r"\Delta") + "$")
        elif 'LAMBDA' in l:
            new.append("$" + l.replace("LAMBDA", r"\Lambda") + "$")
        else:
            new.append(r"$\mathrm{%s}$" % l)
    return new

def _run_band_calc(phonon, band_labels, segment_qpoints, is_auto):
    if is_auto:
        print("# band path is set automalically")
        phonon.auto_band_structure(plot=False,
                               write_yaml=False,
                               with_eigenvectors=False,
                               with_group_velocities=False,
                               npoints=101)
    else:
        qpoints, connects = get_band_qpoints_and_path_connections(
                segment_qpoints, npoints=101,
                rec_lattice=np.linalg.inv(phonon.get_primitive().cell))
        phonon.run_band_structure(paths=qpoints,
                                  with_eigenvectors=False,
                                  with_group_velocities=False,
                                  is_band_connection=False,
                                  path_connections=connects,
                                  labels=band_labels,
                                  is_legacy_plot=False)
    # return phonon

def band_plot(ax,
              phonon,
              band_labels=None,
              segment_qpoints=None,
              is_auto=False,
              color='r'):
    seg_qpoints = [segment_qpoints]  # not split band figure
    # phonon = _run_band_calc(phonon=phonon,
    #                         band_labels=band_labels,
    #                         segment_qpoints=seg_qpoints,
    #                         is_auto=is_auto)
    _run_band_calc(phonon=phonon,
                   band_labels=band_labels,
                   segment_qpoints=seg_qpoints,
                   is_auto=is_auto)
    b_labels = phonon.band_structure.labels
    distances = phonon.band_structure.get_distances()
    frequencies = phonon.band_structure.get_frequencies()
    connections = phonon.band_structure.path_connections
    bp = BandPlot(ax,
                  b_labels,
                  distances,
                  frequencies,
                  connections)
    bp.plot_band(color=color)

def band_plots(ax,
              phonons,
              band_labels=None,
              segment_qpoints=None,
              is_auto=False,
              color=None):

    def _revise_distances(distances, base_distances):
        segment_lengths = []
        for ds in [distances, base_distances]:
            lengths = []
            init = 0
            for d in ds:
                lengths.append(d[-1]-init)
                init = d[-1]
            segment_lengths.append(lengths)
        ratios = np.array(segment_lengths)[0] /  np.array(segment_lengths)[1]
        revised = []
        seg_start = 0
        for i, distance in enumerate(distances):
            if i == 0:
                revised.append(distance / ratios[i])
            else:
                revised.append(seg_start+(distance-distances[i-1][-1]) / ratios[i])
            seg_start = revised[-1][-1]
        return revised

    for i, phonon in enumerate(phonons):
        if i == 0:
            # ph = _run_band_calc(phonon=phonon,
            #                     band_labels=band_labels,
            #                     segment_qpoints=seg_qpoints,
            #                     is_auto=is_auto)
            _run_band_calc(phonon=phonon,
                           band_labels=band_labels,
                           segment_qpoints=[segment_qpoints],  # not split band figure
                           is_auto=is_auto)
            base_primitive_matrix = phonon.get_primitive_matrix()
        else:
            primitive_matrix = phonon.get_primitive_matrix()
            fixed_segment_qpoints = \
                    np.dot(primitive_matrix.T,
                           np.dot(np.linalg.inv(base_primitive_matrix.T), segment_qpoints.T)).T
            _run_band_calc(phonon=phonon,
                           band_labels=band_labels,
                           segment_qpoints=[fixed_segment_qpoints],
                           is_auto=is_auto)

        band_labels = phonon.band_structure.labels
        labels = _revise_band_labels(band_labels)
        print(labels)
        distances = phonon.band_structure.get_distances()
        frequencies = phonon.band_structure.get_frequencies()
        connections = phonon.band_structure.path_connections
        if i == 0:
            base_distances = deepcopy(distances)
            bp = BandPlot(ax,
                          band_labels,
                          distances,
                          frequencies,
                          connections)
            bp.plot_band(color=DEFAULT_COLORS[i])
            xscale = bp.xscale
        else:
            distances = _revise_distances(distances, base_distances)
            bp = BandPlot(ax,
                          band_labels,
                          distances,
                          frequencies,
                          connections,
                          xscale=xscale)
            bp.plot_band(color=DEFAULT_COLORS[i%len(DEFAULT_COLORS)])

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
plot
----
provide various kinds of plot
"""

import numpy as np
from matplotlib import pyplot as plt

DEFAULT_COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
plot
----
provide various kinds of plot
"""

from matplotlib import pyplot as plt

def line_chart(ax, xdata, ydata, xlabel, ylabel):
    """
    plot line chart in ax

        Parameters
        ----------
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

        Returns
        -------
        ax : matplotlib.axes._subplots.AxesSubplot
            plotted ax

        Notes
        -----
    """
    ax.plot(xdata, ydata, linestyle='--', linewidth='0.5', c='red')
    ax.scatter(xdata, ydata, facecolor='white', marker='o', edgecolor='red')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

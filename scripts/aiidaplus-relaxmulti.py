#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script shows multi relax results
"""

import os
import yaml
import numpy as np
import argparse
from pprint import pprint
from matplotlib import pyplot as plt
from aiidaplus.plot import line_chart_group, line_chart_group_trajectory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import load_node

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--relax_dir', type=str,
        help="relax directory in which many yaml files exist")
    parser.add_argument('--xdata', type=str, default='kdensity',
        help="xdata, default: kdensity")
    parser.add_argument('--ydata', type=str, default='energies',
        help="ydata, default: energies, you can choose from 'a_norms', 'b_norms', c_norms', energies', 'vols_per_atom'")
    parser.add_argument('--gdata', type=str, default='encuts',
        help="gdata, default: encuts")
    parser.add_argument('--tdata', type=str, default=None,
        help="tdata, default: None, you can choose sigmas for example")
    parser.add_argument('--title', type=str, default='relax multi plot',
        help="fig title default: relax multi plot")
    parser.add_argument('--figname', type=str, default=None,
        help="if set 'auto, figname becomes the same as title'")
    parser.add_argument('--show', action='store_true',
        help="show plot")
    args = parser.parse_args()
    return args

def import_yamls(relax_dir):
    yamlfiles = [ name for name in os.listdir(relax_dir) if 'yaml' in name ]
    yamlfiles.sort()
    relaxes = []
    for yamlfile in yamlfiles:
        with open(os.path.join(relax_dir, yamlfile)) as f:
            relaxes.append(yaml.load(f, Loader=yaml.SafeLoader))
    return relaxes

def get_data(relaxes):
    kdensity = [ np.average(relax['steps']['step_00']['kpoints']['density']) for relax in relaxes ]
    # kpoints_nums = []
    # for relax in relaxes:
    #     m = relax['steps']['step_00']['kpoints']['mesh']
    #     kpoints_nums.append(m[0]*m[1]*m[2])
    sigmas = [ relax['steps']['step_00']['incar']['sigma'] for relax in relaxes ]
    encuts = [ relax['steps']['step_00']['incar']['encut'] for relax in relaxes ]
    energies = [ relax['final_energy_no_entropy'] for relax in relaxes ]
    structures = [ load_node(relax['final_structure_pk']).get_pymatgen() for relax in relaxes ]
    a_norms = [ structure.lattice.a for structure in structures ]
    b_norms = [ structure.lattice.b for structure in structures ]
    c_norms = [ structure.lattice.c for structure in structures ]
    vols_per_atom = [ structure.volume / len(structure.sites) for structure in structures ]
    datas = {
        'kdensity': kdensity,
        'sigmas': sigmas,
        'encuts': encuts,
        'energies': energies,
        'a_norms': a_norms,
        'b_norms': b_norms,
        'c_norms': c_norms,
        'vols_per_atom': vols_per_atom,
    }
    return datas

def get_plot(datas, xdata, ydata, gdata, tdata, title, figname, show):
    x = np.array(datas[xdata])
    y = np.array(datas[ydata])
    xlabel = xdata
    ylabel = ydata
    g = np.array(datas[gdata])
    glabel = gdata
    title = title

    if tdata is None:
        fig = plt.figure(figsize=(14,14))
        ax = fig.add_axes((0.15, 0.15, 0.6, 0.8))
        line_chart_group(ax=ax,
                         xdata=x,
                         ydata=y,
                         xlabel=xlabel,
                         ylabel=ylabel,
                         gdata=g,
                         glabel=glabel)
    else:
        unique_t = np.unique(datas[tdata])
        fig = plt.figure(figsize=(8*len(unique_t),8))
        x_range = (0.98 - 0.05) / len(unique_t)
        start = 0.05
        for i, t in enumerate(unique_t):
            # ax = fig.add_subplot(1,len(unique_t),i+1)
            ax = fig.add_axes((start, 0.1, x_range-0.05, 0.75))
            idxes = [ idx for idx in range(len(datas[tdata])) if np.isclose(datas[tdata][idx], t) ]
            line_chart_group(ax=ax,
                             xdata=x[idxes],
                             ydata=y[idxes],
                             xlabel=xlabel,
                             ylabel=ylabel,
                             gdata=g[idxes],
                             glabel=glabel)
            ax.set_title('{} = {}'.format(tdata, t))
            ax.set_ylim(min(y), max(y))
            start += x_range
    fig.suptitle(title, fontsize=18)
    # if ydata == 'vols_per_atom':
    #     ax.set_ylim(min(y)-0.01, min(y)+0.03)
    if show:
        plt.show()
    if figname is not None:
        if figname == 'auto':
            fname = title
        else:
            fname = figname
        plt.savefig(fname)

# def get_plot(datas, xdata, ydata, gdata, tdata, title, figname, show):
#     x = datas[xdata]
#     y = datas[ydata]
#     xlabel = xdata
#     ylabel = ydata
#     g = datas[gdata]
#     glabel = gdata
#     title = title
# 
#     fig = plt.figure(figsize=(14,14))
#     ax = fig.add_axes((0.15, 0.15, 0.6, 0.8))
#     if tdata is None:
#         line_chart_group(ax=ax,
#                          xdata=x,
#                          ydata=y,
#                          xlabel=xlabel,
#                          ylabel=ylabel,
#                          gdata=g,
#                          glabel=glabel)
#     else:
#         t = datas[tdata]
#         line_chart_group_trajectory(ax=ax,
#                          xdata=x,
#                          ydata=y,
#                          xlabel=xlabel,
#                          ylabel=ylabel,
#                          gdata=g,
#                          glabel=glabel,
#                          tdata=t)
#     fig.suptitle(title, fontsize=18)
#     if ydata == 'vols_per_atom':
#         ax.set_ylim(min(y)-0.01, min(y)+0.03)
#     if show:
#         plt.show()
#     if figname is not None:
#         if figname == 'auto':
#             fname = title
#         else:
#             fname = figname
#         plt.savefig(fname)

@with_dbenv()
def main(relax_dir,
         xdata,
         ydata,
         gdata,
         tdata,
         title,
         figname,
         show):
    relaxes = import_yamls(relax_dir)
    datas = get_data(relaxes)
    get_plot(datas, xdata, ydata, gdata, tdata, title, figname, show)

if __name__ == '__main__':
    args = get_argparse()
    main(relax_dir=args.relax_dir,
         xdata=args.xdata,
         ydata=args.ydata,
         gdata=args.gdata,
         tdata=args.tdata,
         title=args.title,
         figname=args.figname,
         show=args.show,
         )

#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# plot vasp results
###############################################################################

### import modules
import os
import argparse
import yaml
import numpy as np
from matplotlib import pyplot as plt
# from pymatgen.io import lobster as pmglobster
from pymatgen.io.lobster import outputs as pmglobster
from pymatgen.io import vasp as pmgvasp
from pymatgen.electronic_structure import plotter as pmgplotter

def print_runmode():
    print("---------------")
    print("argparse inputs")
    print("---------------")
    print("run mode : 'ele_band'                  filenames : 'vasprun.xml'                       keys : None")
    print("run mode : 'ele_dos'                   filenames : 'vasprun.xml'                       keys : None")
    print("run mode : 'ele_element_dos'           filenames : 'vasprun.xml'                       keys : None")
    print("run mode : 'lobster_dos'               filenames : 'vasprun.xml' 'DOSCAR.lobster'      keys : None")
    print("run mode : 'lobster_element_dos'       filenames : 'vasprun.xml' 'DOSCAR.lobster'      keys : None")
    print("run mode : 'lobster_element_spd_dos'   filenames : 'vasprun.xml' 'DOSCAR.lobster'      keys : element")
    print("run mode : 'lobster_spd_dos'           filenames : 'vasprun.xml' 'DOSCAR.lobster'      keys : None")
    print("run mode : 'static'         filenames : 'static1 static2'                              keys : 'xkey ykey sortkey'")
    print("                                                           (they are directories)")
### Arg-parser
parser = argparse.ArgumentParser(
    description="This script plots various figures")
parser.add_argument('-r', '--runmode', type=str, help=print_runmode())
parser.add_argument('-f', '--filenames', type=str,
                    help="input filenames")
parser.add_argument('-k', '--keys', type=str, default=None,
                    help="additional parse keys")
parser.add_argument('--xlim', type=str, default='None None',
                    help="figure xlimit, don't use colon \
                          ex) '-10 20', 'None 20'")
parser.add_argument('--ylim', type=str, default='None None',
                    help="figure ylimit, don't use colon \
                          ex) '-10 20', 'None 20'")
parser.add_argument('--xlabel', type=str, default=None,
                    help="xlabel")
parser.add_argument('--ylabel', type=str, default=None,
                    help="ylabel")
parser.add_argument('--savefig', type=str, default=None,
                    help="if this option persed, this does not show figure, just save")
parser.add_argument('--title', type=str, default=None,
                    help="title")
parser.add_argument('--figsize', type=str, default=None,
                    help="ex) '8 12'")
args = parser.parse_args()

### analysis parser
def _reshape_parser(parser, objtype=str):
    """
    from 'None 3.5' to (None, 3.5)
    """
    split = parser.split()
    for i in range(len(split)):
        if split[i] == 'None':
            split[i] = None
        else:
            split[i] = objtype(split[i])
    return tuple(split)

def _load_yaml(yamlfile):
    """
    load yaml type file

        Parameters
        ----------
        yamlfile : str
            ex. vasper-log.yaml file
    """
    with open(yamlfile, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
    return data

def _set_fig_property():
    # plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.size'] = 13
    plt.rcParams['axes.linewidth'] = 1.5
    # plt.rcParams['xtics.major.size'] = 10
    # plt.rcParams['xtics.major.width'] = 1.5


# def _get_final_vasperlog(dirname):
#     """
#     get final vasper-log.yaml file in dirname (relax directory)
#     """
#     optdirs = [ opt for opt in os.listdir(dirname) if 'opt' in opt]
#     optdirs.sort()
#     vasperlog_file = os.path.join(dirname, optdirs[-1], 'vasper-log.yaml')
#     vasperlog = _load_yaml(vasperlog_file)
#     return vasperlog

def get_data_from_vasperlogs(vasperlogs, xkey, ykey, sortkey):
    """
    get data from multiple vasper-log.yaml files
    each input 'key' must be included in vasper-log_data['all_summary']

        Parameters
        ----------
        vasperlogs : list of str
            vasperlogs = [ 'vasper-log.yaml_1',
                           'vasper-log.yaml_2',
                                 ...           ]
        xkey : str
            xkey
        ykey : str
            xkey
        sortkey : str
            sortkey

        Returns
        -------
        data : dict of np.array
            data = {'sortvar1' : np.array([xdata, ydata]),
                    'sortvar2' : np.array([xdata, ydata]),
                                 ...                      }
    """
    def _get_sortvar_sets(vasperlogs):
        sortvars = []
        for vasperlog in vasperlogs:
            sortvars.append(vasperlog['all_summary'][sortkey])
        if type(sortvars[0]) == list:
            sortvar_sets = []
            for ele in sortvars:
                if ele not in sortvar_sets:
                    sortvar_sets.append(ele)
        else:
            sortvar_sets = list(set(sorvars))
        sortvar_sets.sort()
        return sortvar_sets

    def _sort_xydata(data_arr):
        sort_ix = np.argsort(data_arr[0])
        sorted_data_arr = data_arr[:,sort_ix]
        return sorted_data_arr

    sortvar_sets = _get_sortvar_sets(vasperlogs)
    data = {}
    for sortvar in sortvar_sets:
        xdata = []
        ydata = []
        for vasperlog in vasperlogs:
            if vasperlog['all_summary'][sortkey] == sortvar:
                xdata.append(vasperlog['all_summary'][xkey])
                ydata.append(vasperlog['all_summary'][ykey])
        data_arr = _sort_xydata(np.array([xdata, ydata]))
        data[str(sortvar)] = data_arr
    return data

### read data from file
def read_data(runmode, filenames, keys=None):
    """
    read necessary data from file
    """
    if runmode == 'ele_dos':
        vasprun = pmgvasp.outputs.Vasprun(filenames)
        tdos = vasprun.tdos
        return tdos
    elif runmode == 'ele_element_dos':
        vasprun = pmgvasp.outputs.Vasprun(filenames)
        cdos = vasprun.complete_dos
        element_dos = cdos.get_element_dos()
        return element_dos
    elif runmode == 'ele_band':
        vasprun = pmgvasp.outputs.BSVasprun(filenames)
        band = vasprun.get_band_structure(line_mode=True)
        return band
    elif runmode == 'lobster_dos':
        filenames = _reshape_parser(filenames)
        # doscar = pmglobster.Doscar(vasprun=filenames[0], doscar=filenames[1])
        doscar = pmglobster.Doscar()
        # doscar = pmglobster.outputs.Doscar(vasprun=filenames[0], doscar=filenames[1])
        tdos = doscar.tdos
        return tdos
    elif runmode == 'lobster_element_dos':
        filenames = _reshape_parser(filenames)
        # doscar = pmglobster.Doscar(vasprun=filenames[0], doscar=filenames[1])
        doscar = pmglobster.Doscar(doscar=filenames[1])
        cdos = doscar.completedos
        element_dos = cdos.get_element_dos()
        return element_dos
    elif runmode == 'lobster_element_spd_dos':
        filenames = _reshape_parser(filenames)
        # doscar = pmglobster.Doscar(vasprun=filenames[0], doscar=filenames[1])
        doscar = pmglobster.Doscar(doscar=filenames[1])
        cdos = doscar.completedos
        element_dos = cdos.get_element_spd_dos(el=keys)
        return element_dos
    elif runmode == 'lobster_spd_dos':
        filenames = _reshape_parser(filenames)
        doscar = pmglobster.Doscar(vasprun=filenames[0], doscar=filenames[1])
        cdos = doscar.completedos
        element_dos = cdos.get_spd_dos()
        return element_dos
    elif runmode == 'static':
        filenames = _reshape_parser(filenames)
        vasperfiles = []
        for dirname in filenames:
            # vasperfiles.append(_get_final_vasperlog(dirname))
            vasperfiles.append(_load_yaml(os.path.join(dirname, 'vasper-log.yaml')))
        keys = _reshape_parser(keys)
        data = get_data_from_vasperlogs(vasperfiles, keys[0], keys[1], keys[2])
        return data
    else:
        raise ValueError("runmode : %s is not supported" % runmode)

def make_plot(runmode, data, xlim, ylim):
    """
    plot
    """
    if runmode == 'ele_dos' or runmode == 'lobster_dos':
        plotter = pmgplotter.DosPlotter()
        plotter.add_dos("Total DOS", data)
        plotter.show(xlim=xlim, ylim=ylim)
    elif runmode == 'ele_element_dos' or \
         runmode == 'lobster_element_dos' or \
         runmode == 'lobster_element_spd_dos' or \
         runmode == 'lobster_spd_dos':
        plotter = pmgplotter.DosPlotter()
        plotter.add_dos_dict(data)
        plotter.show(xlim=xlim, ylim=ylim)
    elif runmode == 'ele_band':
        #plotter = pmgplotter.BSPlotter(bandstr)
        plotter = pmgplotter.BSPlotter(data)
        plotter.get_plot(ylim=ylim).show()
    elif runmode == 'static':
        if args.figsize is not None:
            figsize = _reshape_parser(args.figsize)
        fig = plt.figure(figsize=(int(figsize[0]), int(figsize[1])))
        ax = fig.add_subplot(111)
        keys = list(data.keys())
        keys.sort()
        for key in keys:
            data_arr = data[key]
            ax.scatter(data_arr[0,:], data_arr[1,:], s=30)
            ax.plot(data_arr[0,:], data_arr[1,:], label=key, linestyle='dashed')
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel(args.xlabel)
        ax.set_ylabel(args.ylabel)
        ax.legend()
        plt.title(args.title)
        plt.tight_layout()
        if args.savefig is None:
            plt.show()
        else:
            plt.savefig(args.savefig)
    else:
        raise ValueError("runmode : %s is not supported" % args.runmode)

_set_fig_property()
xlim = _reshape_parser(args.xlim, objtype=float)
ylim = _reshape_parser(args.ylim, objtype=float)
data = read_data(args.runmode, args.filenames, args.keys)
make_plot(args.runmode, data, xlim, ylim)

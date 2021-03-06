#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you export various data from aiida database.
"""

import argparse
import yaml
import warnings
import numpy as np
from pprint import pprint
from matplotlib import pyplot as plt
from aiida.orm import load_node, QueryBuilder, Node
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.plugins import WorkflowFactory
from pymatgen.io import vasp as pmgvasp
from aiidaplus.get_data import (get_structure_data,
                                get_relax_data,
                                get_phonon_data,
                                get_shear_data,
                                get_twinboundary_relax_data,
                                )
from aiidaplus import plot as aiidaplot
from twinpy.common.kpoints import get_mesh_offset_from_direct_lattice
from twinpy.interfaces.aiida.vasp import (AiidaVaspWorkChain,
                                          AiidaRelaxWorkChain)
from twinpy.interfaces.aiida.phonopy import AiidaPhonopyWorkChain
from twinpy.interfaces.aiida.twinboundary \
        import AiidaTwinBoudnaryRelaxWorkChain

RELAX_WF = WorkflowFactory('vasp.relax')

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-pk', '--node_pk', type=int, default=None,
        help="node pk, currently supported StructureData")
    parser.add_argument('--get_data', action='store_true',
        help="get data")
    parser.add_argument('--show', action='store_true',
        help="show the detailed information of data")
    parser.add_argument('--additional_relax_pks', type=str, default='',
        help="additional relax pks")
    parser.add_argument('--ev_range', type=float, default=4.,
        help="eV range when sheft energy plot is activated")
    parser.add_argument('--ymax', type=float, default=None,
        help="fig ymax")
    args = parser.parse_args()
    return args

def dic2yaml(dic, filename):
    with open(filename, 'w') as f:
        yaml.dump(dic, f, indent=4, default_flow_style=False, explicit_start=True)

# functions
def _export_shear(pk, get_data, show):

    # def __get_results():
    #     parent = node.outputs.parent.get_pymatgen()
    #     dic = {}
    #     dic['atoms_num'] = len(parent.species)
    #     dic['energies'] = np.array(node.outputs.relax_results.get_dict()['energies'])
    #     dic['strain'] = node.outputs.strain.value \
    #             * np.array(node.outputs.shear_ratios['shear_ratios'])

    #     # get relaxed structure pk
    #     qb = QueryBuilder()
    #     qb.append(Node, filters={'id':{'==': pk}}, tag='wf')
    #     qb.append(RELAX_WF, with_incoming='wf', project=['label', 'id'])
    #     relaxes = qb.all()
    #     relaxes.sort(key=lambda x: x[0])
    #     dic['relax'] = {}
    #     for i in range(len(relaxes)):
    #         n = load_node(relaxes[i][1])
    #         dic['relax'][relaxes[i][0]] ={
    #                 'relax_pk': relaxes[i][1],
    #                 'init_structure_pk': n.inputs.structure.pk,
    #                 'final_structure_pk': n.outputs.relax__structure.pk,
    #                 }

    #     return dic

    def _show(dic):
        fig = plt.figure()
        # ax1 = fig.add_axes((0.15, 0.1, 0.35,  0.35))
        # ax2 = fig.add_axes((0.63, 0.1, 0.35, 0.35))
        # ax3 = fig.add_axes((0.15, 0.55, 0.35, 0.35))
        # ax4 = fig.add_axes((0.63, 0.55, 0.35, 0.35))
        ax1 = fig.add_subplot(111)
        aiidaplot.line_chart(
                ax1,
                dic['gamma'] * np.array(dic['shear_ratios']),
                (np.array(dic['relax_results']['energies']) \
                    - dic['relax_results']['energies'][0]) \
                      * 1000 / dic['parent']['natoms'],
                "strain (angstrom)",
                "energy (meV / atom)"
                )
        fig.suptitle('shear result pk: %s' % pk)
        plt.show()

    results = get_shear_data(pk)
    basename = 'pk'+str(pk)+'_shear'
    if get_data:
        # for key in results:
        #     if type(results[key]) == np.ndarray:
        #         results[key] = results[key].tolist()
        yamlname = basename+'.yaml'
        with open(yamlname, 'w') as f:
            yaml.dump(results, f, indent=4, default_flow_style=False)
    if show:
        _show(results)

def _export_structure(pk, get_data, show):
    data = get_structure_data(pk)
    if show:
        for key in data:
            print(key+':')
            pprint(data[key])
    if get_data:
        filename = 'pk'+str(pk)+'_structure.yaml'
        dic2yaml(data, filename)


# def _export_twinboundary_relax(pk, get_data, show, ymax):
#     """
#     Notes:
#         'max_force' means the max force acting on atoms in the final static
#         force calculation.
#     """
#     data = get_twinboundary_relax_data(pk)
#     if show:
#         max_forces = [ get_relax_data(relax_pk)['max_force']
#                            for relax_pk in data['relax_pks'] ]
#         steps = [ i+1 for i in range(len(max_forces)) ]
# 
#         fig = plt.figure()
#         ax = fig.add_subplot(111)
#         aiidaplot.line_chart(ax,
#                              xdata=steps,
#                              ydata=max_forces,
#                              xlabel='steps',
#                              ylabel='max force on atom')
#         ax.set_ylim(0., ymax)
#         plt.title("twinboudnary relax: max force acting on atom")
#         plt.show()
# 
#     if get_data:
#         filename = 'pk'+str(pk)+'_twinboundary_relax.yaml'
#         dic2yaml(data, filename)


def _export_twinboundary_relax(pk, show, additional_relax_pks=None):
    tb_relax = AiidaTwinBoudnaryRelaxWorkChain(load_node(pk))
    tb_relax.get_description()
    if show:
        aiida_relax = tb_relax.get_aiida_relax(
                additional_relax_pks=additional_relax_pks)
        tb_analyzer = tb_relax.get_twinboundary_analyzer(
                additional_relax_pks=additional_relax_pks)
        aiida_relax.plot_convergence()
        tb_analyzer.plot_plane_diff()
        tb_analyzer.plot_angle_diff()
        plt.show()


def _export_twinboundary(pk, get_data, show, ev_range=4.):
    data = get_twinboundary_data(pk)
    conf = load_node(pk).inputs.twinboundary_conf
    lattice = load_node(data['structure_pks'][0][0]).get_pymatgen_structure().lattice
    a = lattice.a
    b = lattice.b
    if show:
        fig = plt.figure(figsize=(12.5,10))
        ax = fig.add_subplot(111)
        aiidaplot.shift_energy_plot(
                ax,
                np.array(data['twinboudnary_summary']['shifts']),
                np.array(data['vasp_results']['energies']),
                data['twinboudnary_summary']['natoms'],
                a,
                b,
                ev_range=ev_range,
                )
        dim = ''.join(list(map(str, conf['dim'])))
        title = 'pk{}_{}_{}_d{}'.format(
            pk,
            conf['twinmode'],
            conf['twintype'],
            dim)
        ax.set_title(title)
        plt.savefig('pk{}_twinboundary.png'.format(
            pk))
        plt.show()

    if get_data:
        filename = 'pk'+str(pk)+'_twinboundary.yaml'
        dic2yaml(data, filename)

def _export_twinboundary_shear(pk, get_data, show):
    # not edited yet
    data = get_twinboundary_data(pk)
    conf = load_node(pk).inputs.twinboundary_conf
    lattice = load_node(data['structure_pks'][0][0]).get_pymatgen_structure().lattice
    a = lattice.a
    b = lattice.b
    if show:
        fig = plt.figure(figsize=(12.5,10))
        ax = fig.add_subplot(111)
        aiidaplot.shift_energy_plot(
                ax,
                np.array(data['twinboudnary_summary']['shifts']),
                np.array(data['vasp_results']['energies']),
                data['twinboudnary_summary']['natoms'],
                a,
                b,
                )
        dim = ''.join(list(map(str, conf['dim'])))
        title = 'pk{}_{}_{}_d{}'.format(
            pk,
            conf['twinmode'],
            conf['twintype'],
            dim)
        ax.set_title(title)
        plt.savefig('pk{}_twinboundary.png'.format(
            pk))
        plt.show()

    if get_data:
        filename = 'pk'+str(pk)+'_twinboundary.yaml'
        dic2yaml(data, filename)


def _export_phonon(pk, get_data, show):
    aiph = AiidaPhonopyWorkChain(load_node(pk))
    aiph.get_description()

    if show:
        phonon = aiph.get_phonon()
        mesh = aiph.phonon_settings['mesh']
        print("run total dos with mesh: {}".format(mesh))
        phonon.run_mesh(mesh)
        phonon.run_total_dos()
        phonon.auto_band_structure(plot=False,
                                   write_yaml=False,
                                   filename=None,
                                   npoints=51)
        phonon.plot_band_structure_and_dos().show()
    if get_data:
        analyzer = aiph.get_phonon_analyzer()
        filename = 'pk' + str(pk) + '_phonopy_params.yaml'
        analyzer.export_phonon(filename=filename)


def _export_kpoints(pk):
    kpt = load_node(pk)
    print("# kpoints")
    pprint(kpt.get_kpoints_mesh())

def _export_vasp(pk):
    aiida_vasp = AiidaVaspWorkChain(load_node(pk))
    aiida_vasp.get_description()


def _export_relax(pk, show):
    aiida_relax = AiidaRelaxWorkChain(load_node(pk))
    aiida_relax.get_description()
    if show:
        aiida_relax.plot_convergence()
        plt.show()

@with_dbenv()
def main(pk, get_data=False, show=False, ev_range=4., ymax=None,
         additional_relax_pks=[],):
    """
    export specified pk data

        Parameters
        ----------
        pk: int
            data node pk
        get_data: bool, default False
            if True, export data
        show: bool, default False
            if True, show detailed information

        Notes
        -----
        object type of specified pk is
          -- StructureData => go to def '_export_structure'
               export structure with POSCAR filetype

        Raises
        ------
        ValueError
            object type of specified pk is not supported
    """
    node = load_node(pk)
    if node.node_type == 'data.structure.StructureData.':
        _export_structure(pk, get_data, show)
    elif node.node_type == 'data.array.kpoints.KpointsData.':
        _export_kpoints(pk)
    elif node.node_type == 'process.workflow.workchain.WorkChainNode.':
        workchain_name = node.process_class.get_name()
        if workchain_name == 'VaspWorkChain':
            _export_vasp(pk)
        elif workchain_name == 'RelaxWorkChain':
            _export_relax(pk, show)
        elif workchain_name == 'PhonopyWorkChain':
            _export_phonon(pk, get_data, show)
        elif workchain_name == 'ShearWorkChain':
            _export_shear(pk, get_data, show)
        # elif workchain_name == 'TwinBoundaryWorkChain':
        #     _export_twinboundary(pk, get_data, show, ev_range)
        elif workchain_name == 'TwinBoundaryRelaxWorkChain':
            _export_twinboundary_relax(pk, show, additional_relax_pks)
        elif workchain_name == 'TwinBoundaryShearWorkChain':
            _export_twinboundary_shear(pk, get_data, show)
        else:
            raise ValueError("workchain %s is not supported" % workchain_name)
    else:
        raise ValueError("object type %s is not supported" % node.node_type)


if __name__ == '__main__':
    args = get_argparse()
    additional_relax_pks = list(map(int, args.additional_relax_pks.split()))
    main(args.node_pk, args.get_data, args.show, args.ev_range, args.ymax,
         additional_relax_pks)

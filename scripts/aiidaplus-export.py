#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you export various data from aiida database.
"""

import argparse
import yaml
import numpy as np
from matplotlib import pyplot as plt
from aiida.orm import load_node, QueryBuilder, Node
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.plugins import WorkflowFactory
from pymatgen.io import vasp as pmgvasp
from aiidaplus.get_data import (get_structure_data,
                                get_relax_data)
from aiidaplus import plot as aiidaplot
from pprint import pprint

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
    args = parser.parse_args()
    return args

def dic2yaml(dic, filename):
    with open(filename, 'w') as f:
        yaml.dump(dic, f, indent=4, default_flow_style=False, explicit_start=True)

# functions
def _export_shear(pk, node, get_data, show):

    def __get_results():
        parent = node.outputs.parent.get_pymatgen()
        dic = {}
        dic['atoms_num'] = len(parent.species)
        dic['energies'] = np.array(node.outputs.relax_results.get_dict()['energies'])
        dic['strain'] = node.outputs.strain.value \
                * np.array(node.outputs.shear_ratios['shear_ratios'])

        # get relaxed structure pk
        qb = QueryBuilder()
        qb.append(Node, filters={'id':{'==': pk}}, tag='wf')
        qb.append(RELAX_WF, with_incoming='wf', project=['label', 'id'])
        relaxes = qb.all()
        relaxes.sort(key=lambda x: x[0])
        dic['relax'] = {}
        for i in range(len(relaxes)):
            n = load_node(relaxes[i][1])
            dic['relax'][relaxes[i][0]] ={
                    'relax_pk': relaxes[i][1],
                    'init_structure_pk': n.inputs.structure.pk,
                    'final_structure_pk': n.outputs.relax__structure.pk,
                    }

        return dic

    def __get_process_fig(dic):
        fig = plt.figure()
        # ax1 = fig.add_axes((0.15, 0.1, 0.35,  0.35))
        # ax2 = fig.add_axes((0.63, 0.1, 0.35, 0.35))
        # ax3 = fig.add_axes((0.15, 0.55, 0.35, 0.35))
        # ax4 = fig.add_axes((0.63, 0.55, 0.35, 0.35))
        ax1 = fig.add_subplot(111)
        aiidaplot.line_chart(
                ax1,
                dic['strain'],
                (dic['energies'] - dic['energies'][0]) * 1000 / dic['atoms_num'],
                "strain (angstrom)",
                "energy (meV / atom)"
                )
        fig.suptitle('shear result pk: %s' % pk)

    results = __get_results()
    __get_process_fig(results)
    if get_data:
        for key in results:
            if type(results[key]) == np.ndarray:
                results[key] = results[key].tolist()
        with open('shearworkchain_pk'+str(pk)+'.yaml', 'w') as f:
            yaml.dump(results, f, indent=4, default_flow_style=False)
    if show:
        plt.savefig('shearworkchain_pk'+str(pk)+'.png')
        plt.show()

def _export_structure(pk, get_data, show):
    data = get_structure_data(pk)
    if show:
        for key in data:
            print(key+':')
            pprint(data[key])
    if get_data:
        filename = 'pk'+str(pk)+'_structure.yaml'
        dic2yaml(data, filename)

def _export_relax(pk, get_data, show):

    def _get_fig(vasp_results):
        steps = [ 'step_%02d' % i for i in range(len(vasp_results)) ]
        relax_times = [ i for i in range(len(vasp_results)) ]
        volumes = []
        maximum_forces = []
        maximum_stresses = []
        total_energes = []
        for i, step in enumerate(steps):
            results = vasp_results[step]
            volumes.append(results['structure']['final']['volume'])
            maximum_forces.append(results['maximum_force'])
            maximum_stresses.append(results['maximum_stress'])
            total_energes.append(results['energy_no_entropy'])

        fig = plt.figure()
        ax1 = fig.add_axes((0.15, 0.1, 0.35,  0.35))
        ax2 = fig.add_axes((0.63, 0.1, 0.35, 0.35))
        ax3 = fig.add_axes((0.15, 0.55, 0.35, 0.35))
        ax4 = fig.add_axes((0.63, 0.55, 0.35, 0.35))
        aiidaplot.line_chart(
                ax1,
                relax_times,
                volumes,
                'relax times',
                'volume [angstrom]')
        aiidaplot.line_chart(
                ax2,
                relax_times,
                maximum_forces,
                'relax times',
                'maximum force')
        aiidaplot.line_chart(
                ax3,
                relax_times,
                maximum_stresses,
                'relax times',
                'maximum stress')
        aiidaplot.line_chart(
                ax4,
                relax_times,
                total_energes,
                'relax times',
                'total energy')
        fig.suptitle('relux result pk: %s' % pk)

    data = get_relax_data(pk)
    _get_fig(data['steps'])
    if get_data:
        filename = 'pk'+str(pk)+'_relax.yaml'
        dic2yaml(data, filename)
        plt.savefig('pk'+str(pk)+'_relax.png')
    if show:
        plt.show()

@with_dbenv()
def main(pk, get_data=False, show=False):
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
    elif node.node_type == 'process.workflow.workchain.WorkChainNode.':
        workchain_name = node.process_class.get_name()
        if workchain_name == 'RelaxWorkChain':
            _export_relax(pk, get_data, show)
        elif workchain_name == 'ShearWorkChain':
            _export_shear(pk, node, get_data, show)
        else:
            raise ValueError("workchain %s is not supported" % workchain_name)
    else:
        raise ValueError("object type %s is not supported" % node.node_type)


if __name__ == '__main__':
    args = get_argparse()
    main(args.node_pk, args.get_data, args.show)

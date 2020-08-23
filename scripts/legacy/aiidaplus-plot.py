#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
import numpy as np
from matplotlib import pyplot as plt
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import load_node
from aiidaplus import plot as aiidaplot

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--filename', type=str, default=None,
        help="input file name or structure pk")
    parser.add_argument('-t', '--filetype', type=str, default=None,
        help="input file type, currently supported 'pk' and 'vasprun'")
    parser.add_argument('-o', '--figname', type=str, default=None,
        help="if figname is not None, save fig with this name")
    args = parser.parse_args()
    return args

def plot_relax(pk, node):

    def __get_result():
        dic = {
          'relax_structure_pk': node.outputs.relax__structure.pk,
          'maximum_force': node.outputs.misc['maximum_force'],
          'maximum_stress': node.outputs.misc['maximum_stress'],
          'total_energies': node.outputs.misc['total_energies']['energy_no_entropy']
          }
        return dic

    def __get_process_log():
        pks = [ each_node.pk for each_node in node.called[1:] ]  # to get rid of final step '[1:]'
        volume = [ each_node.called[0].called[0].outputs.structure.
                get_pymatgen_structure().volume for each_node in node.called[1:] ]
        space_group = [ list(each_node.called[0].called[0].outputs.structure.
                get_pymatgen_structure().get_space_group_info()) for each_node in node.called[1:] ]
        structure_pk = [ each_node.called[0].called[0].outputs.structure.pk
                for each_node in node.called[1:] ]
        maximum_force = [ each_node.outputs.misc.get_dict()['maximum_force']
                for each_node in node.called[1:] ]
        maximum_stress = [ each_node.outputs.misc.get_dict()['maximum_stress']
                for each_node in node.called[1:] ]
        total_energy = [ each_node.outputs.misc.
                get_dict()['total_energies']['energy_no_entropy']
                for each_node in node.called[1:] ]
        for lst in [pks, volume, space_group, structure_pk, maximum_force, maximum_stress, total_energy]:
            lst.reverse()
        relax_times = [ i+1 for i in range(len(pks)) ]
        dic = {
                'pks': pks,
                'volume': volume,
                'space_group': space_group,
                'structure_pk': structure_pk,
                'maximum_force': maximum_force,
                'maximum_stress': maximum_stress,
                'total_energy': total_energy,
                'relax_times': relax_times
              }
        return dic

    def __get_process_fig(dic):
        fig = plt.figure()
        ax1 = fig.add_axes((0.15, 0.1, 0.35,  0.35))
        ax2 = fig.add_axes((0.63, 0.1, 0.35, 0.35))
        ax3 = fig.add_axes((0.15, 0.55, 0.35, 0.35))
        ax4 = fig.add_axes((0.63, 0.55, 0.35, 0.35))
        aiidaplot.line_chart(
                ax1,
                dic['relax_times'],
                dic['volume'],
                'relax times',
                'volume [angstrom]')
        aiidaplot.line_chart(
                ax2,
                dic['relax_times'],
                dic['maximum_force'],
                'relax times',
                'maximum force')
        aiidaplot.line_chart(
                ax3,
                dic['relax_times'],
                dic['maximum_stress'],
                'relax times',
                'maximum stress')
        aiidaplot.line_chart(
                ax4,
                dic['relax_times'],
                dic['total_energy'],
                'relax times',
                'total energy')
        fig.suptitle('relux result pk: %s' % pk)
        return fig

    processes = __get_process_log()
    results = __get_result()
    results['volume'] = processes['volume'][-1]
    results['space_group'] = processes['space_group'][-1]
    processes['final_state'] = results
    processes['relax_pk'] = pk
    fig = __get_process_fig(processes)
    return fig

def plot_vasprun(vasprun):
    from pymatgen.io.vasp.outputs import Vasprun

    def __get_data(vasprun):
        data = Vasprun(vasprun)
        output = data.as_dict()['output']
        dic = {}
        dic['steps'] = [ i for i in range(len(output['ionic_steps'])) ]
        dic['ave_forces'] = []
        dic['stresses'] = []
        dic['volume'] = []
        dic['energy'] = []
        for ionic_step in output['ionic_steps']:
            dic['ave_forces'].append(np.linalg.norm(ionic_step['forces'], axis=1))
            s = np.array(ionic_step['stress'])
            # xx, yy, zz, yz, zx, xy
            dic['stresses'].append(
                    [ s[0,0], s[1,1], s[2,2], s[1,2], s[2,0], s[0,1] ])
            dic['volume'].append(ionic_step['structure']['lattice']['volume'])
            dic['energy'].append(ionic_step['e_wo_entrp'])
        return dic

    def __get_fig(dic):
        fig = plt.figure()
        ax1 = fig.add_axes((0.15, 0.1, 0.35,  0.35))
        ax2 = fig.add_axes((0.63, 0.1, 0.35, 0.35))
        ax3 = fig.add_axes((0.15, 0.55, 0.35, 0.35))
        ax4 = fig.add_axes((0.63, 0.55, 0.35, 0.35))
        aiidaplot.line_chart(
                ax1,
                dic['steps'],
                dic['volume'],
                'relax times',
                'volume [angstrom]')
        aiidaplot.line_chart(
                ax2,
                dic['steps'],
                dic['energy'],
                'relax times',
                'energy [eV]')
        atom_forces = list(np.array(data['ave_forces']).T)
        for atom_force in atom_forces:
            aiidaplot.line_chart(
                    ax3,
                    dic['steps'],
                    atom_force,
                    'relax times',
                    'averaged force')
        tensors = ['xx', 'yy', 'zz', 'yz', 'zx', 'xy']
        stresses = list(np.array(dic['stresses']).T)
        for tensor, stress in zip(tensors, stresses):
            aiidaplot.line_chart(
                    ax4,
                    dic['steps'],
                    stress,
                    'relax times',
                    'stress',
                    label=tensor)
        return fig

    data = __get_data(vasprun)
    fig = __get_fig(data)
    return fig


@with_dbenv()
def main(filename,
         filetype,
         figname):

    if filetype == 'pk':
        node = load_node(filename)
        if node.node_type == 'process.workflow.workchain.WorkChainNode.':
            workchain_name = node.process_class.get_name()
            if workchain_name == 'RelaxWorkChain':
                fig = plot_relax(filename, node)
            else:
                raise ValueError("workchain %s is not supported" % workchain_name)
        else:
            raise ValueError("object type %s is not supported" % node.node_type)

    elif filetype =='vasprun':
        fig = plot_vasprun(filename)

    if figname is None:
        plt.show()
    else:
        plt.savefig(figname)

if __name__ == '__main__':
    args = get_argparse()
    main(filename=args.filename,
         filetype=args.filetype,
         figname=args.figname)

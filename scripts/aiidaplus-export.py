#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you export various data from aiida database.
"""

import argparse
import yaml
from matplotlib import pyplot as plt
from aiida.orm import load_node
from aiida.cmdline.utils.decorators import with_dbenv
from pymatgen.io import vasp as pmgvasp
from aiidaplus import plot as aiidaplot
from pprint import pprint

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

# functions
def _export_structure(pk, node, get_data, show):
    aiidaplus_structure = __import__("aiidaplus-structure")
    structure = node.get_pymatgen_structure()
    if show:
        aiidaplus_structure.get_description(structure)
    if get_data:
        poscar.write_file('pk'+str(pk)+'.poscar')

def _export_relax(pk, node, get_data, show):

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
        maximum_force = [ each_node.outputs.misc.get_dict()['maximum_force']
                for each_node in node.called[1:] ]
        maximum_stress = [ each_node.outputs.misc.get_dict()['maximum_stress']
                for each_node in node.called[1:] ]
        total_energy = [ each_node.outputs.misc.
                get_dict()['total_energies']['energy_no_entropy']
                for each_node in node.called[1:] ]
        for lst in [pks, volume, maximum_force, maximum_stress, total_energy]:
            lst.reverse()
        relax_times = [ i+1 for i in range(len(pks)) ]
        dic = {
                'pks': pks,
                'volume': volume,
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

    processes = __get_process_log()
    results = __get_result()
    results['volume'] = processes['volume'][-1]
    processes['final_state'] = results
    processes['relax_pk'] = pk
    __get_process_fig(processes)
    print('final state:')
    pprint(results)
    if get_data:
        with open('relaxworkchain_pk'+str(pk)+'.yaml', 'w') as f:
            yaml.dump(processes, f, indent=4, default_flow_style=False)
    if show:
        plt.savefig('relaxworkchain_pk'+str(pk)+'.png')
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
        _export_structure(pk, node, get_data, show)
    elif node.node_type == 'process.workflow.workchain.WorkChainNode.':
        workchain_name = node.process_class.get_name()
        if workchain_name == 'RelaxWorkChain':
            _export_relax(pk, node, get_data, show)
        else:
            raise ValueError("workchain %s is not supported" % workchain_name)
    else:
        raise ValueError("object type %s is not supported" % node.node_type)


if __name__ == '__main__':
    args = get_argparse()
    main(args.node_pk, args.get_data, args.show)

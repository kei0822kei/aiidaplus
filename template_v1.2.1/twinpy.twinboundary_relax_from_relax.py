#!/usr/bin/env python

import yaml
import argparse
import numpy as np
from copy import deepcopy
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
from aiida_twinpy.common.structure import get_cell_from_aiida
from pymatgen.io.phonopy import get_pmg_structure
from twinpy.api_twinpy import get_twinpy_from_cell
from aiidaplus.utils import (get_kpoints,
                             get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut)
from aiidaplus.get_data import get_relax_data

def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer', type=str,
        default='stern', help="input computer (default:stern)'")
    parser.add_argument('--queue', type=str,
        default='', help="queue name, default None")
    parser.add_argument('--group', type=str,
        default=None, help="add nodes to specified group")
    args = parser.parse_args()
    return args

args = get_argparse()

#-----------
# relax data
#-----------
relax_pk = 6548  # aiida
data = get_relax_data(relax_pk)

#----------------
# common settings
#----------------
wf = 'twinpy.twinboundary_relax'
label = "twinpy twinboundary relax calc using relax result (pk: {})".format(relax_pk)
description = label
max_wallclock_seconds = 100 * 3600
clean_workdir = True

#----------------------
# twinpy shear settings
#----------------------
twinboundary_relax_conf = {
        'shear_strain_ratio': 0.,
        'twinmode': '10-12',
        'twintype': 1,
        'dim': [1,1,1],
        'xshift': 0.,
        'yshift': 0.,
        'make_tb_flat': True,
        'structure_type': 'primitive',
        }
relax_times = 3

#----------
# structure
#----------
structure_pk = data['final_structure_pk']

#-------
# potcar
#-------
potential_family = data['steps']['step_00']['potential_family']
potential_mapping = data['steps']['step_00']['potential_mapping']

#-------------------------
# incar and relax settings
#-------------------------
incar_settings = data['steps']['step_00']['incar']
incar_settings['ediff'] = 1e-04
# 
# relax_conf = incar_settings['relax']
# relax_conf['force_cutoff'] = 1e-02
# relax_conf['positions'] = True
# relax_conf['volume'] = False
# relax_conf['shape'] = False
del incar_settings['relax']

relax_conf = {
    'algo': 'rd',  # default 'cg'
    'steps': 15,
    'positions': True,
    'volume': False,
    'shape': False,
    'convergence_absolute': False,
    'convergence_max_iterations': 1,
    # 'convergence_max_iterations': 10,
    'convergence_on': True,
    'convergence_positions': 0.1,
    # 'force_cutoff': 0.0001,
    'force_cutoff': 0.01,
    }


parser_settings = data['steps']['step_00']['parser_settings']

#------------------------
# kpoints for fc2 and nac
#------------------------
kpoints_relax = data['steps']['step_00']['kpoints']

def check_group_existing(group):
    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")

@with_dbenv()
def main(computer,
         queue='',
         group=None):

    # group check
    if group is not None:
        check_group_existing(group)

    # common settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.computer = Str(computer)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description

    # structure
    builder.structure = load_node(structure_pk)

    # twinpy settings
    builder.twinboundary_relax_conf = Dict(dict=twinboundary_relax_conf)

    # vasp settings
    cell = get_cell_from_aiida(builder.structure,
                               get_scaled_positions=True)
    twinpy = get_twinpy_from_cell(cell=cell,
                                  twinmode=twinboundary_relax_conf['twinmode'])
    twinpy.set_twinboundary(twintype=twinboundary_relax_conf['twintype'],
                            xshift=twinboundary_relax_conf['xshift'],
                            yshift=twinboundary_relax_conf['yshift'],
                            dim=twinboundary_relax_conf['dim'],
                            shear_strain_ratio=0.,
                            make_tb_flat=twinboundary_relax_conf['make_tb_flat'])
    ph_tb = twinpy.get_twinboundary_phonopy_structure(
                structure_type=twinboundary_relax_conf['structure_type'])
    pmgstructure = get_pmg_structure(ph_tb)
    kpoints_tb = get_kpoints(structure=pmgstructure,
                             mesh=None,
                             interval=kpoints_relax['intervals'],
                             offset=None)
    base_settings = {
            'vasp_code': 'vasp544mpi',
            'incar_settings': incar_settings,
            'potential_family': potential_family,
            'potential_mapping': potential_mapping,
            }
    relax_settings = deepcopy(base_settings)
    relax_settings.update({
        'kpoints': {'mesh': kpoints_tb['mesh'], 'offset': kpoints_tb['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds},
        'relax_conf': relax_conf,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        })
    builder.calculator_settings = Dict(dict={'relax': relax_settings})
    builder.relax_times = Int(relax_times)

    # submit
    future = submit(builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))

    # add group
    if group is not None:
        grp = Group.get(label=group)
        running_node = load_node(future.pk)
        grp.add_nodes(running_node)
        print("pk {} is added to group: {}".format(future.pk, group))

if __name__ == '__main__':
    main(computer=args.computer,
         queue=args.queue,
         group=args.group)

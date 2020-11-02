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
wf = 'twinpy.shear'
label = "twinpy shear calc using relax result (pk: {})".format(relax_pk)
description = label
dry_run = False
# dry_run = True
is_phonon = True
max_wallclock_seconds_relax = 100 * 3600
max_wallclock_seconds_phonon = 100 * 3600
clean_workdir = True

#----------------------
# twinpy shear settings
#----------------------
shear_conf = {
        'twinmode': '10-12',
        'dim': [1,1,1],
        'xshift': 0.,
        'yshift': 0.,
        # 'grids': 2,
        'grids': 5,
        'structure_type': 'primitive',
        # 'structure_type': 'primitive'  # or 'conventional' or ''
        }

#---------------
# phonon_conf
#---------------

phonon_conf = {
    'distance': 0.03,
    'mesh': [18, 18, 10],
    'supercell_matrix': [2, 2, 2],
    'symmetry_tolerance': 1e-5
    }

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
relax_conf = incar_settings['relax']
del incar_settings['relax']
parser_settings = data['steps']['step_00']['parser_settings']

#------------------------
# kpoints for fc2 and nac
#------------------------
kpoints_relax = data['steps']['step_00']['kpoints']

kpoints_phonon = {
    'mesh': None,
    'interval': kpoints_relax['intervals'],
    'offset': kpoints_relax['offset']
    }


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
    builder.dry_run = Bool(dry_run)
    builder.is_phonon = Bool(is_phonon)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description

    # structure
    builder.structure = load_node(structure_pk)

    # twinpy settings
    builder.shear_conf = Dict(dict=shear_conf)

    # vasp settings
    # hexagonal = get_twinpy_structure_from_structure(builder.structure)
    # hexagonal.set_parent(twinmode=shear_conf['twinmode'])
    # hexagonal.set_is_primitive(shear_conf['is_primitive'])
    # hexagonal.run()
    # pmgparent = hexagonal.get_pymatgen_structure()
    cell = get_cell_from_aiida(builder.structure,
                               get_scaled_positions=True)
    twinpy = get_twinpy_from_cell(cell=cell,
                                  twinmode=shear_conf['twinmode'])
    twinpy.set_shear(xshift=shear_conf['xshift'],
                     yshift=shear_conf['yshift'],
                     dim=shear_conf['dim'],
                     shear_strain_ratio=0.)
    ph_shear = twinpy.get_shear_phonopy_structure(
                   structure_type=shear_conf['structure_type'])
    pmgstructure = get_pmg_structure(ph_shear)
    supercell = deepcopy(pmgstructure)
    supercell.make_supercell(phonon_conf['supercell_matrix'])
    kpoints_ph = get_kpoints(structure=supercell,
                             mesh=kpoints_phonon['mesh'],
                             interval=kpoints_phonon['interval'],
                             offset=kpoints_phonon['offset'])
    base_settings = {
            'vasp_code': 'vasp544mpi',
            'incar_settings': incar_settings,
            'potential_family': potential_family,
            'potential_mapping': potential_mapping,
            }
    relax_settings = deepcopy(base_settings)
    relax_settings.update({
        'kpoints': {'mesh': kpoints_relax['mesh'], 'offset': kpoints_relax['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds_relax},
        'relax_conf': relax_conf,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        })
    phonon_settings = deepcopy(base_settings)
    phonon_settings.update({
        'kpoints': {'mesh': kpoints_ph['mesh'], 'offset': kpoints_ph['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds_phonon},
        'phonon_conf': phonon_conf,
        })
    builder.calculator_settings = Dict(dict={'relax': relax_settings,
                                             'phonon': phonon_settings})

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

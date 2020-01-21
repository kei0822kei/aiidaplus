#!/usr/bin/env python

import yaml
import argparse
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
from aiidaplus.utils import (get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut)

def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer', type=str,
        default='stern', help="input computer (default:stern)'")
    parser.add_argument('--queue', type=str,
        default='', help="queue name, default None")
    parser.add_argument('--group', type=str,
        default=None, help="add nodes to specified group")
    parser.add_argument('--verbose', action='store_true', help="verbose")
    args = parser.parse_args()
    return args

args = get_argparse()

@with_dbenv()
def get_elements(pk):
    node = load_node(pk)
    elements = get_elements_from_aiidastructure(node)
    return elements


#----------------
# common settings
#----------------
wf = 'vasp.relax'
tot_num_mpiprocs = 16
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"

#----------
# structure
#----------
structure_pk = 3932
elements = get_elements(structure_pk)

#-------
# potcar
#-------
potential_family = 'PBE.54'
potential_mapping = get_default_potcar_mapping(elements)
# potential_mapping = {
#         'Na': 'Na',
#         'Cl': 'Cl'
#         }

#------
# incar
#------
### base setting
incar_settings = {
    'addgrid': True,
    'ediff': 1e-6,
    'gga': 'PS',
    'ialgo': 38,
    'lcharg': False,
    'lreal': False,
    'lwave': False,
    'npar': 4,
    'prec': 'Accurate',
    }

### encut
# encut = 300
encut = get_encut(potential_family=potential_family,
                  potential_mapping=potential_mapping,
                  multiply=1.3)

incar_settings['encut'] = encut

### metal or not metal
##### metal
smearing_settings = {
    'ismear': 1,
    'sigma': 0.2
    }
##### not metal
# smearing_settings = {
#     'ismear': 0,
#     'sigma': 0.01
#     }

incar_settings.update(smearing_settings)

#---------------
# relax_settings
#---------------
relax_conf = {
    'perform': True,
    'positions': True,
    'volume': True,
    'shape': True,
    'steps': 20,
    'convergence_absolute': False,
    'convergence_max_iterations': 3,
    'convergence_on': True,
    'convergence_positions': 0.01,
    'convergence_shape_angles': 0.1,
    'convergence_shape_lengths': 0.1,
    'convergence_volume': 0.01,
    'force_cutoff': 0.0001,
    # 'energy_cutoff': 1e-6,
    }
relax_settings = {
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,
    }

#--------
# kpoints
#--------
### not use kdensity
# kpoints = {
#     'mesh': [6, 6, 6],
#     'offset': [0.5, 0.5, 0.5]
#     }
### use kdensity
kpoints = {
    'kdensity': 0.2,
    'offset': [0.5, 0.5, 0.5]
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
         group=None,
         verbose=False):

    # group check
    if group is not None:
        check_group_existing(group)

    # common settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.code = Code.get_from_string('{}@{}'.format('vasp544mpi', computer))
    builder.clean_workdir = Bool(False)
    builder.verbose = Bool(verbose)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description


    # options
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    options.resources = {'tot_num_mpiprocs': tot_num_mpiprocs,
                         'parallel_env': 'mpi*'}
    options.queue_name = queue
    options.max_wallclock_seconds = max_wallclock_seconds
    builder.options = Dict(dict=options)

    # structure
    builder.structure = load_node(structure_pk)

    # incar
    builder.parameters = Dict(dict=incar_settings)

    # relax
    relax_attribute = AttributeDict()
    keys = relax_conf.keys()
    if 'perform' in keys:
        relax_attribute.perform = \
                Bool(relax_conf['perform'])
    if 'positions' in keys:
        relax_attribute.positions = \
                Bool(relax_conf['positions'])
    if 'volume' in keys:
        relax_attribute.volume = \
                Bool(relax_conf['volume'])
    if 'shape' in keys:
        relax_attribute.shape = \
                Bool(relax_conf['shape'])
    if 'steps' in keys:
        relax_attribute.steps = \
                Int(relax_conf['steps'])
    if 'convergence_absolute' in keys:
        relax_attribute.convergence_absolute = \
                Bool(relax_conf['convergence_absolute'])
    if 'convergence_max_iterations' in keys:
        relax_attribute.convergence_max_iterations = \
                Int(relax_conf['convergence_max_iterations'])
    if 'convergence_on' in keys:
        relax_attribute.convergence_on = \
                Bool(relax_conf['convergence_on'])
    if 'convergence_positions' in keys:
        relax_attribute.convergence_positions = \
                Float(relax_conf['convergence_positions'])
    if 'convergence_shape_angles' in keys:
        relax_attribute.convergence_shape_angles = \
                Float(relax_conf['convergence_shape_angles'])
    if 'convergence_shape_lengths' in keys:
        relax_attribute.convergence_shape_lengths = \
                Float(relax_conf['convergence_shape_lengths'])
    if 'convergence_volume' in keys:
        relax_attribute.convergence_volume = \
                Float(relax_conf['convergence_volume'])
    if 'force_cutoff' in keys:
        relax_attribute.force_cutoff = \
                Float(relax_conf['force_cutoff'])
    if 'energy_cutoff' in keys:
        relax_attribute.energy_cutoff = \
                Float(relax_conf['energy_cutoff'])
    builder.relax = relax_attribute
    builder.settings = Dict(dict=relax_settings)

    # kpoints
    kpt = KpointsData()
    if 'kdensity' in kpoints.keys():
        kpt.set_cell_from_structure(builder.structure)
        kpt.set_kpoints_mesh_from_density(
                kpoints['kdensity'], offset=kpoints['offset'])
        if verbose:
            kmesh = kpt.get_kpoints_mesh()
            print("kdensity is: %s" % str(kpoints['kdensity']))
            print("reciprocal lattice (included 2*pi) is:")
            print(kpt.reciprocal_cell)
            print("set kpoints mesh as:")
            print(kmesh[0])
            print("set offset as:")
            print(kmesh[1])
    else:
        kpt.set_kpoints_mesh(kpoints['mesh'], offset=kpoints['offset'])
    builder.kpoints = kpt

    # potcar
    builder.potential_family = Str(potential_family)
    builder.potential_mapping = Dict(dict=potential_mapping)

    # submit
    future = submit(workflow, **builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))

    # add group
    grp = Group.get(label=group)
    running_node = load_node(future.pk)
    grp.add_nodes(running_node)
    print("pk {} is added to group: {}".format(future.pk, group))

if __name__ == '__main__':
    main(computer=args.computer,
         queue=args.queue,
         group=args.group,
         verbose=args.verbose)

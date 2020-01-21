#!/usr/bin/env python

import yaml
import argparse
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import load_node, Bool, Code, Dict, Group, Str, KpointsData
from aiidaplus.utils import (get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut)

def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer', type=str,
        default='stern', help="input computer ex. 'vega'")
    parser.add_argument('--queue', type=str,
        default='', help="queue name, default None")
    parser.add_argument('--group', type=str,
        default=None, help="add nodes to specified group")
    parser.add_argument('--dry_run', type=bool,
        default=False, help="dry run, if True, submit => run")
    parser.add_argument('--verbose', type=bool,
        default=True, help="verbose")
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
wf = 'vasp.vasp'
tot_num_mpiprocs = 16
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"

#----------
# structure
#----------
structure_pk = 4649
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

### if relax
relax_settings = {
    'nsw': 40,
    'ibrion': 2,
    'isif': 3,
    'ediffg': -1e-4
    }
incar_settings.update(relax_settings)

#--------
# kpoints
#--------
### not use kdensity
kpoints = {
    'mesh': [6, 6, 6],
    'offset': [0.5, 0.5, 0.5]
    }
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
         dry_run=False,
         verbose=True):

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

    # run or submit
    if dry_run:
        run(workflow, **builder)
        return
    else:
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
         dry_run=args.dry_run,
         verbose=args.verbose)

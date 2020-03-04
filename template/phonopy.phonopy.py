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
wf = 'phonopy.phonopy'
code = 'phonopy'
tot_num_mpiprocs = 16
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"

#----------
# structure
#----------
structure_pk = 17823
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

#--------
# phonopy
#--------
vasp_code = 'vasp544mpi'
distance = 0.03
is_nac = False
phonopy_mesh = [11,11,11]
supercell_matrix = [2,2,2]
symmetry_tolerance = 1e-5
vasp_max_wallclock_seconds = 3600 * 10
run_phonopy = True


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

    # kpoints
    # def get_kpoints_from_density(kdensity, supercell_matrix):
    #     kpt = KpointsData()
    #     kpt.set_cell_from_structure(builder.structure)
    #     kpt.set_kpoints_mesh_from_density(
    #             kpoints['kdensity'], offset=kpoints['offset'])
    #     if verbose:
    #         kmesh = kpt.get_kpoints_mesh()
    #         print("kdensity is: %s" % str(kpoints['kdensity']))
    #         print("reciprocal lattice (included 2*pi) is:")
    #         print(kpt.reciprocal_cell)
    #         print("set kpoints mesh as:")
    #         print(kmesh[0])
    #         print("set offset as:")
    #         print(kmesh[1])
    #         print("su")
    #         print("supercell_matrix: %s" % str(supercell_matrix))
    #         print("kmesh / supercell_matrix")
    #         kpoints = np.array(kmesh) / np.array(supercell_matrix)
    #         return kpoints

    def get_phonon_settings():
        phonon_settings = {}
        phonon_settings['distance'] = distance
        phonon_settings['is_nac'] = is_nac
        phonon_settings['mesh'] = phonopy_mesh
        phonon_settings['supercell_matrix'] = supercell_matrix
        phonon_settings['symmetry_tolerance'] = symmetry_tolerance
        return phonon_settings

    def get_vasp_settings():
        dic = {}
        base_config = {'code_string': vasp_code+'@'+computer,
                       'kpoints_density': kpoints['kdensity'],
                       'offset': kpoints['offset'], # work ?
                       'potential_family': potential_family,
                       'potential_mapping': potential_mapping,
                       'options': {'resources': {'parallel_env': 'mpi*',
                                                 'tot_num_mpiprocs': tot_num_mpiprocs},
                                   'max_wallclock_seconds': vasp_max_wallclock_seconds}}
        base_parser_settings = {'add_energies': True,
                                'add_forces': True,
                                'add_stress': True}
        forces_config = base_config.copy()
        # forces_config.update({'kpoints_mesh': get_kpoints_from_density(kdensity, supercell_matrix),
        #                       'parser_settings': base_parser_settings,
        #                       'parameters': incar_settings})
        forces_config.update({'parser_settings': base_parser_settings,
                              'parameters': incar_settings})
        dic['forces'] = forces_config
        # if is_nac:
        #     nac_config = base_config.copy()
        #     nac_parser_settings = {'add_born_charges': True,
        #                            'add_dielectrics': True}
        #     nac_parser_settings.update(base_parser_settings)
        #     nac_incar_dict = {'lepsilon': True}
        #     nac_incar_dict.update(params['incar']['incar_base'])
        #     nac_config.update({'kpoints_mesh': params['kpoints']['mesh_nac'],
        #                        'parser_settings': nac_parser_settings,
        #                        'parameters': nac_incar_dict})
        #     dic['nac'] = nac_config
        return dic

    # group check
    if group is not None:
        check_group_existing(group)

    # common settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.code_string = Str('{}@{}'.format(code, computer))
    # builder.clean_workdir = Bool(False)
    # builder.verbose = Bool(verbose)

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

    # phonopy
    builder.phonon_settings = Dict(dict=get_phonon_settings())
    builder.run_phonopy = Bool(run_phonopy)
    builder.remote_phonopy = Bool(True)
    builder.calculator_settings = Dict(dict=get_vasp_settings())

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

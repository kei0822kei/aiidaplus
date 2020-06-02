#!/usr/bin/env python

import yaml
import argparse
from pprint import pprint
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
from aiidaplus.utils import (get_kpoints,
                             get_default_potcar_mapping,
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
    parser.add_argument('--verbose', action='store_true',
        default=None, help="show detail")
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
max_wallclock_seconds = 36000
clean_workdir = True

#----------
# structure
#----------
# structure_pk = 30347  # AgBr
# structure_pk = 4545  # for glass, Ne
structure_pk = 1250 # Ti_c, aiida
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
incar_settings_base = {
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

### encuts
encut_grids = 7
interval = 50
encut = get_encut(potential_family=potential_family,
                  potential_mapping=potential_mapping,
                  multiply=1.3)
init_encut = int(encut)//interval*interval
encuts = [ init_encut+50*i for i in range(encut_grids) ]
encuts.append(encut)
encuts.sort()

### metal
sigmas = [0.1, 0.2, 0.3, 0.4]

##### not metal
# sigmas = [0.01]

#--------
# kpoints
#--------
### choose one of them

### type1
# meshes = [[6,6,6], [8,8,8], [10,10,10]]
# kdensities = None
# offset = None

### type2
meshes = None
kdensities = [0.3, 0.2, 0.1]
offset = None

#---------------
# relax_settings
#---------------
relax_conf = {
    'perform': True,
    'positions': True,
    'volume': True,
    'shape': True,
    'algo': 'rd',  # default: 'cg'
    'steps': 20,
    'convergence_absolute': False,
    'convergence_max_iterations': 2,
    'convergence_on': True,
    'convergence_positions': 0.01,
    'convergence_shape_angles': 0.1,
    'convergence_shape_lengths': 0.1,
    'convergence_volume': 0.01,
    'force_cutoff': 0.001,  # or 'energy_cutoff': 1e-4,
    }

# 'add_structure': True is automatically set
parser_settings = {
    'add_misc': True,
    'add_kpoints': True,
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,

    ### before activate parameters below
    ### always chech whether is works
    ### detail see parser/vasp.py in aiida-vasp

    # 'add_dynmat': True,
    # 'add_hessian': True,
    # 'add_poscar-structure': True,
    # 'add_trajectory': True,
    # 'add_bands': False,
    # 'add_dos': False,
    # 'add_projectors': True,
    # 'add_born_charges': False,
    # 'add_chgcar': False,
    # 'add_wavecar': False,
}

def check_group_existing(group):
    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")

def get_val_sets(structure_pk, encuts, sigmas, meshes=None, kdensities=None):
    val_sets = []
    for encut in encuts:
        for sigma in sigmas:
            if meshes is not None:
                for mesh in meshes:
                    label = 's:{} e:{} s{} m{}'.format(structure_pk, encut, sigma, mesh)
                    description = 'structure:{} encut:{} sigma{} mesh{}' \
                            .format(structure_pk, encut, sigma, mesh)
                    val_sets.append({
                        'label': label,
                        'description': description,
                        'encut': encut,
                        'sigma': sigma,
                        'kdensity': None,
                        'mesh': mesh,
                        })
            else:
                for kdensity in kdensities:
                    label = 'e:{} s{} d{}'.format(encut, sigma, kdensity)
                    description = 'encut:{} sigma{} kdensity{}' \
                            .format(encut, sigma, kdensity)
                    val_sets.append({
                        'label': label,
                        'description': description,
                        'encut': encut,
                        'sigma': sigma,
                        'kdensity': kdensity,
                        'mesh': None,
                        })
    return val_sets

@with_dbenv()
def main(computer,
         queue='',
         group=None,
         verbose=False):

    # group check
    if group is not None:
        check_group_existing(group)

    if meshes is not None and kdensities is not None:
        raise RuntimeError("both meshes and kdensities are set")

    val_sets = get_val_sets(
            structure_pk=structure_pk,
            encuts=encuts,
            sigmas=sigmas,
            meshes=meshes,
            kdensities=kdensities,
            )
    if verbose:
        print("val_sets: total %s" % len(val_sets))
        pprint(val_sets)

    for vals in val_sets:
        # set vals
        incar_settings = incar_settings_base.copy()
        smearing_settings = {
            'ismear': 1,
            'sigma': vals['sigma'],
            }
        incar_settings['encut'] = vals['encut']
        incar_settings.update(smearing_settings)

        kpoints = {
            'mesh': vals['mesh'],
            'kdensity': vals['kdensity'],
            'offset': offset,
            }

        # common settings
        workflow = WorkflowFactory(wf)
        builder = workflow.get_builder()
        builder.code = Code.get_from_string('{}@{}'.format('vasp544mpi', computer))
        builder.clean_workdir = Bool(clean_workdir)
        builder.verbose = Bool(True)

        # label and descriptions
        builder.metadata.label = vals['label']
        builder.metadata.description = vals['description']

        # options
        options = AttributeDict()
        options.account = ''
        options.qos = ''
        options.resources =  {
                'tot_num_mpiprocs': 16,
                'num_machines': 1,
                'parallel_env': 'mpi*'
                }
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
        if 'algo' in keys:
            relax_attribute.algo = \
                    Str(relax_conf['algo'])
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

        # parser settings
        builder.settings = Dict(dict={'parser_settings': parser_settings})

        # kpoints
        kpt = KpointsData()
        kpoints_vasp = get_kpoints(structure=builder.structure.get_pymatgen(),
                                   mesh=kpoints['mesh'],
                                   kdensity=kpoints['kdensity'],
                                   offset=kpoints['offset'],
                                   verbose=verbose)
        kpt.set_kpoints_mesh(kpoints_vasp['mesh'], offset=kpoints_vasp['offset'])
        builder.kpoints = kpt

        # potcar
        builder.potential_family = Str(potential_family)
        builder.potential_mapping = Dict(dict=potential_mapping)

        # submit
        future = submit(workflow, **builder)
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
         group=args.group,
         verbose=args.verbose)

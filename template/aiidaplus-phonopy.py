#!/usr/bin/env python

import sys
import phonopy
from aiida.manage.configuration import load_profile
load_profile()
from aiida.orm import Float, Bool, Str, load_node


def launch_aiida():
    import spglib
    from phonopy.interface.vasp import (read_vasp_from_strings,
                                        get_vasp_structure_lines)
    from phonopy.structure.atoms import PhonopyAtoms
    from aiida.plugins import DataFactory, WorkflowFactory
    from aiida.engine import run, submit
    from aiida_phonopy.common.utils import phonopy_atoms_to_structure
    from aiida.orm import load_node

    Dict = DataFactory('dict')
    unitcell_str = """ Sr Ti O
   1.0
     3.9050000000000000    0.0000000000000000    0.0000000000000000
     0.0000000000000000    3.9050000000000000    0.0000000000000000
     0.0000000000000000    0.0000000000000000    3.9050000000000000
 Sr Ti O
   1   1   3
Direct
   0.0000000000000000  0.0000000000000000  0.0000000000000000
   0.5000000000000000  0.5000000000000000  0.5000000000000000
   0.5000000000000000  0.0000000000000000  0.5000000000000000
   0.5000000000000000  0.5000000000000000  0.0000000000000000
   0.0000000000000000  0.5000000000000000  0.5000000000000000"""

    lat, pos, num = spglib.refine_cell(
        read_vasp_from_strings(unitcell_str).to_tuple())
    cell = read_vasp_from_strings(unitcell_str)
    cell = PhonopyAtoms(cell=lat, scaled_positions=pos, numbers=num)
    cell = read_vasp_from_strings(
        '\n'.join(get_vasp_structure_lines(cell)))
    # structure = phonopy_atoms_to_structure(cell)
    structure_pk = 2537
    structure = load_node(structure_pk)

    base_incar_dict = {
        'PREC': 'Accurate',
        'IBRION': -1,
        # 'EDIFF': 1e-8,
        'EDIFF': 1e-6,
        'NELMIN': 5,
        'NELM': 100,
        'ENCUT': 520,
        'IALGO': 38,
        'ISMEAR': 0,
        'SIGMA': 0.01,
        'GGA': 'PS',
        'LREAL': False,
        'lcharg': False,
        'lwave': False,
    }

    base_config = {'code_string': 'vasp544mpi@vega',
                   'potential_family': 'PBE.54',
                   'potential_mapping': {'O': 'O',
                                         'Ti': 'Ti_pv',
                                         'Sr': 'Sr_sv'},
                   'options': {'resources': {'parallel_env': 'mpi*',
                                             'tot_num_mpiprocs': 16},
                               'max_wallclock_seconds': 3600 * 10}}
    base_parser_settings = {'add_energies': True,
                            'add_forces': True,
                            'add_stress': True}
    forces_config = base_config.copy()
    forces_config.update({'kpoints_mesh': [4, 4, 4],  # k-point density,
                          'parser_settings': base_parser_settings,
                          'parameters': base_incar_dict})
    nac_config = base_config.copy()
    nac_parser_settings = {'add_born_charges': True,
                           # 'structure': structure,    # add by Keiyu
                           'add_dielectrics': True}
    nac_parser_settings.update(base_parser_settings)
    nac_incar_dict = {'lepsilon': True}
    nac_incar_dict.update(base_incar_dict)
    nac_config.update({'kpoints_mesh': [8, 8, 8],  # k-point density,
                       'parser_settings': nac_parser_settings,
                       # 'structure': structure,    # add by Keiyu
                       'parameters': nac_incar_dict})

    PhononPhonopy = WorkflowFactory('phonopy.phonon')
    builder = PhononPhonopy.get_builder()
    builder.structure = structure
    builder.calculator_settings = Dict(dict={'forces': forces_config,
                                             'nac': nac_config})
    builder.run_phonopy = Bool(True)
    builder.remote_phonopy = Bool(True)
    builder.code_string = Str('phonopy@vega')
    builder.phonon_settings = Dict(
        dict={'mesh': 50.0,
              'supercell_matrix': [2, 2, 2],
              'distance': 0.01,
              # 'is_nac': True})
              'is_nac': False})
    builder.symmetry_tolerance = Float(1e-5)
    builder.options = Dict(dict=base_config['options'])
    builder.metadata.label = "SrTiO3 phonon 2x2x2 load nodes"
    builder.metadata.description = "SrTiO3 phonon 2x2x2 load nodes"

    # Chose how to run the calculation
    run_by_deamon = False
    # run_by_deamon = False
    if not run_by_deamon:
        result = run(builder)
        print(result)
    else:
        future = submit(builder)
        print(future)
        print('Running workchain with pk={}'.format(future.pk))


def dump_phonopy(pk):
    n = load_node(pk)
    unitcell = n.inputs.structure.get_ase()
    smat = n.outputs.phonon_setting_info['supercell_matrix']
    ph = phonopy.load(unitcell=unitcell,
                      supercell_matrix=smat,
                      primitive_matrix='auto')
    force_sets = n.outputs.force_sets.get_array('force_sets')
    dataset = n.outputs.phonon_setting_info['displacement_dataset']
    ph.dataset = dataset
    ph.forces = force_sets
    if 'nac_params' in n.outputs:
        borns = n.outputs.nac_params.get_array('born_charges')
        epsilon = n.outputs.nac_params.get_array('epsilon')
        nac_params = {'born': borns,
                      'factor': 14.399652,
                      'dielectric': epsilon}
        ph.nac_params = nac_params

    settings = {'force_sets': True,
                'displacements': True,
                'force_constants': False,
                'born_effective_charge': True,
                'dielectric_constant': True}
    # phonopy-params.yaml is written out.
    ph.save(settings=settings)
    print("phonopy_params.yaml was made for PK=%d" % pk)


if __name__ == '__main__':
    print("the length argv : %s" % str(len(sys.argv)))
    if len(sys.argv) < 2:
        launch_aiida()
    else:
        dump_phonopy(int(sys.argv[1]))

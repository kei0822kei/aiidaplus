#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
get data from aiida pk
"""
import numpy as np
import warnings
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.io.phonopy import get_phonopy_structure
from aiida.orm import load_node
from aiida.common import exceptions
from aiida.cmdline.utils.decorators import with_dbenv
from phonopy import Phonopy
from aiidaplus.utils import get_kpoints

@with_dbenv()
def get_node_from_pk(pk):
    """
    get node from pk
    """
    return load_node(pk)

def check_process_class(node,
                        expected_process_class:str):
    """
    check process class of node is the same as the expected

    Args:
        node: aiida node
        expected_process_class (str): expected process class

    Raises:
        AssertionError: input node is not the same as expected
    """
    assert node.process_class.get_name() == expected_process_class, \
            "input node: {}, expected: {} (NOT MATCH)". \
            format(node.process_class, expected_process_class)

def get_structure_data_from_pymatgen(pmgstructure:Structure,
                                     symprec:float=1e-5) -> dict:
    """
    get structure data from pymatgen structure

    Raises:
        Warning: final structure do not exist

    Note:
        symprec=1e-5 (default), which is the same as VASP SYMPREC default
    """
    analyzer = SpacegroupAnalyzer(pmgstructure, symprec=symprec)
    dataset = analyzer.get_symmetry_dataset()

    dic = {}
    dic['symprec'] = symprec
    dic['volume'] = pmgstructure.lattice.volume
    dic['lattice'] = pmgstructure.lattice.matrix.tolist()
    dic['lattice_abc'] = list(pmgstructure.lattice.abc)
    dic['lattice_angles'] = list(pmgstructure.lattice.angles)
    dic['international'] = dataset['international']
    dic['pointgroup'] = dataset['pointgroup']
    dic['natoms'] = len(pmgstructure.species)
    dic['wyckoffs'] = dataset['wyckoffs']
    dic['site_symmetry_symbols'] = dataset['site_symmetry_symbols']
    dic['hall'] =dataset['hall']
    dic['hall_number'] = dataset['hall_number']

    return dic

def get_structure_data(pk, symprec=1e-5) -> dict:
    """
    get structure data from pk

    Note:
        symprec=1e-5 (default), which is the same as VASP SYMPREC default
    """
    node = get_node_from_pk(pk)
    pmgstructure = node.get_pymatgen()
    dic = get_structure_data_from_pymatgen(pmgstructure)
    dic['pk'] = pk
    dic['data_type'] = 'StructureData'
    return dic

def get_vasp_data(pk, symprec=1e-5) -> dict:
    """
    get vasp data from pk

    Note:
        - symprec=1e-5 (default), which is the same as VASP SYMPREC default
        - Warning: final structure does not exist
    """
    node = get_node_from_pk(pk)
    check_process_class(node, 'VaspWorkChain')
    results = node.outputs.misc.get_dict()

    structure = {}
    initial_structure_pk = node.inputs.structure.pk
    initial_structure = get_structure_data(initial_structure_pk,
                                           symprec=symprec)
    structure['initial'] = initial_structure
    try:
        final_structure_pk = node.outputs.structure.pk
        final_structure = get_structure_data(final_structure_pk,
                                             symprec=symprec)
        structure['final'] = final_structure
    except exceptions.NotExistent:
        warnings.warn("final structure does not exist")

    kpoints = get_kpoints(
            structure=load_node(initial_structure_pk).get_pymatgen_structure(),
            mesh=node.inputs.kpoints.get_kpoints_mesh()[0],
            )
    kpoints['densities'] = kpoints['densities'].tolist()

    dic = {}
    dic['data_type'] = 'VaspWorkChain'
    dic['pk'] = pk
    dic['incar'] = node.inputs.parameters.get_dict()
    dic['potential_family'] = node.inputs.potential_family.value
    dic['potential_mapping'] = node.inputs.potential_mapping.get_dict()
    dic['kpoints'] = kpoints
    dic['structure'] = structure
    dic['maximum_force'] = results['maximum_force']
    dic['maximum_stress'] = results['maximum_stress']
    dic['energy_no_entropy'] = results['total_energies']['energy_no_entropy']

    return dic

def get_relax_data(pk, symprec=1e-5) -> dict:
    """
    get relax data from pk

    Note:
        - symprec=1e-5 (default), which is the same as VASP SYMPREC default
        - Warning: final vasp calculation is not static calc
    """
    node = get_node_from_pk(pk)
    check_process_class(node, 'RelaxWorkChain')

    # drop final static calculation
    vasp_pks = [ vasp_node.called[0].pk for vasp_node in node.called ]
    vasp_pks.reverse()
    if 'nsw' not in \
            get_node_from_pk(vasp_pks[-1]).inputs.parameters.get_dict().keys():
        del vasp_pks[-1]
    else:
        warnings.warn("final vasp calculation is not static calc")
    vasp_results = {}
    for i, vasp_pk in enumerate(vasp_pks):
        vasp_results['step_%02d' % i] = get_vasp_data(vasp_pk,
                                                           symprec=symprec)

    dic = {}
    dic['data_type'] = 'RelaxWorkChain'
    dic['pk'] = pk
    dic['initial_structure_pk'] = node.inputs.structure.pk
    dic['final_structure_pk'] = node.outputs.structure.pk
    dic['final_energy_no_entropy'] = \
        node.outputs.misc.get_dict()['total_energies']['energy_no_entropy']
    dic['steps'] = vasp_results

    return dic

def get_phonon_from_aiida(pk):
    """
    get phonon object from aiida pk
    """
    node = load_node(pk)
    pmgstructure = node.inputs.structure.get_pymatgen()
    unitcell = get_phonopy_structure(pmgstructure)
    phonon_settings = node.outputs.phonon_setting_info.get_dict()
    phonon = Phonopy(unitcell,
                     supercell_matrix=phonon_settings['supercell_matrix'],
                     primitive_matrix=phonon_settings['primitive_matrix'])
    phonon.set_displacement_dataset(phonon_settings['displacement_dataset'])
    phonon.set_forces(node.outputs.force_sets.get_array('force_sets'))
    phonon.produce_force_constants()
    return phonon

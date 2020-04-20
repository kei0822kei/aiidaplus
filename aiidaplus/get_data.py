#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
get data from aiida pk
"""
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from aiida.orm import load_node
from aiida.common import exceptions
from aiida.cmdline.utils.decorators import with_dbenv

@with_dbenv
def get_node_from_pk(pk):
    """
    get node from pk
    """
    node = load_node(pk)

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
    assert node.process_class == expected_process_class, \
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
    dic['lattice_abc'] = pmgstructure.lattice.abc
    dic['lattice_angles'] = pmgstructure.lattice.angles
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

    Raises:
        Warning: final structure does not exist

    Note:
        symprec=1e-5 (default), which is the same as VASP SYMPREC default
    """
    node = get_node_from_pk(pk)
    check_process_class(node, 'aiida_vasp.workchains.vasp.VaspWorkChain')
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
        raise Warning("final structure does not exist")

    dic = {}
    dic['data_type'] = 'VaspWorkChain'
    dic['pk'] = pk
    dic['incar'] = node.inputs.parameters.get_dict()
    dic['potential_family'] = node.inputs.potential_family.value
    dic['potential_mapping'] = node.inputs.potential_mapping.get_dict()
    dic['kpoints'] = node.inputs.kpoints.get_kpoints_mesh()
    dic['structure'] = structure
    dic['maximum_force'] = results['maximum_force']
    dic['maximum_stress'] = results['maximum_stress']
    dic['energy_no_entropy'] = results['energy_no_entropy']

    return dic

def get_relax_data(pk, symprec=1e-5) -> dict:
    """
    get relax data from pk

    Raises:
        Warning: final vasp calculation is not static calc

    Note:
        symprec=1e-5 (default), which is the same as VASP SYMPREC default
    """
    node = get_node_from_pk(pk)
    check_process_class(node, 'aiida_vasp.workchains.relax.RelaxWorkChain')

    # drop final static calculation
    vasp_pks = [ vasp_node.called[0] for vasp_node in node.called ]
    if 'nsw' in \
            get_node_from_pk(vasp_pks[-1]).inputs.parameters.get_dict():
        del vasp_pks[-1]
    else:
        raise Warning("final vasp calculation is not static calc")
    vasp_pks.reverse()
    vasp_results = {}
    for i, vasp_pk in enumerate(vasp_pks):
        vasp_results['step_%02d' % str(i)] = get_vasp_data(vasp_pk,
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

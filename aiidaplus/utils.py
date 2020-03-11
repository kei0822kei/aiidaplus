#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida utils
"""
import os
import numpy as np
import yaml
from decimal import Decimal, ROUND_HALF_UP
# from yaml import CLoader as Loader
from aiida.orm import StructureData
from pymatgen.core.structure import Structure

def round_off(x:float):
    """
    round off for input value 'x'

    Args:
        x (float): some value

    Returns:
        int: rouned off value

    Examples:
        >>> round_off(4.5)
            5
        >>> round_off(-4.5)
            -5
    """
    return int(Decimal(str(x)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))

def get_grids_from_density(structure:Structure,
                           grid_density:float,
                           direct_or_reciprocal:str,
                           odd_or_even:list=None):
    """
    get grid from structure

    Args:
        structure (pymatgen.core.structure.Structure): structure
        grid_density (float): grid density
        direct_or_reciprocal (str): choose 'direct' or 'reciprocal'
        odd_or_even (list): if you specify as [ 'even', 'odd', None ]
        fix the result list to [ even_num, odd_num, original_num ]

    Returns:
        np.array: grids

    Raises:
        ValueError: either 'direct' or 'reciprocal' did not specified

    Note:
        reciprocal lattice is included 2 pi
    """
    def __fix_num_to_odd_or_even(num, numtype):
        if numtype is None:
            fixed_num = round_off(num)
        else:
            if int(num) % 2 == 0:
                if numtype == 'even':
                    fixed_num = int(num)
                else:
                    fixed_num = int(num) + 1
            else:
                if numtype == 'odd':
                    fixed_num = int(num)
                else:
                    fixed_num = int(num) + 1
        return fixed_num

    if direct_or_reciprocal == 'direct':
        lattice_norms = np.array(
                structure.lattice.abc)
    elif direct_or_reciprocal == 'reciprocal':
        lattice_norms = np.array(
                structure.lattice.reciprocal_lattice.abc)
    else:
        raise ValueError("'direct_or_reciprocal' must be specified as \n \
                          'dicrect' or 'reciprocal'")
    grids_float = np.array(lattice_norms / grid_density)
    if odd_or_even is None:
        grids = np.int64(np.round(grids_float))
    else:
        assert len(odd_or_even) == 3
        grids = np.int64([ __fix_num_to_odd_or_even(num, numtype)
                               for num, numtype in zip(grids_float, odd_or_even) ])
    return grids

def get_elements_from_aiidastructure(aiidastructure:StructureData):
    """
    get elements from aiida structure

    Args:
        aiidastructure (StructureData): aiida structure data

    Returns:
        dict: elements
    """
    elements = [ aiida_ele.get_symbols_string()
            for aiida_ele in aiidastructure.kinds ]
    return elements

def get_default_potcar_mapping(elements:list):
    """
    get default potcar mapping from elements

    Args:
        elements (list): elements

    Returns:
        dict: potcar mapping

    Note:
        default potcar file: /path/to/aiidaplus/potcar/default_potca.yaml
    """
    default_potcar_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'potcar',
            'default_potcar.yaml')
    default_potcars = yaml.load(
            open(default_potcar_file), Loader=yaml.SafeLoader)
    mapping = {}
    for element in elements:
        mapping[element] = default_potcars[element]
    return mapping

def get_encut(potential_family:str,
              potential_mapping:dict,
              multiply:float=1.3):
    """
    get multiplied enmax

    Args:
        potential_family (str): 'PBE.54' or 'LDA.54'
        mapping (dict): potcar mapping
        multiply (float): multiply value

    Returns:
        float: multiplied enmax
    """
    encut_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'potcar',
            'encut_'+potential_family+'.yaml')
    encuts = yaml.load(open(encut_file), Loader=yaml.SafeLoader)
    enmax = max([ encuts[key] for key in list(potential_mapping.values()) ])
    return enmax * multiply

def get_kpoints(structure:Structure=None,
                mesh:list=None,
                kdensity:float=None,
                offset:list=None):
    """
    get preferable kpoints mesh

    Args:
        structure (pymatgen.core.structure.Structure): structure
        mesh (list): the number of kpoints, default:None
        kdensity (float): kdensity included 2*pi in reciprocal lattice,
        default:None
        offset (list): shift from (0,0,0)

    Returns:
        list: mesh
        list: offset

    Raises:
        ValueError: both mesh and kdensity are None
        ValueError: mesh and kdensity are both specified

    Examples:
        description

        >>> print_test ("test", "message")
          test message

    Note:
        description
    """
    if structure is not None:
        is_hexagonal = structure.lattice.is_hexagonal()

    if mesh is None and kdensity is None:
        raise ValueError("mesh or kdensity must be specified")

    if mesh is not None and kdensity is not None:
        raise ValueError("mesh and kdensity are both specified")

    if kdensity is not None:
        if is_hexagonal:
            odd_or_even = ('odd', 'odd', 'even')
        else:
            odd_or_even = ('even', 'even', 'even')
        mesh = get_grids_from_density(structure=structure,
                                      grid_density=kdensity,
                                      direct_or_reciprocal='reciprocal',
                                      odd_or_even=odd_or_even)

    if offset is None:
        if structure.lattice.is_hexagonal():
            offset = [0, 0, 0.5]
        else:
            offset = [0.5, 0.5, 0.5]

    return mesh, offset

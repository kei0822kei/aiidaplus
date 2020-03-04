#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida utils
"""
import os
import numpy as np
import yaml
# from yaml import CLoader as Loader
from aiida.orm import StructureData
from pymatgen.core.structure import Structure

def get_grids_from_density(structure:Structure,
                           grid_density:float,
                           direct_or_reciprocal:str):
    """
    get grid from structure

    Args:
        structure (pymatgen.core.structure.Structure): structure
        grid_density (float): grid density
        direct_or_reciprocal (str): choose 'direct' or 'reciprocal'

    Returns:
        np.array: grids

    Raises:
        ValueError: either 'direct' or 'reciprocal' did not specified

    Note:
        reciprocal lattice is included 2 pi
    """
    if direct_or_reciprocal == 'direct':
        lattice_norms = np.array(
                structure.lattice.abc)
    elif direct_or_reciprocal == 'reciprocal':
        lattice_norms = np.array(
                structure.lattice.reciprocal_lattice.abc)
    grids = np.int64(
        np.round(np.array(lattice_norms / grid_density)))
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida utils
"""
import os
import numpy as np
import yaml
from aiida.orm import StructureData


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


def get_qpoints_from_band_labels(pmgstructure, labels) -> np.array:
    """
    get qpoints from band labels

    Args:
        structure: pymatgen structure
        labels (list): labels of band structure,
                       if you have gamma, write as 'GAMMA'

    Returns:
        np.array: segment qpoints
    """
    import seekpath
    structure = (pmgstructure.lattice.matrix,
                 pmgstructure.frac_coords,
                 [ specie.Z for specie in pmgstructure.species ])
    labels_qpoints = seekpath.get_path(structure)['point_coords']
    qpoints = []
    for label in labels:
        qpoints.append(labels_qpoints[label])
    return np.array(qpoints)

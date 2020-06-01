#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida utils
"""
import os
import numpy as np
import yaml
import math
from pprint import pprint
from decimal import Decimal, ROUND_HALF_UP
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

def get_grids_from_interval(structure:Structure,
                             grid_interval:float,
                             direct_or_reciprocal:str,
                             odd_or_even:list=None):
    """
    get grid from structure

    Args:
        structure (pymatgen.core.structure.Structure): structure
        grid_interval (float): grid intervals
        direct_or_reciprocal (str): choose 'direct' or 'reciprocal'
        odd_or_even (list): if you specify as [ 'even', 'odd', None ]
        fix the result list to [ even_num, odd_num, original_num ]

    Returns:
        dict: grids and intervals

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
        abc = structure.lattice.abc
    elif direct_or_reciprocal == 'reciprocal':
        abc = structure.lattice.reciprocal_lattice.abc
    else:
        raise ValueError("'direct_or_reciprocal' must be specified as \n \
                          'dicrect' or 'reciprocal'")
    lattice_norms = np.array(abc)
    grids_float = lattice_norms / grid_interval
    if odd_or_even is None:
        grids = np.int64(np.round(grids_float))
    else:
        assert len(odd_or_even) == 3
        grids = np.int64([ __fix_num_to_odd_or_even(num, numtype)
                               for num, numtype in zip(grids_float, odd_or_even) ])
    grids = np.where(grids==0, 1, grids)
    intervals = lattice_norms / grids
    return {'grids': grids, 'intervals': intervals}

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

def get_kpoints(structure:Structure,
                mesh:list=None,
                interval:float=None,
                offset:list=None,
                verbose:bool=False):
    """
    get preferable kpoints mesh and kdnesity

    Args:
        structure (pymatgen.core.structure.Structure): structure
        mesh (list): the number of kpoints, default:None
        interval (float): interval included 2*pi in reciprocal lattice,
        default:None
        offset (list): shift from (0,0,0)

    Returns:
        dict: mesh, offset, densities of kpoints of each axis
              and interval in resicprocal lattice

    Raises:
        ValueError: both mesh and intervals are None
        ValueError: mesh and intervals are both specified

    Examples:
        description

        >>> print_test ("test", "message")
          test message

    Note:
        description
    """
    is_hexagonal = structure.lattice.is_hexagonal()
    inputs = {'mesh': mesh, 'interval': interval, 'offset': offset}

    if mesh is None and interval is None:
        raise ValueError("mesh or interval must be specified")

    if mesh is not None and interval is not None:
        raise ValueError("mesh and interval are both specified")

    if interval is not None:
        if is_hexagonal:
            odd_or_even = ('odd', 'odd', 'even')
        else:
            odd_or_even = ('even', 'even', 'even')
        kgrids = get_grids_from_interval(
                    structure=structure,
                    grid_interval=interval,
                    direct_or_reciprocal='reciprocal',
                    odd_or_even=odd_or_even)
        kgrids['mesh'] = kgrids['grids']
        del kgrids['grids']
    else:
        lattice_norms = np.array(structure.lattice.reciprocal_lattice.abc)
        intervals = lattice_norms / mesh
        kgrids = {'mesh': mesh, 'intervals': intervals}

    if offset is None:
        if structure.lattice.is_hexagonal():
            offset = [0, 0, 0.5]
        else:
            offset = [0.5, 0.5, 0.5]
        for i in range(len(kgrids['mesh'])):
            if kgrids['mesh'][i] % 2 == 1:
                offset[i] = 0

    kgrids['offset'] = offset

    m = kgrids['mesh']
    vol_per_mesh = structure.lattice.reciprocal_lattice.volume / (m[0]*m[1]*m[2])
    # ave_interval = vol_per_mesh ** (1/3)
    ave_interval = np.average(kgrids['intervals'])
    kgrids['ave_interval'] = float(ave_interval)
    kgrids['density'] = m[0]*m[1]*m[2] / structure.lattice.reciprocal_lattice.volume

    if verbose:
        print("lattice:")
        print(structure.lattice)
        print("")
        print("reciprocal lattice (including 2pi):")
        print(structure.lattice.reciprocal_lattice)
        print("")
        print("inputs:")
        pprint(inputs)
        print("")
        print("outputs:")
        print("# unit of interval is [/anstrome]")
        print("# unit of density is [angstrome^3]")
        # print("# ave_interval is math.pow(recip_vol_per_mesh, 1/3)")
        print("# ave_interval is the average of interval of each axis")
        pprint(kgrids)

    return kgrids

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

def get_default_labels_of_twinmode(twinmode) -> list:
    """
    get default labels of twinmode
    """
    # if twinmode == '10-12':
    #     labels = ['A', 'H', 'K', 'GAMMA', 'M', 'L', 'A']
    # else:
    #     raise ValueError("twinmode: {} is currently not supported" % twinmode)
    labels = ['A', 'H', 'K', 'GAMMA', 'M', 'L', 'A']
    return labels


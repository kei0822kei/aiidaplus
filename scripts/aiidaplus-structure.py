#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
import warnings
import numpy as np
from pprint import pprint
from aiida.cmdline.utils.decorators import with_dbenv
from phonopy.structure.atoms import symbol_map, atom_data
from phonopy.interface.vasp import sort_positions_by_symbols
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.structure import Structure
from pymatgen.io.phonopy import get_pmg_structure
from aiidaplus.get_data import get_structure_data_from_pymatgen
from twinpy.structure.base import get_phonopy_structure
import spglib

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--filename', type=str, default=None,
        help="input file name or structure pk")
    parser.add_argument('-t', '--filetype', type=str, default=None,
        help="input file type, currently supported 'cif' or 'poscar' or 'pk'")
    parser.add_argument('--label', type=str, default='',
        help="add label to the structure node")
    parser.add_argument('--description', type=str, default='',
        help="if '', description becomes the same as label")
    parser.add_argument('--get_cif', action='store_true',
        help="get cif file")
    parser.add_argument('--get_json', action='store_true',
        help="get json file")
    parser.add_argument('--get_cssr', action='store_true',
        help="get cssr file")
    parser.add_argument('--get_poscar', action='store_true',
        help="get poscar file")
    parser.add_argument('--add_db', action='store_true',
        help="import structure to aiida database")
    parser.add_argument('--group', type=str, default=None,
        help="if not None, add structure to specified group")
    parser.add_argument('--conventional', action='store_true',
        help="if True, get conventinoal structure")
    parser.add_argument('--primitive', action='store_true',
        help="if True, get primitive strucutre")
    parser.add_argument('--sort_by_symbols', action='store_true',
        help="sort atoms by symbols")
    parser.add_argument('--show', action='store_true',
        help="get description about structure")
    parser.add_argument('--symprec', type=float, default=1e-5,
        help="symprec")
    args = parser.parse_args()
    return args

def get_pmgstructure(filename, filetype, symprec):
    """
    get pymatgen structure object

        Parameters
        ----------
        filename : str
            input file name
        filetype : str
            file type of 'filename'
            currently supported 'cif' or 'poscar'

        Notes
        -----
        occupancy_tolerance = 1.
        - If total occupancy of a site is between 1 and
          occupancy_tolerance, the occupancies will be scaled down to 1.

        site_tolerance = 1e-5
        - This tolerance is used to determine if two sites are sitting
          in the same position, in which case they will be combined to
          a single disordered site.
        - 1e-5 is the same as VASP SYMPREC defualt

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    occupancy_tolerance = 1.

    if filetype == 'cif':
        from pymatgen.io import cif as pmgcif
        cif = pmgcif.CifParser(filename,
                               occupancy_tolerance=occupancy_tolerance,
                               site_tolerance=symprec)
        pmgstruct = cif.get_structures()[0]
    elif filetype == 'poscar':
        from pymatgen.io.vasp import inputs as pmginputs
        poscar = pmginputs.Poscar.from_file(filename)
        pmgstruct = poscar.structure
    elif filetype == 'pk':
        from aiida.orm import load_node
        node = load_node(int(filename))
        pmgstruct = node.get_pymatgen_structure()
    else:
        raise ValueError("specified filetype is not supported")
    return pmgstruct

def get_atomic_numbers(symbols):
    """
    get atomic numbers from symbols
    """
    numbers = [ symbol_map[symbol] for symbol in symbols ]
    return numbers

def get_chemical_symbols(numbers):
    """
    get chemical symbols from atomic numbers
    """
    symbols = [ atom_data[num][0] for num in numbers ]
    return symbols

def get_cell_from_pmgstructure(pmgstructure):
    lattice = pmgstructure.lattice.matrix
    scaled_positions = pmgstructure.frac_coords
    symbols = [ specie.value for specie in pmgstructure.species ]
    return (lattice, scaled_positions, symbols)

def export_structure(pmgstruct, filetype):
    structure_filename = {
            'poscar': 'POSCAR',
            'cif': 'structure.cif',
            'cssr': 'structure.cssr',
            'json': 'structure.json'
               }
    pmgstruct.to(fmt=filetype, filename=structure_filename[filetype])

def get_description(pmgstruct, symprec):
    from pymatgen.io import vasp as pmgvasp
    data = get_structure_data_from_pymatgen(pmgstruct, symprec=symprec)
    for key in data:
        if key == 'wyckoffs' or key == 'site_symmetry_symbols':
            print(key)
            if len(data[key]) > 5:
                continue
        print(key+':')
        pprint(data[key])

def import_to_aiida(pmgstruct, label, description, group=None):
    from aiida.orm.nodes.data import StructureData
    from aiida.orm import Group
    structure = StructureData(pymatgen_structure=pmgstruct)
    structure.label = label
    if description == '':
        structure.description = label
    else:
        structure.description = description
    structure.store()
    print("structure data imported")
    print("pk : %s \n" % str(structure.pk))
    print("# to check the imported structure")
    print("verdi data structure export %s \n" % str(structure.pk))
    if group is not None:
        grp = Group.get(label=group)
        grp.add_nodes(structure)
        print("structure {0} has added to group '{1}'".format(
            structure.pk, group))

def standardize_structure(pmgstruct,
                          structure_type,
                          symprec,
                          sort_by_symbols=False,
                          engine='phonopy'):
    """
    structure_type = 'primitive' or 'conventional'
    sort_by_symbols: if True, sort symbols and scaled_positions
    in order to make 'Al' 'O' 'Si' 'Al' 'O' 'Si' to 'Al' 'O' 'Si'
    """
    assert structure_type in ['primitive', 'conventional'], \
            "structure_type must be 'primitive' or 'conventional'"
    if engine == 'pymatgen':
        struct_analyzer = SpacegroupAnalyzer(pmgstruct, symprec=symprec)
        if structure_type == 'primitivie':
            print("primitive standardizing structure\n")
            structure = struct_analyzer.get_primitive_standard_structure()
        else:
            print("conventional standardizing structure\n")
            structure = struct_analyzer.get_conventional_standard_structure()
    elif engine == 'phonopy':
        cell = get_cell_from_pmgstructure(pmgstruct)
        numbers = get_atomic_numbers(cell[2])
        cell_spglib = (cell[0], cell[1], numbers)

        if structure_type == 'primitive':
            to_primitive = True
        else:
            to_primitive = False
        std_cell = spglib.standardize_cell(cell=cell_spglib,
                                           to_primitive=to_primitive,
                                           symprec=symprec)
        if sort_by_symbols:
            posi_orig = std_cell[1]
            num_atoms, unique_symbols, scaled_positions, _ = \
                sort_positions_by_symbols(symbols=get_chemical_symbols(std_cell[2]),
                                          positions=std_cell[1])
            symbols = []
            for num, symbol in zip(num_atoms, unique_symbols):
                symbols.extend([symbol] * num)

            if not np.allclose(posi_orig, scaled_positions):
                warnings.warn("atoms order has changed")
            std_cell = (std_cell[0], scaled_positions, symbols)

        structure = Structure(lattice=std_cell[0],
                              coords=std_cell[1],
                              species=std_cell[2])

    return structure

@with_dbenv()
def main(filename,
         filetype,
         get_cif,
         get_cssr,
         get_json,
         get_poscar,
         add_db,
         group,
         conventional,
         primitive,
         show,
         label,
         description,
         sort_by_symbols,
         symprec):

    pmgstruct = get_pmgstructure(filename, filetype, symprec)

    if primitive:
        pmgstruct = standardize_structure(pmgstruct=pmgstruct,
                                          structure_type='primitive',
                                          sort_by_symbols=sort_by_symbols,
                                          symprec=symprec,)
    if conventional:
        pmgstruct = standardize_structure(pmgstruct=pmgstruct,
                                          structure_type='conventional',
                                          sort_by_symbols=sort_by_symbols,
                                          symprec=symprec)

    if show:
        get_description(pmgstruct, symprec)
    if get_cif:
        export_structure(pmgstruct, 'cif')
    if get_cssr:
        export_structure(pmgstruct, 'cssr')
    if get_json:
        export_structure(pmgstruct, 'json')
    if get_poscar:
        export_structure(pmgstruct, 'poscar')
    if add_db:
        import_to_aiida(pmgstruct, label, description, group)

if __name__ == '__main__':
    args = get_argparse()
    if args.primitive and args.conventional:
        raise ValueError("both primitive and conventional activated")

    main(filename=args.filename,
         filetype=args.filetype,
         get_cif=args.get_cif,
         get_cssr=args.get_cssr,
         get_json=args.get_json,
         get_poscar=args.get_poscar,
         add_db=args.add_db,
         group=args.group,
         conventional=args.conventional,
         primitive=args.primitive,
         show=args.show,
         label=args.label,
         description=args.description,
         sort_by_symbols=args.sort_by_symbols,
         symprec=args.symprec)

#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
from aiida.cmdline.utils.decorators import with_dbenv
aiidaplus_vasp = __import__("aiidaplus-vasp")

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
    parser.add_argument('--standardize', action='store_true',
        help="if True, standardize structure")
    parser.add_argument('--primitive', action='store_true',
        help="if True, find primitive strucutre")
    parser.add_argument('--show', action='store_true',
        help="get description about structure")
    args = parser.parse_args()
    return args

def get_pmgstructure(filename, filetype, primitive):
    """
    get pymatgen structure object

        Parameters
        ----------
        filename : str
            input file name
        filetype : str
            file type of 'filename'
            currently supported 'cif' or 'poscar'
        primitive : bool
            if True, return primitive structure

        Notes
        -----
        occupancy_tolerance = 1.
        - If total occupancy of a site is between 1 and
          occupancy_tolerance, the occupancies will be scaled down to 1.

        site_tolerance = 1e-4
        - This tolerance is used to determine if two sites are sitting
          in the same position, in which case they will be combined to
          a single disordered site.

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    occupancy_tolerance = 1.
    site_tolerance = 1e-4

    if filetype == 'cif':
        from pymatgen.io import cif as pmgcif
        cif = pmgcif.CifParser(filename,
                               occupancy_tolerance=occupancy_tolerance,
                               site_tolerance=site_tolerance)
        pmgstruct = cif.get_structures(primitive=primitive)[0]
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

def export_structure(pmgstruct, filetype):
    structure_filename = {
            'poscar': 'POSCAR',
            'cif': 'structure.cif',
            'cssr': 'structure.cssr',
            'json': 'structure.json'
               }
    pmgstruct.to(fmt=filetype, filename=structure_filename[filetype])

def get_description(pmgstruct):
    from pymatgen.io import vasp as pmgvasp
    poscar = pmgvasp.Poscar(pmgstruct)
    print("-----------------")
    print("STRUCTURE DETAILS")
    print("-----------------")
    print('Object Type: StructureData')
    print('Lattice')
    print(pmgstruct.lattice)
    print('Site Symbols')
    print(poscar.site_symbols)
    print('Number of Atoms')
    print(poscar.natoms)
    print('Space Group')
    print(pmgstruct.get_space_group_info())

def import_to_aiida(pmgstruct, label, group=None):
    from aiida.orm.nodes.data import StructureData
    from aiida.orm import Group
    structure = StructureData(pymatgen_structure=pmgstruct)
    structure.label = label
    structure.description = label
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

def standardize_structure(pmgstruct, primitive=False):
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    struct_analyzer = SpacegroupAnalyzer(pmgstruct)
    if primitive:
        print("primitive standardizing structure\n")
        structure = struct_analyzer.get_primitive_standard_structure()
    else:
        print("conventional standardizing structure\n")
        structure = struct_analyzer.get_conventional_standard_structure()
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
         standardize,
         primitive,
         show,
         label):

    if group is not None:
        aiidaplus_vasp.check_group_existing(group)

    pmgstruct = get_pmgstructure(filename, filetype, primitive)
    if standardize:
        pmgstruct = standardize_structure(pmgstruct, primitive)
    if show:
        get_description(pmgstruct)
    if get_cif:
        export_structure(pmgstruct, 'cif')
    if get_cssr:
        export_structure(pmgstruct, 'cssr')
    if get_json:
        export_structure(pmgstruct, 'json')
    if get_poscar:
        export_structure(pmgstruct, 'poscar')
    if add_db:
        import_to_aiida(pmgstruct, label, group)

if __name__ == '__main__':
    args = get_argparse()
    main(filename=args.filename,
         filetype=args.filetype,
         get_cif=args.get_cif,
         get_cssr=args.get_cssr,
         get_json=args.get_json,
         get_poscar=args.get_poscar,
         add_db=args.add_db,
         group=args.group,
         standardize=args.standardize,
         primitive=args.primitive,
         show=args.show,
         label=args.label)

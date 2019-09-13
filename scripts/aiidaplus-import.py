#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you import various data to aiida database.
"""

import argparse
from aiida.cmdline.utils.decorators import with_dbenv

# argparse
parser = argparse.ArgumentParser(
    description="This script helps you import various data to aiida database.")
parser.add_argument('-f', '--filename', type=str, default=None,
    help="input file name")
parser.add_argument('-t', '--filetype', type=str, default=None,
    help="input file type, currently supported 'cif' or 'poscar'")
parser.add_argument('-c', '--comment', type=str, default=None,
    help="comment which is included with imported data")
args = parser.parse_args()


# functions
def import_StructureData(filename, filetype, comment):
    """
    import StructureData

        Parameters
        ----------
        filename : str
            input file name
        filetype : int, default var
            file type of 'filename'
            currently supported 'cif' or 'poscar'
        comment : str

        Notes
        -----
        occupancy_tolerance = 1.
        - If total occupancy of a site is between 1 and
          occupancy_tolerance, the occupancies will be scaled down to 1.

        site_tolerance = 1e-4
        - This tolerance is used to determine if two sites are sitting
          in the same position, in which case they will be combined to
          a single disordered site.

        primitive = False
        - When the input cif file convert to the pymatgen structure,
          do not try to find primitive.

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    from aiida.orm.nodes.data import StructureData

    occupancy_tolerance = 1.
    site_tolerance = 1e-4
    primitive = False

    if filetype == 'cif':
        from pymatgen.io import cif as pmgcif
        cif = pmgcif.CifParser(filename,
                               occupancy_tolerance=occupancy_tolerance,
                               site_tolerance=site_tolerance)
        pmgstruct = cif.get_structures(primitive=primitive)
    elif filetype == 'poscar':
        from pymatgen.io.vasp import inputs as pmginputs
        poscar = pmginputs.Poscar.from_file(filename)
        pmgstruct = StructureData(pymatgen_structure=poscar.structure)
    else:
        raise ValueError("specified filetype is not supported")
    structure = StructureData(pymatgen_structure=poscar.structure)
    structure.store()
    structure.add_comment(comment)
    print("structure data imported")
    print("pk : %s \n" % str(structure.pk))
    print("# to check the imported structure")
    print("verdi data structure export %s \n" % str(structure.pk))
    print("# to check the comment")
    print("verdi comment show %s" % str(structure.pk))


@with_dbenv()
def main(filename, filetype, comment):
    """
    import data with comment

        Parameters
        ----------
        filename : str
            input file name
        filetype : int, default var
            file type of 'filename'
            currently supported 'cif' or 'poscar'
        comment : str

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    if filetype in ['cif', 'poscar']:
        import_StructureData(filename, filetype, comment)
    else:
        raise ValueError("specified filetype is not supported")


if __name__ == '__main__':
    print("# inputs")
    print("filename : %s" % str(args.filename))
    print("filetype : %s" % str(args.filetype))
    print("comment  : %s \n" % str(args.comment))
    main(args.filename, args.filetype, args.comment)

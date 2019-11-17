#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida-vasp calculation toolkits
-------------------------------
definitions which help aiida-vasp calculation
"""
import os
import numpy as np
import yaml
from yaml import CLoader as Loader
from aiida.orm import load_node
from aiida.orm.nodes.data import KpointsData


def default_params(filetype, is_metal, structure_pk=None, kdensity=None):
    """
    description of this method

        Parameters
        ----------
        filetype : str
            input filetype setting file are exported
            choose from 'oneshot', 'relax' or 'phonon'
        is_metal : bool
            if structure is metallic, choose True
            otherwise, choose False
        structure_pk : int, default None
            if you set 'structure_pk', set stucture
        kdensity : float, default None
            if you set 'kdensity' and 'structure_pk',
            consider the density of kpoints.
            INCLUDED 2 pi

        Returns
        -------
        dic : dict
            params for running aiida-vasp

        Notes
        -----

        Raises
        ------
        ValueError
            conditions which ValueError occurs
    """
    def _label_descrip(dic):
        dic['label'] = "this is label"
        dic['description'] = "this is description"

    def _get_structuredata_from_node(structure_pk):
        if structure_pk is None:
            structure_data = None
        else:
            print("load struecture % s" % str(structure_pk))
            structure_data = load_node(structure_pk)
            pmgstruct = structure_data.get_pymatgen_structure()
            print("lattice:")
            print(pmgstruct.lattice)
            print('symbols:')
            print(structure_data.get_symbols_set())
            print("atoms:")
            print(len(pmgstruct.frac_coords))
        return structure_data

    def _structure(dic, structure_pk):
        if structure_pk is None:
            dic['structure_pk'] = 'structure pk (int)'
        else:
            dic['structure_pk'] = structure_pk

    def _clean_workingdir(dic):
        dic['clean_workdir'] = False

    def _incar_params(dic, is_metal, get_encut_from_structure=False):
        def __get_encut():
            if get_encut_from_structure:
                print("set encut from structure")
                encut_file = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'potcar',
                        'encut_'+dic['potcar']['potential_family']+'.yaml')
                encuts_db = yaml.load(open(encut_file), Loader=Loader)
                max_encut = max([ encuts_db[key] for key
                        in dic['potcar']['potential_mapping'] ])
                print("max_encut was %s" % str(max_encut))
                print("multiply by 1.3")
                encut = int(max_encut * 1.3)
                print("set encut: %s" % str(encut))
                return encut
            else:
                print("encut in incar parameters are set automatically '375'")
                encut = 375
            return encut


        def __incar_params_base(incar_dic, is_metal):
            incar_dic['incar_base'] = {
                     'system': 'system name',
                     'prec': 'Accurate',
                     'addgrid': True,
                     'ediff': 1e-6,
                     'ialgo': 38,
                     'lcharg': False,
                     'lreal': False,
                     'lwave': False,
                     # 'lepsilon': True,
                     # 'icharg': 1,
                     # 'istart': 1,
                     'gga': 'PS',
                     'npar': 4
                  }
            if is_metal:
                static_opt = {
                     'ismear': 1,
                     'sigma': 0.2
                  }
            else:
                static_opt = {
                     'ismear': 0,
                     'sigma': 0.01,
                  }
            incar_dic['incar_base'].update(static_opt)

        dic['incar'] = {}
        dic['incar']['encut'] = __get_encut()
        __incar_params_base(dic['incar'], is_metal)

    def _kpoints(dic, structure_data, kdensity):
        if kdensity is not None:
            kdata = KpointsData()
            kdata.set_cell_from_structure(structure_data)
            print("kdensity is: %s" % str(kdensity))
            print("reciprocal lattice (included 2*pi) is:")
            print(kdata.reciprocal_cell)
            print("set kpoints mesh as:")
            kdata.set_kpoints_mesh_from_density(
                    kdensity, offset=[0.5,0.5,0.5])
            kmesh = kdata.get_kpoints_mesh()
            print(kmesh[0])
            dic['kpoints'] = {
                  'mesh': kmesh[0],
                  'offset': kmesh[1]
                }
        else:
            dic['kpoints'] = {
                  'mesh' : [6,6,6],
                  'offset' : [0.5,0.5,0.5]
                }
        if filetype == 'phonon':
            dic['kpoints']['mesh_fc2'] = [2,2,2]
            dic['kpoints']['mesh_nac'] = [12,12,12]

    def _potcar(dic, structure_data):
        if structure_data is not None:
            default_potcar_file = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'potcar',
                    'default_potcar.yaml')
            default_potcars = yaml.load(
                    open(default_potcar_file), Loader=Loader)
            mapping = {}
            for element in list(structure_data.get_symbols_set()):
                mapping[element] = default_potcars[element]
        else:
            mapping = {
                        'Ga': 'Ga',
                        'As': 'As'
                      }
        dic['potcar'] = {
            'potential_family': 'PBE.54',
            'potential_mapping': mapping
          }

    def _relax_conf(dic):
        if filetype == 'relax':
            dic['relax_conf'] = {
                'perform': True,
                'energy_cutoff': 1e-6,  # default, False
                'force_cutoff': 1e-4,  # default, False
                'steps': 20,  # default, 60
                'positions': True,
                'shape': True,
                'volume': True,
                'convergence_on': True,
                'convergence_absolute': False,
                'convergence_max_iterations': 3,
                'convergence_volume': 0.01,
                'convergence_positions': 0.01,
                'convergence_shape_lengths': 0.1,
                'convergence_shape_angles': 0.1
              }

    def _phonon_conf(dic):
        if filetype == 'phonon':
            dic['phonon_conf'] = {}
            dic['phonon_conf']['phonon_settings'] = {
                'supercell_matrix': [2,2,2],
                'distance': 0.03,
                'mesh': 50.0,  # ?? what is this setting?
                'is_nac': True
              }
            dic['phonon_conf']['symmetry_tolerance'] = 1e-5

    dic = {}
    _label_descrip(dic)
    structure_data = _get_structuredata_from_node(structure_pk)
    _structure(dic, structure_pk)
    _clean_workingdir(dic)
    _kpoints(dic, structure_data, kdensity)
    _potcar(dic, structure_data)
    if structure_pk is None:
        _incar_params(dic, is_metal, get_encut_from_structure=False)
    else:
        _incar_params(dic, is_metal, get_encut_from_structure=True)
    _relax_conf(dic)
    _phonon_conf(dic)
    return dic

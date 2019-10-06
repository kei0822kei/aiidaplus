#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aiida-vasp calculation toolkits
-------------------------------
definitions which help aiida-vasp calculation
"""

def default_params(filetype, is_metal):
    """
    description of this method

        Parameters
        ----------
        filetype : str
            input filetype setting file are exported
            choose from 'oneshot', 'relax' or 'phonopy'
        is_metal : bool
            if structure is metallic, choose True
            otherwise, choose False

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
    def _structure(dic):
        dic['structure_pk'] = 'structure pk (int)'

    def _clean_workingdir(dic):
        dic['clean_workdir'] = False

    def _incar_params(dic, is_metal):
        def __incar_params_base(incar_dic, is_metal):
            incar_dic['incar_base'] = {
                     'system': 'system name',
                     'prec': 'Accurate',
                     'addgrid': True,
                     'encut': 375,
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
                     # 'ismear': -5
                     'ismear': 0,
                     'sigma': 0.01,
                  }
            incar_dic['incar_base'].update(static_opt)

        def __incar_params_relax(incar_dic):
            incar_dic['incar_relax'] = {
                    'ediffg': -0.0001,
                    'ibrion': 2,
                    'nsw' : 20,
                    'isif': 3
                  }

        dic['incar'] = {}
        __incar_params_base(dic['incar'], is_metal)
        __incar_params_relax(dic['incar'])

    def _relax_conf(dic):
        if filetype == 'relax':
            dic['relax_conf'] = {
                  'relax': True,
                  # 'steps': 60,  # does not work? 2019/10/05
                  # 'positions': True,  # does not work? 2019/10/05
                  # 'shape': True,  # does not work? 2019/10/05
                  # 'volume': True,  # does not work? 2019/10/05
                  'convergence_on': True,
                  'convergence_absolute': False,
                  'convergence_max_iterations': 3,
                  # 'convergence_shape_lengths': 0.1,
                  'convergence_shape_lengths': 0.5,
                  # 'convergence_shape_angles': 0.1,
                  'convergence_shape_angles': 0.5,
                  # 'convergence_volume': 0.01,
                  'convergence_volume': 0.1,
                  # 'convergence_positions': 0.01
                  'convergence_positions': 0.1,
            }

    def _kpoints(dic):
        dic['kpoints'] = {
              'mesh' : [6,6,6],
              'offset' : [0.5,0.5,0.5]
            }

    def _potcar(dic):
        dic['potcar'] = {
            'potential_family': 'PBE.54',
            'potential_mapping': {
                 'Ga': 'Ga',
                 'As': 'As'
              }
          }

    dic = {}
    _structure(dic)
    _clean_workingdir(dic)
    _incar_params(dic, is_metal)
    _kpoints(dic)
    _potcar(dic)
    _relax_conf(dic)
    return dic

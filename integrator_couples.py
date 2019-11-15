#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is integrator for couples

"""

import numpy as np
#from renegotiation import v_last_period_renegotiated, v_renegotiated_loop
from ren_mar import v_ren, v_ren2
from ren_mar_alt import v_ren_new
    

def ev_couple(setup,Vpostren,t,use_sparse=True,return_vren=False):
    # computes expected value of couple entering the next period with an option
    # to renegotiate or to break up
    
    
    _Vren = v_ren(setup,Vpostren,interpolate=True) # does renegotiation
        
    
    
    Vren = {'M':{'V':_Vren[0],'VF':_Vren[1],'VM':_Vren[2]},
            'SF':Vpostren['Female, single'],
            'SM':Vpostren['Male, single']}
    
    # accounts for exogenous transitions
    EV, EVf, EVm = ev_couple_exo(setup,Vren['M'],t,use_sparse)
    
    if return_vren:
        return EV, EVf, EVm, Vren
    else:
        return EV, EVf, EVm
    
def ev_couple_m_c(setup,Vpostren,t,marriage,use_sparse=True,return_vren=False):
    # computes expected value of couple entering the next period with an option
    # to renegotiate or to break up
    
    
    _Vren = v_ren2(setup,Vpostren,marriage,t,interpolate=True) # does renegotiation
    
    
    _Vren2 = v_ren_new(setup,Vpostren,marriage,t,interpolate=True)['Values']
    
    
    
    Vren = {'M':{'V':_Vren[0],'VF':_Vren[1],'VM':_Vren[2]},
            'SF':Vpostren['Female, single'],
            'SM':Vpostren['Male, single']}
    
    
    
    Vren2 = {'M':{'V':_Vren2[0],'VF':_Vren2[1],'VM':_Vren2[2]},
            'SF':Vpostren['Female, single'],
            'SM':Vpostren['Male, single']}
    
    # accounts for exogenous transitions
    EV, EVf, EVm = ev_couple_exo(setup,Vren['M'],t,use_sparse)
    EV2, EVf2, EVm2 = ev_couple_exo(setup,Vren2['M'],t,use_sparse)
    
    
    print('Max diff in EV = {}'.format(np.max(np.abs(EV2-EV))))
    
    if return_vren:
        return EV, EVf, EVm, Vren
    else:
        return EV, EVf, EVm


def ev_couple_exo(setup,Vren,t,use_sparse=True):
    
 
    # this does dot product along 3rd dimension
    # this takes V that already accounts for renegotiation (so that is e
    # expected pre-negotiation V) and takes expectations wrt exogenous shocks
    
    
    if use_sparse:
        
        M = setup.exogrid.all_t_mat_sparse_T[t]      
        def integrate_array(x):
            xout = np.zeros_like(x)
            for itheta in range(x.shape[2]):
                xout[...,itheta] = x[...,itheta]*M                
            return xout
    else:
        
        M = setup.exogrid.all_t_mat[t].T        
        def integrate_array(x):
            xout = np.zeros_like(x)
            for itheta in range(x.shape[2]):
                xout[...,itheta] = np.dot(x[...,itheta], M)                
            return xout  
        
        
        
    
    EV, EVf, EVm = tuple( (integrate_array(a) for a in (Vren['V'],Vren['VF'],Vren['VM'])) )
    
    
    return EV, EVf, EVm
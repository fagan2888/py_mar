#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 13:48:13 2020

@author: egorkozlov
"""

import numpy as np
from aux_routines import first_true, last_true
from numba import njit, vectorize
from gridvec import VecOnGrid



def v_mar_igrid(setup,t,V,icouple,ind_or_inds,*,female,marriage,interpolate=True,return_all=False):
    # this returns value functions for couple that entered the last period with
    # (s,Z,theta) from the grid and is allowed to renegotiate them or breakup
    
    # if return_all==False returns Vout_f, Vout_m, that are value functions
    # of male and female from entering this union
    # if return_all==True returns (Vout_f, Vout_m, ismar, thetaout, technical)
    # where ismar is marriage decision, thetaout is resulting theta and 
    # tuple technical contains less usable stuff (check v_newmar_core for it)
    #
    # combine = True creates matrix (n_s-by-n_inds)
    # combine = False assumed that n_s is the same shape as n_inds and creates
    # a flat array.
    
    #This differs from previous since here the choice between marriage and 
    #cohabitation is couple based and taken here. For a given bargaining power and other
    #states the couple decides to 
    
    
    which=V['Couple, M']['V'][icouple,...]>= V['Couple, C']['V'][icouple,...]
    
    
    dtype = setup.dtype
    # import objects
    agrid_c = setup.agrid_c
    agrid_s = setup.agrid_s
   
    
    
    VMval_single, VFval_single = V['Male, single']['V'], V['Female, single']['V']
    VMval_postren = V['Couple, M']['VM'][icouple,...]*which+(1-which)*V['Couple, C']['VM'][icouple,...]
    VFval_postren = V['Couple, M']['VF'][icouple,...]*which+(1-which)*V['Couple, C']['VF'][icouple,...]
    
    
    
    # substantial part
    ind, izf, izm, ipsi = setup.all_indices(t,ind_or_inds)
    
    
    # using trim = True implicitly trims things on top
    # so if sf is 0.75*amax and sm is 0.75*amax then sc is 1*amax and not 1.5
    
    #sc = sf+sm # savings of couple
    s_partner = agrid_c[icouple] - agrid_s # we assume all points on grid
    
    
    # this implicitly trims negative or too large values
    s_partner_v = VecOnGrid(agrid_s,s_partner,trim=True) 
    
    
    # this applies them
    
    if female:
        Vfs = VFval_single[:,izf]
        Vms = s_partner_v.apply(VMval_single,axis=0,take=(1,izm))
    else:
        Vms = VMval_single[:,izm]
        Vfs = s_partner_v.apply(VFval_single,axis=0,take=(1,izf))
        
        
 
    
   
    expnd = lambda x : setup.v_thetagrid_fine.apply(x,axis=2)
    
    
    Vmm, Vfm = (expnd(x[:,ind,:]) for x in 
                     (VMval_postren,VFval_postren))
    
    assert Vmm.dtype==dtype
   
    ins = [Vfm,Vmm,Vfs,Vms]
    ins = [x.astype(dtype,copy=False) for x in ins] # optional type conversion
  
   
    vfout, vmout, nbsout, agree, ithetaout,i_mar = mar_loop(Vfm,Vmm,Vfs,Vms,which)
    
   


    return {'Values': (vfout, vmout), 'NBS': nbsout, 'theta': ithetaout, 'Decision':agree, 'i_mar':(agree) & (i_mar)}



def v_no_mar(setup,t,V,icouple,ind_or_inds,*,female,marriage):
    # emulates v_mar_igrid but with no marriage
    
    
    ind, izf, izm, ipsi = setup.all_indices(t,ind_or_inds)
    
    vmout, vfout = V['Male, single']['V'][:,izm], V['Female, single']['V'][:,izf]
    
    
    nbsout = np.zeros_like(vmout,dtype=np.float64)
    ithetaout = -np.ones_like(vmout,dtype=np.int16)
    agree = np.full_like(vmout,False,dtype=np.bool)
    i_mar = np.full_like(vmout,False,dtype=np.bool)
    
    return {'Values': (vfout, vmout), 'NBS': nbsout, 'theta': ithetaout, 'Decision':agree,'i_mar':i_mar}




@njit
def mar_loop(vfy,vmy,vfn,vmn,which):

    shp=vfy.shape
    
    sf=np.empty(shp,dtype=np.float64)
    sm=np.empty(shp,dtype=np.float64)
    
    sf = vfy - np.expand_dims(vfn,vfn.ndim)
    sm = vmy - np.expand_dims(vmn,vmn.ndim)
    
    na, nexo, nt = vfy.shape
    
    #vout = np.zeros((vy.shape[:-1]),np.float32)
    vfout = vfn.copy()
    vmout = vmn.copy()
    nbsout = np.zeros(vfn.shape)
    
    ithetaout = np.full(vfout.shape,-1,dtype=np.int16)
    agree = np.zeros(vfout.shape,dtype=np.bool_)
    whichout = np.zeros(vfout.shape,dtype=np.bool_)
    
    ntheta = vfy.shape[-1]
    
    for ia in range(na):
        for iexo in range(nexo):
            sf_i = sf[ia,iexo,:]
            sm_i = sm[ia,iexo,:]
            
            both = (sf_i >= 0) & (sm_i >= 0)
            
            good = np.any(both)
             
            agree[ia,iexo] = good
            f1 = np.float64(1)
            
            if good:
                nbs = np.zeros(ntheta,dtype=np.float64)
                nbs[both] = sf_i[both]* sm_i[both]
                i_best = 5#nbs.argmax()
                nbs_best = nbs[i_best]

                    
                ithetaout[ia,iexo] = i_best
                vfout[ia,iexo] = vfy[ia,iexo,i_best]
                vmout[ia,iexo] = vmy[ia,iexo,i_best]
                nbsout[ia,iexo] = nbs_best
                whichout[ia,iexo]=which[ia,iexo,i_best]
                
              
   
    
    return vfout, vmout, nbsout, agree, ithetaout, whichout
            


@vectorize('float64(float64,float64,float64)')  
def nbs(x,y,gamma):
    if x > 0 and y > 0:
        return (x**gamma) * (y**(1-gamma))
    else:
        return 0
                        


def mar_mat(vfy,vmy,vfn,vmn,gamma,t,setup):

    sf = vfy - np.expand_dims(vfn,vfn.ndim)
    sm = vmy - np.expand_dims(vmn,vmn.ndim)
    
    
    
    #vout = np.zeros((vy.shape[:-1]),np.float32)
    vfout = vfn.copy()
    vmout = vmn.copy()
    
    
    agree = (sf>=0) & (sm>=0)
    any_agree = np.any(agree,axis=-1)
    
    # this reshapes things
    n_agree = np.sum(any_agree)
    
    nbsout = np.zeros(vfn.shape,dtype=np.float64)
    ithetaout = -1*np.ones(vfn.shape,dtype=np.int32)
    
    
    if n_agree > 0:       
        
        sf_a = sf[any_agree,:]
        sm_a = sm[any_agree,:]
        nbs_a = np.zeros(sf_a.shape,dtype=np.float64)
        
        a_pos = (sf_a>=0) & (sm_a>=0)
        
        nbs_a[a_pos] = (sf_a[a_pos]**gamma) * (sm_a[a_pos]**(1-gamma))
        inds_best = np.argmax(nbs_a,axis=1)
        
        take = lambda x : np.take_along_axis(x,inds_best[:,None],axis=1).reshape((n_agree,))
        
        nbsout[any_agree] = take(nbs_a) 
        assert np.all(nbsout[any_agree] > 0)
        ithetaout[any_agree] = inds_best
        vfout[any_agree] = take(vfy[any_agree,:])
        vmout[any_agree] = take(vmy[any_agree,:])
        
    
        
        
    return vfout, vmout, nbsout, any_agree, ithetaout
        

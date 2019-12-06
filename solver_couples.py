#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is solver for those who are couples at period 0
"""
import numpy as np
from timeit import default_timer


from optimizers import get_EVM
from optimizers import v_optimize_couple

from platform import system

if system() != 'Darwin' and system() != 'Windows':    
    nbatch_def = 50
    use_cp = True
    
elif system() == 'Windows':
    
    nbatch_def = 17
    use_cp = True
    
else:
    
    nbatch_def = 17
    use_cp = False

def v_iter_couple(setup,t,EV_tuple,nbatch=nbatch_def,verbose=False):
    
    if verbose: start = default_timer()
    
    agrid = setup.agrid_c
    sgrid = setup.sgrid_c
    ind, p = setup.s_ind_c, setup.s_p_c
    
    
    
    
    EV_by_l = EV_tuple[0]
    
    EV_fem_by_l = EV_tuple[1]
    EV_mal_by_l = EV_tuple[2]
    
    
    ls = setup.ls_levels
    us = setup.ls_utilities
    #pd = setup.ls_pdown
    nls = len(ls)
    
    
    # type conversion is here
    
    zf  = setup.exogrid.all_t[t][:,0]
    zm  = setup.exogrid.all_t[t][:,1]
    psi = setup.exogrid.all_t[t][:,2]
    beta = setup.pars['beta_t'][t]
    sigma = setup.pars['crra_power']
    R = setup.pars['R_t'][t]


    
    wf = np.exp(zf)
    wm = np.exp(zm)
    
    #labor_income = np.exp(zf) + np.exp(zm)
    
    #money = R*agrid[:,None] + wf[None,:] 
    
    
    nexo = setup.pars['nexo_t'][t]
    shp = (setup.na,nexo,setup.ntheta)
    
    # type conversion to keep everything float32
    sgrid,sigma,beta = (np.float32(x) for x in (sgrid,sigma,beta))
    
    V_couple, c_opt, s_opt, i_opt, il_opt = np.empty(shp,np.float32), np.empty(shp,np.float16), np.empty(shp,np.float32), np.empty(shp,np.int16), np.empty(shp,np.int8)
    
    
    V_all_l = np.empty(shp+(nls,),dtype=np.float32)
    
    theta_val = np.float32(setup.thetagrid)
    umult_vec = setup.u_mult(theta_val)
    
    # the original problem is max{umult*u(c) + beta*EV}
    # we need to rescale the problem to max{u(c) + beta*EV_resc}
    
    istart = 0
    ifinish = nbatch if nbatch < nexo else nexo
    
    # this natually splits everything onto slices
    
    for ibatch in range(int(np.ceil(nexo/nbatch))):
        #money_i = money[:,istart:ifinish]
        assert ifinish > istart
        
        money_t = (R*agrid, wf[istart:ifinish], wm[istart:ifinish])
        EV_t = (ind,p,EV_by_l[:,istart:ifinish,...])
        
        V_pure_i, c_opt_i, s_opt_i, i_opt_i, il_opt_i, V_all_l_i = \
           v_optimize_couple(money_t,sgrid,umult_vec,EV_t,sigma,beta,ls,us)
        V_ret_i = V_pure_i + psi[None,istart:ifinish,None]
        
        
        V_couple[:,istart:ifinish,:] = V_ret_i
        c_opt[:,istart:ifinish,:] = c_opt_i
        s_opt[:,istart:ifinish,:] = s_opt_i
        i_opt[:,istart:ifinish,:] = i_opt_i
        il_opt[:,istart:ifinish,:] = il_opt_i
        V_all_l[:,istart:ifinish,...] = V_all_l_i
        
        
        istart = ifinish
        ifinish = ifinish+nbatch if ifinish+nbatch < nexo else nexo
        
        if verbose: print('Batch {} done at {} sec'.format(ibatch,default_timer()-start))
    
    
    assert np.all(c_opt > 0)
    
    psi_r = psi[None,:,None].astype(np.float32)
    
    # finally obtain value functions of partners
    uf, um = setup.u_part(c_opt,theta_val[None,None,:])
    EVf_all, EVm_all, EV_all  = (get_EVM(ind,p,x) for x in (EV_fem_by_l, EV_mal_by_l,EV_by_l))
    V_fem = uf + psi_r + beta*np.take_along_axis(np.take_along_axis(EVf_all,i_opt[...,None],0),il_opt[...,None],3).squeeze(axis=3)
    V_mal = um + psi_r + beta*np.take_along_axis(np.take_along_axis(EVm_all,i_opt[...,None],0),il_opt[...,None],3).squeeze(axis=3)
    
    #TODO check below for monotonicity: it is driven by uf!!
#    psi_broadcast = np.broadcast_to(psi_r,V_fem.shape)
#    d_psi = np.diff(psi_broadcast,axis=1)
#    d_Vfem = np.diff(V_fem,axis=1)
#    npsi = setup.pars['n_psi']
#    nexo = setup.pars['nexo']
#    for i in range(round(nexo)):
#        for j in range(len(agrid)):
#            for h in range(len(setup.thetagrid)):
#       
#                if not np.all(np.diff(V_couple[j,(i*npsi):(npsi+i*npsi),h],axis=0)>0):
#                    print('Time utility of Female is {}'.format(uf[j,(i*npsi):(npsi+i*npsi),h]+psi_r[j,(i*npsi):(npsi+i*npsi),h]))
#                    print('Couple consumption is {}'.format(c_opt[j,(i*npsi):(npsi+i*npsi),h]))
#                    print('Female Expected Value is {}'.format(np.take_along_axis(EVf_all,i_opt,0)[j,(i*npsi):(npsi+i*npsi),h]))
#                    print('Male expected value is {}'.format(np.take_along_axis(EVm_all,i_opt,0)[j,(i*npsi):(npsi+i*npsi),h]))
#                    print('Couple value is {}'.format(V_couple[j,(i*npsi):(npsi+i*npsi),h]))
#                    assert np.all(np.diff(V_couple[j,(i*npsi):(npsi+i*npsi),h],axis=0)>0)
                    
                    
    
    # consistency check
    #uc = setup.u_couple(c_opt,theta_val[None,None,:])
    #V_all = uc + psi_r + beta*np.take_along_axis(np.take_along_axis(EV_all,i_opt[...,None],0),il_opt[...,None],3).squeeze(axis=3)
    
    #assert np.allclose(V_all,V_couple,atol=1e-5)
    
    
    
    
    #out = {'V':V_couple,'VF':V_fem,'VM':V_mal,'c':c_opt, 's':s_opt}
    def r(x): return x.astype(np.float32)
    
    return r(V_couple), r(V_fem), r(V_mal), r(c_opt), r(s_opt), il_opt, r(V_all_l)





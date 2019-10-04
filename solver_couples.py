#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is solver for those who are couples at period 0
"""
import numpy as np
from timeit import default_timer


from optimizers import build_s_grid, sgrid_on_agrid, get_EVM
from optimizers import v_optimize

from platform import system

if system() != 'Darwin':    
    nbatch_def = 200
    use_cp = True
else:
    nbatch_def = 1
    use_cp = False


#@jit(nopython=True)
def vm_period_zero_grid_massive(setup,a0,EV_tuple,nbatch=nbatch_def,verbose=False):
    
    if verbose: start = default_timer()
    
    agrid = setup.agrid
    sgrid = build_s_grid(agrid,10,0.001,0.1)
    ind, p = sgrid_on_agrid(sgrid,agrid)
    
    EV = EV_tuple[0]
    
    EV_fem = EV_tuple[1]
    EV_mal = EV_tuple[2]
    
    
    zf  = setup.exogrid.all_t[0][:,0]
    zm  = setup.exogrid.all_t[0][:,1]
    psi = setup.exogrid.all_t[0][:,2]
    beta = setup.pars['beta']
    sigma = setup.pars['crra_power']

    labor_income = np.exp(zf) + np.exp(zm)
    
    money = a0[:,None] + labor_income[None,:]
    
    shp = (setup.na,setup.nexo,setup.ntheta)
    
    # type conversion to keep everything float32
    money,sgrid,EV,sigma,beta = (np.float32(x) for x in (money,sgrid,EV,sigma,beta))
    
    V_couple, c_opt, s_opt, i_opt = np.empty(shp), np.empty(shp), np.empty(shp), np.empty(shp,np.int32)
    
    
    theta_val = setup.thetagrid[None,None,:]
    umult_vec = setup.u_mult(theta_val)
    
    #MMEV = (1/umult_vec[None,None,:])*get_EVM(ind,p,EV)
    # this is required 
    
    EV_resc = (1/umult_vec)*EV
    
    if verbose: print('MMEV computed after {} sec'.format(default_timer()-start))
    
    istart = 0
    ifinish = nbatch if nbatch < setup.nexo else setup.nexo
    
    # this natually splits everything onto slices
    
    for ibatch in range(int(np.floor(setup.nexo/nbatch))):
        #money_i = money[:,istart:ifinish]
        
        money_t = (a0,labor_income[istart:ifinish])
        EV_t = (ind,p,EV_resc[:,istart:ifinish,:])
        
        #MMEV_i = MMEV[:,istart:ifinish]
        #V_pure_i, c_opt_i, s_opt_i = v_optimizeM(money_i,sgrid,MMEV_i,sigma,beta)
        V_pure_i, c_opt_i, s_opt_i, i_opt_i = v_optimize(money_t,sgrid,EV_t,sigma,beta,return_ind=True)
        V_ret_i = umult_vec[None,None,:]*V_pure_i + psi[None,istart:ifinish,None]
        
        
        if use_cp:
            V_pure_i0, c_opt_i0, s_opt_i0, i_opt_i0 = v_optimize(money_t,sgrid,EV_t,sigma,beta,return_ind=True,use_cp=False)
            print('Max diff V: {}'.format(np.max(np.abs(V_pure_i0-V_pure_i))))
            print('Max diff c: {}'.format(np.max(np.abs(c_opt_i0-c_opt_i))))
            print('Max diff s: {}'.format(np.max(np.abs(s_opt_i0-s_opt_i))))
            print('Max diff i: {}'.format(np.max(np.abs(i_opt_i0-i_opt_i))))
            
        
        V_couple[:,istart:ifinish,:] = V_ret_i
        c_opt[:,istart:ifinish,:] = c_opt_i
        s_opt[:,istart:ifinish,:] = s_opt_i
        i_opt[:,istart:ifinish,:] = i_opt_i
        
        istart = ifinish
        ifinish = ifinish+nbatch if ifinish+nbatch < setup.nexo else setup.nexo
        
        if verbose: print('Batch {} done at {} sec'.format(ibatch,default_timer()-start))
    
    
    
    
    # finally obtain value functions of partners
    uf, um = setup.u_part(c_opt,theta_val)
    EVf_all, EVm_all = (get_EVM(ind,p,x) for x in (EV_fem, EV_mal))
    V_fem = uf# + beta*np.take_along_axis(EVf_all,i_opt,0)
    V_mal = um# + beta*np.take_along_axis(EVm_all,i_opt,0)
    
    V_out = {'V':V_couple,'VF':V_fem,'VM':V_mal}
    
    return V_out, c_opt, s_opt


# this is equivalent to the above function with nbatch = 1
'''
def vm_period_zero_grid_loop(setup,a0,EV):
    
    
    if system() != 'Darwin':
        from opt_test import v_optimize_MEV_cp as v_optimize
    else:
        from opt_test import v_optimize_MEV_np as v_optimize
    
    
    agrid = setup.agrid
    sgrid = build_s_grid(agrid,10,0.001,0.1)
    ind, p = sgrid_on_agrid(sgrid,agrid)
    
    
    zf  = setup.exogrid.all_t[0][:,0]
    zm  = setup.exogrid.all_t[0][:,1]
    psi = setup.exogrid.all_t[0][:,2]
    beta = setup.pars['beta']
    sigma = setup.pars['crra_power']

    
    money = a0[:,None] + np.exp(zf[None,:]) + np.exp(zm[None,:])
    
    shp = (setup.na,setup.nexo,setup.ntheta)
    
    money,sgrid,EV,sigma,beta = (np.float32(x) for x in (money,sgrid,EV,sigma,beta))
    
    V_ret, c_opt, s_opt = np.empty(shp), np.empty(shp), np.empty(shp)
    
    umult_vec = setup.u_mult(setup.thetagrid)
    
    for iexo in range(setup.nexo):
        mi = money[:,iexo]
        uadd = psi[iexo]       
        
        MEV = (1/umult_vec[None,:])*get_EVM(ind,p,EV[:,iexo,:])        
        
        q = v_optimizeM(mi,sgrid,MEV,sigma,beta)
        #q = v_optimize(mi,sgrid,MEV,sigma,beta)
        
        
                
        V_ret[:,iexo,:] = umult_vec[None,:]*q[0] + uadd
        c_opt[:,iexo,:], s_opt[:,iexo,:] = q[1:]
    
           
    return V_ret, c_opt, s_opt
'''
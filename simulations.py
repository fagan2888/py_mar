#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This contains things relevant for simulations
"""

import numpy as np


from mc_tools import mc_simulate
from gridvec import VecOnGrid

class Agents:
    
    
    def __init__(self,M,N=15000,T=None,verbose=True):
        if T is None:
            T = M.setup.pars['T']
            
            
        np.random.seed(18) # TODO: this should be replaced by explicitly supplying shocks  
            
        # take the stuff from the model and arguments
        # note that this does not induce any copying just creates links
        self.M = M
        self.V = M.V
        self.setup = M.setup
        self.state_names = self.setup.state_names
        self.N = N
        self.T = T
        self.verbose = verbose
        self.timer = M.time
        
        
        # initialize assets
        
        self.iassets = np.zeros((N,T),np.int32)
        

        # initialize theta
        self.itheta = -np.ones((N,T),np.int32)
        
        # initialize iexo
        self.iexo = np.zeros((N,T),np.int32)
        self.iexo[:,0] = np.random.randint(0,self.setup.pars['n_zf'],size=N) # initialize iexo
        
        # initialize state
        self.state = np.zeros((N,T),dtype=np.int32)       
        self.state[:,0] = 0  # everyone starts as female
        
        self.state_codes = dict()
        self.has_theta = list()
        for i, name in enumerate(self.setup.state_names):
            self.state_codes[name] = i
            self.has_theta.append((name=='Couple, C' or name=='Couple, M'))
        
        
        self.timer('Simulations, creation')
    
    def simulate(self):
        
        #Create Variables that stores varibles of interest
        
        
        for t in range(self.T-1):
         
            self.anext(t) 
            self.iexonext(t)            
            self.statenext(t)
            self.timer('Simulations, iteration')
        
        
        #return self.gsavings, self.iexo, self.state,self.gtheta
    
    
    def anext(self,t):
        # finds savings (potenitally off-grid)
        
        for ist, sname in enumerate(self.state_codes):
            
            is_state = (self.state[:,t]==ist)            
            use_theta = self.has_theta[ist]            
            nst = np.sum(is_state)
            
            if nst==0:
                continue
            
            ind = np.where(is_state)[0]
            
            if not use_theta:
                
                # apply for singles
                anext = self.V[t][sname]['s'][self.iassets[ind,t],self.iexo[ind,t]]
                
            else:
                
                # interpolate in both assets and theta
                # function apply_2dim is experimental but I checked it at this setup
                
                # apply for couples
                
                tk = lambda x : self.setup.v_thetagrid_fine.apply(x,axis=2)
                
                anext = tk(self.V[t][sname]['s'])[self.iassets[ind,t],self.iexo[ind,t],self.itheta[ind,t]]
                
                
            assert np.all(anext >= 0)
            
            agrid = self.setup.agrid_c if use_theta else self.setup.agrid_s
            
            self.iassets[ind,t+1] = VecOnGrid(agrid,anext).roll(shocks=None) # TODO: add shocks
            
      
            
            
      
            
            
            
    def iexonext(self,t):
        
        # let's find out new exogenous state
        
        for ist,sname in enumerate(self.state_names):
            is_state = (self.state[:,t]==ist)
            nst = np.sum(is_state)
            
            if nst == 0:
                continue
            
            ind = np.where(is_state)[0]
            sname = self.state_names[ist]
            
            mat = self.setup.exo_mats[sname][t]
            
            iexo_now = self.iexo[ind,t].reshape(nst)
            
            iexo_next = mc_simulate(iexo_now,mat,shocks=None) # import + add shocks     
            self.iexo[ind,t+1] = iexo_next
            
            assert np.all(iexo_next<self.setup.pars['nexo'])
            
    def statenext(self,t):
        
        setup = self.setup
        
        for ist,sname in enumerate(self.state_names):
            is_state = (self.state[:,t]==ist)
            
            if self.verbose: print('At t = {} count of {} is {}'.format(t,sname,np.sum(is_state)))
            
            if not np.any(is_state):
                continue
            
            ind = np.where(is_state)[0]
            
            nind = ind.size
            
            
            
            if sname == "Female, single":
                # TODO: this is temporary version, it computes partners for
                # everyone and after that imposes meet / no meet, this should
                # not happen.
                
                # meet a partner
                
                pmeet = self.setup.pars['pmeet']
                
                
                matches = self.M.decisions[t]['Female, single']
                
                
                ia = self.iassets[ind,t+1] # note that timing is slightly inconsistent                
                # we use iexo from t and savings from t+1
                # TODO: fix the seed
                iznow = self.iexo[ind,t]
                
                pmat = matches['p'][ia,iznow,:]
                pmat_cum = pmat.cumsum(axis=1)
                v = np.random.random_sample(ind.size) # draw uniform dist
                
                i_pmat = (v[:,None] > pmat_cum).sum(axis=1)  # index of the position in pmat
                
                ic_out = matches['iexo'][ia,iznow,i_pmat]
                ia_out = matches['ia'][ia,iznow,i_pmat]
                it_out = matches['theta'][ia,iznow,i_pmat]
                
                # potential assets position of couple
                
                iall, izf, izm, ipsi = setup.all_indices(ic_out)
                
                
                # compute for everyone
                
                
                
                i_nomeet =  np.array( np.random.rand(nind) > pmeet )
                
                
                
                i_pot_agree = matches['Decision'][ia,iznow,i_pmat]
                i_m_preferred = matches['M or C'][ia,iznow,i_pmat]
                
                i_disagree = (~i_pot_agree)
                i_disagree_or_nomeet = (i_disagree) | (i_nomeet)
                i_disagree_and_meet = (i_disagree) & ~(i_nomeet)
                
                i_agree = ~i_disagree_or_nomeet

                
                i_agree_mar = (i_agree) & (i_m_preferred)
                i_agree_coh = (i_agree) & (~i_m_preferred)
                
                assert np.all(~i_nomeet[i_agree])
                
                
                nmar, ncoh, ndis, nnom = np.sum(i_agree_mar),np.sum(i_agree_coh),np.sum(i_disagree_and_meet),np.sum(i_nomeet)
                ntot = sum((nmar, ncoh, ndis, nnom))
                
                print('{} mar, {} coh,  {} disagreed, {} did not meet ({} total)'.format(nmar,ncoh,ndis,nnom,ntot))
                #assert np.all(ismar==(i_agree )
                
                if np.any(i_agree_mar):
                    
                    self.itheta[ind[i_agree_mar],t+1] = it_out[i_agree_mar]
                    self.iexo[ind[i_agree_mar],t+1] = iall[i_agree_mar]
                    self.state[ind[i_agree_mar],t+1] = self.state_codes['Couple, M']
                    self.iassets[ind[i_agree_mar],t+1] = ia_out[i_agree_mar]
                    
                if np.any(i_agree_coh):
                    
                    self.itheta[ind[i_agree_coh],t+1] = it_out[i_agree_coh]
                    self.iexo[ind[i_agree_coh],t+1] = iall[i_agree_coh]
                    self.state[ind[i_agree_coh],t+1] = self.state_codes['Couple, C']
                    self.iassets[ind[i_agree_coh],t+1] = ia_out[i_agree_coh]
                    
                
                    
                if np.any(i_disagree_or_nomeet):
                    # do not touch assets
                    self.iexo[ind[i_disagree_or_nomeet],t+1] = izf[i_disagree_or_nomeet]
                    self.state[ind[i_disagree_or_nomeet],t+1] = self.state_codes['Female, single']
                    
            elif sname == "Couple, M" or sname == "Couple, C":
                
                decision = self.M.decisions[t][sname]
                
                
                # by default keep the same theta and weights
                
                self.itheta[ind,t+1] = self.itheta[ind,t]
                
                nt = self.setup.ntheta_fine
                
                
                # initiate renegotiation
                isc = self.iassets[ind,t+1]
                iall, izf, izm, ipsi = self.setup.all_indices(self.iexo[ind,t+1])
                
                itht = self.itheta[ind,t+1] 
                agrid =  self.setup.agrid_c                
                sc = agrid[isc] # needed only for dividing asssets               
                
                thts_all = decision['thetas']
                thts_orig_all = np.broadcast_to(np.arange(nt)[None,None,:],thts_all.shape)
                
                
                thts = thts_all[isc,iall,itht]
                thts_orig = thts_orig_all[isc,iall,itht]
                
                i_stay = decision['Decision'][isc,iall]

                
                
                i_div = ~i_stay                
                i_ren = (i_stay) & (thts_orig != thts)
                i_renf = (i_stay) & (thts_orig > thts)
                i_renm = (i_stay) & (thts_orig < thts)
                i_sq = (i_stay) & (thts_orig == thts)
                
                print('{} divorce, {} ren-f, {} ren-m, {} sq'.format(np.sum(i_div),np.sum(i_renf),np.sum(i_renm),np.sum(i_sq))                     )
                
                
                
                zf_grid = self.setup.exo_grids['Female, single'][t]
                zm_grid = self.setup.exo_grids['Male, single'][t]
                
                
                 
                
                if np.any(i_div):
                    
                    income_fem = np.exp(zf_grid[izf[i_div]])
                    income_mal = np.exp(zm_grid[izm[i_div]])
                    
                    income_share_fem = income_fem / (income_fem + income_mal)
                    
                    costs = self.setup.div_costs if sname == 'Couple, M' else self.setup.sep_costs
                               
                    share_f, share_m = costs.shares_if_split(income_share_fem)
                    
                    sf = share_f*sc[i_div]
                    
                    self.iassets[ind[i_div],t+1] = VecOnGrid(agrid,sf).roll() # FIXME: this is temporary solution till we find a better organization
                    self.itheta[ind[i_div],t+1] = -1
                    self.iexo[ind[i_div],t+1] = izf[i_div]
                    self.state[ind[i_div],t+1] = self.state_codes['Female, single']
                
                if np.any(i_ren):
                    
                    self.itheta[ind[i_ren],t+1] = thts[i_ren]
                    
                    #Distinguish between marriage and cohabitation
                    if sname == "Couple, M":
                        self.state[ind[i_ren],t+1] = self.state_codes[sname]
                    else:
                        i_coh = decision['Cohabitation preferred to Marriage'][isc,iall,thts]
                        i_coh1=i_coh[i_ren]
                        self.state[ind[i_ren],t+1] = i_coh1*self.state_codes["Couple, C"]+(1-i_coh1)*self.state_codes["Couple, M"]
                      
                            
                        
                    
                if np.any(i_sq):
                    self.state[ind[i_sq],t+1] = self.state_codes[sname]
                    # do not touch theta as already updated
                    
                    #Distinguish between marriage and cohabitation
                    if sname == "Couple, M":
                        self.state[ind[i_sq],t+1] = self.state_codes[sname]
                    else:
                        i_coh = decision['Cohabitation preferred to Marriage'][isc,iall,thts]
                        i_coh1=i_coh[i_sq]
                        self.state[ind[i_sq],t+1] = i_coh1*self.state_codes["Couple, C"]+(1-i_coh1)*self.state_codes["Couple, M"]
            
            else:
                raise Exception('unsupported state?')
        
        assert not np.any(np.isnan(self.state[:,t+1]))
                
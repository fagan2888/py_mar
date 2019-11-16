# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 10:26:49 2019

This file comupte simulated moments + optionally 
plots some graphs

@author: Fabio
"""

import numpy as np
import matplotlib.pyplot as plt 

def moment(setup,gassets,iexo,state,gtheta,draw=True):
#This function compute moments coming from the simulation
#Optionally it can also plot graphs about them. It is feeded with
#matrixes coming from simulations

    #As a first thing we unpack assets and theta
    assets_t=np.array([gassets[t].val for t in range(setup.pars['T'])]).T
    theta_t=np.array([gtheta[t].val for t in range(setup.pars['T'])]).T
    N=len(state)
    
    #Get states codes
    state_codes = {name: i for i, name in enumerate(setup.state_names)}
    
    ###########################################
    #Moments: Variables over Age
    ###########################################
    
    relt=np.zeros((len(state_codes),setup.pars['T']))
    ass_rel=np.zeros((len(state_codes),setup.pars['T']))
    inc_rel=np.zeros((len(state_codes),setup.pars['T']))
    
    for ist,sname in enumerate(state_codes):
        for t in range(setup.pars['T']):
            
            #Arrays for preparation
            is_state = (state[:,t]==ist)
            ind = np.where(is_state)[0]
            zf,zm,psi=setup.all_indices(iexo[ind,t])[1:4]
            
            #Relationship over time
            relt[ist,t]=np.sum(is_state)
            
            #Assets over time   
            ass_rel[ist,t]=np.mean(assets_t[ind,t])
            
            #Income over time
            if sname=="Female, single":
                inc_rel[ist,t]=np.mean(np.exp(setup.exogrid.zf_t[t][zf]))
                
            elif sname=="Male, single":
                 inc_rel[ist,t]=np.mean(np.exp(setup.exogrid.zf_t[t][zm]))
                
            elif sname=="Couple, C" or sname=="Couple, M":
                 inc_rel[ist,t]=np.mean(np.exp(setup.exogrid.zf_t[t][zf])+np.exp(setup.exogrid.zf_t[t][zm]))
    
            else:
            
               print('Error: No relationship chosen')
               
               
    ###########################################
    #Moments: Spells Creation
    ###########################################
    spells_type=list()
    spells_length=list()
    spells_end=list()
    
    for n in range(N):
        for ist,sname in enumerate(state_codes):
            for t in range(setup.pars['T']):
                
                if t==0:
                    leng=0
                 
                if (leng>=0) and (state[n,t]==ist): 
                    leng=leng+1
                
                if (leng>0 and state[n,t]!=ist) or (t==setup.pars['T']-1): 
                   
                    spells_type=[ist] + spells_type
                    spells_length=[leng] + spells_length
                    spells_end=[state[n,t]] + spells_end
                    leng=0
            
    spells_type.reverse()
    spells_length.reverse()
    spells_end.reverse()
    spells=np.array([np.array(spells_type),np.array(spells_length),np.array(spells_end)]).T
    
    #Now divide spells by relationship nature
    
    for ist,sname in enumerate(state_codes):
        s = sname.replace(',', '')
        s = s.replace(' ', '')
        
        
        is_state= (spells[:,0]==ist)
        ind = np.where(is_state)[0]
        globals()['spells_t'+s]=spells[ind,:]
        is_state= (globals()['spells_t'+s][:,1]!=0)
        ind = np.where(is_state)[0]
        globals()['spells_'+s]=globals()['spells_t'+s][ind,:]
    
    
    ##################################
    # Construct the Hazard functions
    #################################
        
    #Hazard of Divorce
    hazd=list()
    lgh=len(spells_CoupleM[:,0])
    for t in range(setup.pars['T']):
        
        cond=spells_CoupleM[:,1]==t+1
        temp=spells_CoupleM[cond,2]
        cond1=temp!=2
        temp1=temp[cond1]
        if lgh>0:
            haz1=len(temp1)/lgh
            lgh=lgh-len(temp)
        else:
            haz1=0.0
        hazd=[haz1]+hazd
        
    hazd.reverse()
    hazd=np.array(hazd).T 
    
    #Hazard of Separation
    hazs=list()
    lgh=len(spells_CoupleC[:,0])
    for t in range(setup.pars['T']):
        
        cond=spells_CoupleC[:,1]==t+1
        temp=spells_CoupleC[cond,2]
        cond1=temp==0
        temp1=temp[cond1]
        if lgh>0:
            haz1=len(temp1)/lgh
            lgh=lgh-len(temp)
        else:
            haz1=0.0
        hazs=[haz1]+hazs
        
    hazs.reverse()
    hazs=np.array(hazs).T
    
    #Hazard of Marriage (Cohabitation spells)
    hazm=list()
    lgh=len(spells_CoupleC[:,0])
    for t in range(setup.pars['T']):
        
        cond=spells_CoupleC[:,1]==t+1
        temp=spells_CoupleC[cond,2]
        cond1=temp==2
        temp1=temp[cond1]
        if lgh>0:
            haz1=len(temp1)/lgh
            lgh=lgh-len(temp)
        else:
            haz1=0.0
        hazm=[haz1]+hazm
        
    hazm.reverse()
    hazm=np.array(hazm).T
    
    #Singles: Marriage vs. cohabitation transition
    spells_s=np.append(spells_Femalesingle,spells_Malesingle,axis=0)
    cond=spells_s[:,2]>1
    spells_sc=spells_s[cond,2]
    condm=spells_sc==2
    sharem=len(spells_sc[condm])/max(len(spells_sc),0.0001)
    
    if draw:
    
        #Print something useful for debug and rest
        print('The share of singles choosing marriage is {0:.2f}'.format(sharem))
        cond=(state<2)
        print('The max level of assets for singles is {:.2f}, the grid upper bound is {:.2f}'.format(np.amax(assets_t[cond]),max(setup.agrids)))
        cond=(state>1)
        print('The max level of assets for couples is {:.2f}, the grid upper bound is {:.2f}'.format(np.amax(assets_t[cond]),max(setup.agrid)))
        
        #############################################
        # Hazard of Divorce, Separation and Marriage
        #############################################
        fig = plt.figure()
        f1=fig.add_subplot(2,1,1)
        
        plt.plot(np.array(range(setup.pars['T'])), hazd,markersize=6, label='Hazard of Divorce')
        plt.plot(np.array(range(setup.pars['T'])), hazs,markersize=6, label='Hazard of Separation')
        plt.plot(np.array(range(setup.pars['T'])), hazm,markersize=6, label='Hazard of Marriage')
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3),
                  fancybox=True, shadow=True, ncol=3, fontsize='x-small')
        #plt.legend(loc='upper left', shadow=True, fontsize='x-small')
        plt.xlabel('Duration')
        plt.ylabel('Hazard')
                   
        ##########################################
        # Assets Over the Live Cycle
        ########################################## 
        fig = plt.figure()
        f2=fig.add_subplot(2,1,1)
        
        for ist,sname in enumerate(state_codes):
            plt.plot(np.array(range(setup.pars['T'])), ass_rel[ist,],color=print(ist/len(state_codes)),markersize=6, label=sname)
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3),
                  fancybox=True, shadow=True, ncol=len(state_codes), fontsize='x-small')
        #plt.legend(loc='upper left', shadow=True, fontsize='x-small')
        plt.xlabel('Time')
        plt.ylabel('Assets')
        
        ##########################################
        # Income Over the Live Cycle
        ########################################## 
        fig = plt.figure()
        f3=fig.add_subplot(2,1,1)
        
        for ist,sname in enumerate(state_codes):
          
            plt.plot(np.array(range(setup.pars['T'])), inc_rel[ist,],color=print(ist/len(state_codes)),markersize=6, label=sname)
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3),
                  fancybox=True, shadow=True, ncol=len(state_codes), fontsize='x-small')
        plt.xlabel('Time')
        plt.ylabel('Income')
                
                
        ##########################################
        # Relationship Over the Live Cycle
        ##########################################       
        fig = plt.figure()
        f4=fig.add_subplot(2,1,1)
        for ist,sname in enumerate(state_codes):
            plt.plot([],[],color=print(ist/len(state_codes)), label=sname)
        plt.stackplot(np.array(range(setup.pars['T'])),relt[0,]/N,relt[1,]/N,relt[2,]/N,relt[3,]/N,
                      colors = ['b','y','g','r'])            
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3),
                  fancybox=True, shadow=True, ncol=len(state_codes), fontsize='x-small')
        plt.xlabel('Time')
        plt.ylabel('Share')

        
        
        
'''
Created on Nov 11, 2013

@author: ajn
'''

import numpy
import math
import matplotlib.pyplot as plt
import pyparticleest.models.mlnlg as mlnlg
import pyparticleest.paramest.paramest as param_est
import scipy.io
import scipy.linalg
import sys


def generate_dataset(length, Qz, R, Qes, Qeb):
    
    e_vec = numpy.zeros((1, length+1))
    z_vec = numpy.zeros((1, length+1))
    
    e = numpy.zeros((1,1))
    z = numpy.zeros((1,1))
    
    e_vec[:,0] = e.ravel()
    z_vec[:,0] = z.ravel()
    
    y = numpy.zeros((1, length))
    t = 0
    
    for i in range(1,length+1):
        a = 1 if (t % 2 == 0) else 0
        e = 0.1*a*e + (1-a)*z + numpy.random.multivariate_normal(numpy.zeros((1,)),a*Qes+(1-a)*Qeb)
        
        wz = numpy.random.multivariate_normal(numpy.zeros((1,)), Qz).ravel().reshape((-1,1))
        
        z = z + wz
        t = t + 1
        y[:,i-1] = (e**2 + (1-a)*z + numpy.random.multivariate_normal(numpy.zeros((1,)), R)).ravel()
        e_vec[:,i] = e.ravel()
        z_vec[:,i] = z.ravel()
    
    return (y.T.tolist(), e_vec, z_vec)    

class ParticleAPFTest(mlnlg.MixedNLGaussianInitialGaussian):
    """ Model 60 & 61 from Lindsten & Schon (2011) """
    def __init__(self, Qz, R, Qes, Qeb):
        """ Define all model variables """
        
        # No uncertainty in initial state
        xi0 = numpy.array([[0.0],])
        z0 =  numpy.array([[0.0],])
        P0 = 1.0*numpy.eye(1)
        
        Az = numpy.eye(1)
        
        self.Qes = numpy.copy(Qes)
        self.Qeb = numpy.copy(Qeb)

        super(ParticleAPFTest,self).__init__(xi0=xi0, z0=z0, Pz0=P0,R=R, Qz=Qz, Az=Az)
   
    def get_nonlin_pred_dynamics(self, particles, u, t):
        tmp = numpy.vstack(particles)[:,numpy.newaxis,:]
        a = 1 if (t % 2 == 0) else 0
        xi = tmp[:,:,0]
        Axi = numpy.reshape((1.0-a,), (1,1,1))
        Axi = numpy.repeat(Axi, len(particles), axis=0)
        fxi = 0.1*a*xi[:,numpy.newaxis,:]
        Qxi = numpy.repeat((a*self.Qes+(1-a)*self.Qeb)[numpy.newaxis], len(particles),axis=0)
        return (Axi, fxi, Qxi)
    
    def get_lin_pred_dynamics(self, particles, u, t):
#         a = 1 if (t % 2 == 0) else 0
#         Az = (1-a)*numpy.ones((len(particles),1,1))
#         fz = math.cos(t)*numpy.eye(1)
#         fz = numpy.repeat(fz[numpy.newaxis], len(particles), axis=0)
        return (None, None, None)
    
    def get_meas_dynamics(self, particles, y, t):
        if (y == None):
            return (y, None, None, None)
    
        N = len(particles)    
        tmp = numpy.vstack(particles)
        h = tmp[:,0]**2
        h = h[:,numpy.newaxis,numpy.newaxis]
        
        a = 1 if (t % 2 == 0) else 0
        C = a*numpy.ones((N, 1, 1))
        
        return (numpy.asarray(y).reshape((-1,1)), C, h, None)

# class ParticleLSB_EKF(ParticleLSB):
# 
#     def calc_Sigma_xi(self, particles, u, t): 
#         """ Return sampled process noise for the non-linear states """
#         (Axi, _fxi, Qxi, _, _, _) = self.get_nonlin_pred_dynamics_int(particles=particles, u=u, t=t)
#         (_xil, _zl, Pl) = self.get_states(particles)
#         N = len(particles)
#                     
#         Sigma = numpy.zeros((N, self.lxi, self.lxi))
#         for i in xrange(N):
#             Sigma[i] = Qxi[i] + Axi[i].dot(Pl[i]).dot(Axi[i].T)
# 
#         return Sigma
# 
#     def eval_1st_stage_weights(self, particles, u, y, t):
#         N = len(particles)
#         part = numpy.copy(particles)
#         xin = self.pred_xi(part, u, t)
#         Sigma = self.calc_Sigma_xi(particles, u, t)
#         self.cond_predict(part, xin, u, t)
#         
#         tmp = numpy.vstack(part)
#         h = 0.05*tmp[:,0]**2
#         h_grad = 0.1*tmp[:,0]
#         
#         tmp = (h_grad**2)
#         Rext = self.kf.R + Sigma*tmp[:,numpy.newaxis, numpy.newaxis]
#         logRext = numpy.log(Rext)
#         diff = y - h
#         
#         lyz = numpy.empty(N)
#         l2pi = math.log(2*math.pi)
#         for i in xrange(N):
#             lyz[i] = -0.5*(l2pi + logRext[i,0,0] + (diff[i].ravel()**2)/Rext[i,0,0])
#         return lyz
# 
# class ParticleLSB_UKF(ParticleLSB):
# 
#     def eval_1st_stage_weights(self, particles, u, y, t):
#         N = len(particles)
#         #xin = self.pred_xi(part, u, t)
# 
#         (Axi, fxi, _, _, _, _) = self.get_nonlin_pred_dynamics_int(particles=particles, u=u, t=t)
#         (_xil, zl, Pl) = self.get_states(particles)
# 
#         Rext = numpy.empty(N)
#         diff = numpy.empty(N)
# 
#         for i in xrange(N):
#             m = numpy.vstack((zl[i], numpy.zeros((6,1))))
#             K = scipy.linalg.block_diag(Pl[i], self.Qxi, self.kf.Q, self.kf.R)
#             Na = len(K)
#             (U,s,_V) = numpy.linalg.svd(Na*K)
#             Kroot = U.dot(numpy.diag(numpy.sqrt(s)))
# 
#             ypred = numpy.empty(2*Na)
#             # Some ugly hard-coding here of the function f and g
#             # g = 0.05*xi**2
#             for j in xrange(Na):
#                 val = m + Kroot[:,j:j+1]
#                 xin = fxi[i]+Axi[i].dot(val[:4])+val[4]
#                 ypred[j] = 0.05*(xin)**2+val[9]
# 
#                 val = m - Kroot[:,j:j+1]
#                 xin = fxi[i]+Axi[i].dot(val[:4])+val[4]
#                 ypred[Na+j] = 0.05*(xin)**2+val[9]
# 
#             # Construct estimate of covariance for predicted measurement
#             Rext[i] = numpy.cov(ypred)
#             diff[i] = y - numpy.mean(ypred)
# 
#         logRext = numpy.log(Rext)
# 
#         lyz = numpy.empty(N)
#         l2pi = math.log(2*math.pi)
#         for i in xrange(N):
#             lyz[i] = -0.5*(l2pi + logRext[i] + (diff[i].ravel()**2)/Rext[i])
#         return lyz

def wmean(logw, val):
    w = numpy.exp(logw)
    w = w / sum(w)
    return numpy.sum(w*val.ravel())

if __name__ == '__main__':
    
    num = 200
    nums = 10
        
    # How many steps forward in time should our simulation run
    steps = 40
    
    Qes = 0.1*numpy.eye(1)
    Qeb = 0.1*numpy.eye(1)
    R = 0.1*numpy.eye(1)
    Qz = 0.1*numpy.eye(1)
    
    
    if (len(sys.argv) > 1):
        if (sys.argv[1] == 'apf_compare'):
            
            mode = sys.argv[2]
            
            print "Running tests for %s" % mode
            
            sims = 100
            part_count = (5, 10, 15, 20, 25, 30, 50, 75, 100, 150, 200, 300, 500)
            rmse_eta = numpy.zeros((sims, len(part_count)))
            rmse_theta = numpy.zeros((sims, len(part_count)))
            filt = 'PF'
            model=ParticleLSB()
            if (mode.lower() == 'epf'):
                model = ParticleLSB_EKF()
                filt = 'APF'
            elif (mode.lower() == 'upf'):
                model = ParticleLSB_UKF()
                filt = 'APF'
            elif (mode.lower() == 'apf'):
                filt = 'APF'
            else:
                pass
            
            for k in range(sims):
                
                # Create reference
                numpy.random.seed(k)
                (y, e, z) = generate_dataset(steps)
                pe = param_est.ParamEstimation(model=model, u=None, y=y)
                    
                for ind, pc in enumerate(part_count):
                
                    pe.simulate(pc, num_traj=1, res=0.67, filter=filt, smoother='ancestor')
                    avg = numpy.zeros((2, steps+1))

                    for i in range(steps+1):
                        avg[0,i] = wmean(pe.pt.traj[i].pa.w, numpy.vstack(pe.pt.traj[i].pa.part)[:,0])
                        zest = numpy.vstack(pe.pt.traj[i].pa.part)[:,1:5].T
                        thetaest = 25.0+C_theta.dot(zest)
                        avg[1,i] = wmean(pe.pt.traj[i].pa.w, thetaest)
                        
                    theta = 25.0+C_theta.dot(z.reshape((4,-1)))
                    sqr_err_eta = (avg[0,:] - e[0,:])**2
                    sqr_err_theta = (avg[1,:] - theta)**2
                            
                    rmse_eta[k, ind] = numpy.sqrt(numpy.mean(sqr_err_eta))
                    rmse_theta[k, ind] = numpy.sqrt(numpy.mean(sqr_err_theta))
                    
            for ind, pc in enumerate(part_count):
                print "%d: (%f, %f)" % (pc, numpy.mean(rmse_eta[:,ind]), numpy.mean(rmse_theta[:,ind]))
                
            
    else:
    

    
        # Create arrays for storing some values for later plotting    
        vals = numpy.zeros((2, num+1, steps+1))
    
        plt.ion()

        # Create reference
        numpy.random.seed(1)
        #numpy.random.seed(86)
        (y, e, z) = generate_dataset(steps, Qz=Qz, R=R, Qes=Qes, Qeb=Qeb)
        # Store values for last time-step aswell    
    
        
        x = numpy.asarray(range(steps+1))
        model = ParticleAPFTest(Qz=Qz, R=R, Qes=Qes, Qeb=Qeb)
        # Create an array for our particles 
        ParamEstimator = param_est.ParamEstimation(model=model, u=None, y=y)
        ParamEstimator.simulate(num, nums, res=0.67, filter='PF', smoother='ancestor')

        
        svals = numpy.zeros((2, nums, steps+1))
        vals = numpy.zeros((2, num, steps+1))
        vals_mean = numpy.zeros((2, steps+1))
        for i in range(steps+1):
            (xil, zl, Pl) = model.get_states(ParamEstimator.straj.straj[i])
            svals[0,:,i] = numpy.vstack(xil).ravel()
            svals[1,:,i] = numpy.hstack(zl).ravel()
            (xil, zl, Pl) = model.get_states(ParamEstimator.pt.traj[i].pa.part)
            vals[0,:,i]=numpy.vstack(xil).ravel()
            vals[1,:,i]=numpy.hstack(zl).ravel()
            vals_mean[0, i] = wmean(ParamEstimator.pt.traj[i].pa.w, vals[0,:,i])
            vals_mean[1, i] = wmean(ParamEstimator.pt.traj[i].pa.w, vals[1,:,i])
            
        svals_mean = numpy.mean(svals,1)
        plt.figure()

        for j in range(num):   
            plt.plot(range(steps+1),vals[0,j,:],'.', markersize=1.0, color='#000000')
        for j in range(nums):
            plt.plot(range(steps+1),svals[0,j,:],'--', markersize=2.0, color='#FF0000')
        plt.plot(range(steps+1),svals_mean[0,:],'--', markersize=1.0, color='#00FF00')
        plt.plot(range(steps+1),vals_mean[0,:],'--', markersize=1.0, color='#0000FF')
        plt.plot(x, e.T,'k--',markersize=1.0)
        plt.show()
        
        plt.figure()
        for j in range(num):   
            plt.plot(range(steps+1),vals[1,j,:],'.', markersize=1.0, color='#000000')
#         for j in range(nums):
#             plt.plot(range(steps+1),svals[1,j,:],'--', markersize=2.0, color='#FF0000')
#         plt.plot(range(steps+1),svals_mean[1,:],'-', markersize=1.0, color='#00FF00')
        plt.plot(range(steps+1),vals_mean[1,:],'--', markersize=1.0, color='#0000FF')
        plt.plot(x, z.ravel(),'k--',markersize=1.0)
        plt.show()

        plt.draw()
        
        plt.ioff()
        plt.show()
        plt.draw()
    print "exit"
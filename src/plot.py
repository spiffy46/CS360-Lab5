import optparse
import sys
import os

import matplotlib
matplotlib.use('Agg')
from pylab import *

# Class that parses a file and plots several graphs
class Plotter:
    def __init__(self):
        self.files = [f for f in os.listdir('.') if os.path.isfile(f)]
	pass

    def parse(self,fileheader):
        """ Parse the data file and accumulate values for plots. 
        """
	if fileheader == 'web-lightserver':
		self.servicerate = 1094.0
	else:
		self.servicerate = 1203.0
        # Initialize plotter variables.
        self.data = {}
	self.sizes = {}
		# open file
	for File in self.files:
		if fileheader not in File:
		    continue
	    	f = open(File)
		for line in f.readlines():
				# skip lines starting with a comment character
	            if line.startswith("#"):
	                continue
				# try parsing the line
	            try:
	                sessionid,url,status,resp,size,seconds = line.split()
	            except:
		        continue
				# convert to proper data types
		    status = int(status)
 	            size = int(size)
	            seconds = float(seconds)
		    load = float(File.split('-')[2].split('.')[0])
		    utilization = load/self.servicerate
	            utilization = round(utilization,1)
				# add to dictionary
	       	    if utilization not in self.data:
	       	        self.data[utilization] = []
	            self.data[utilization].append(seconds)

    def plot(self,name):
		clf()
		# plot download times
		x = []
		keys = []
		# collect data into a list of lists
		for threads in sorted(self.data.keys()):
			x.append(self.data[threads])
			keys.append(threads)
		# plot all the lists as a boxplot
		theoreticalx = np.arange(0.01,0.99,0.01)
		plot(theoreticalx, 1/(self.servicerate-(theoreticalx*self.servicerate)))	
		boxplot(x,sym='',positions=keys)
		title(name)
		xlabel('Utilization (p)')
		ylabel('Response Time')
		xlim([0,1])
		savefig('response-time-%s.png' % name)

if __name__ == '__main__':
    p = Plotter()
    p.parse('web-lightserver')
    p.plot('lightserver')
    p.parse('web-myserver')
    p.plot('myserver')


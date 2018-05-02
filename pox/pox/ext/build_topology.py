import os
import sys
import networkx
import pdb
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.node import Controller
from mininet.node import RemoteController
from mininet.cli import CLI
sys.path.append("../../")
from pox.ext.jelly_pox import JELLYPOX
from subprocess import Popen
from time import sleep, time
from YenKSP.algorithms import ksp_yen
from YenKSP.graph import DiGraph

class JellyFishTop(Topo):
    def build(self):

            leftHost = self.addHost( 'h1' )
            rightHost = self.addHost( 'h2' )
            leftSwitch = self.addSwitch( 's3' )
            rightSwitch = self.addSwitch( 's4' )

            # Add links
            self.addLink( leftHost, leftSwitch )
            self.addLink( leftSwitch, rightSwitch )
            self.addLink( rightSwitch, rightHost )


def experiment(net):
        net.start()
        sleep(3)
        net.pingAll()
        net.stop()

def load_random_graph(file, n):
	graph = DiGraph()
	for i in range(n):
	    graph.add_node(str(i))
	with open(file) as f:
	    for line in f:
		if line.startswith("#"):
		    continue
		tokens = line.split()
		source_node = tokens[0]
		if int(source_node) >= n:
		    raise "Source node greater than max"
		for dest_node in tokens[1:]:
		    graph.add_edge(str(source_node), str(dest_node), 1)
		    graph.add_edge(str(dest_node), str(source_node), 1)
	return graph

def count_shortest_paths(digraph, n):
	counts = {}
	for a in range(n):
	    for b in range(a+1, n):
		ksp = ksp_yen(digraph, str(a), str(b), 64)
		minCost = ksp[0]['cost']
		for i in range(len(ksp)):
		    if i >= 8 and ksp[i]['cost'] > minCost:
			break
		    else:
			prev_node  = None
			for node in ksp[i]['path']:
			    if not prev_node:
				prev_node = node
				continue
			    else:
				link = (str(prev_node), str(node))
				rev_link = (str(node), str(prev_node))
				if link not in counts:
			            counts[link] = {"8-ksp": 0, "8-ecmp": 0, "64-ecmp": 0}
				if rev_link not in counts:
			            counts[rev_link] = {"8-ksp": 0, "8-ecmp": 0, "64-ecmp": 0}
				if ksp[i]['cost'] == minCost and i < 8:
				    counts[link]["8-ecmp"] += 1
				    counts[rev_link]["8-ecmp"] += 1
				if ksp[i]['cost'] == minCost:
				    counts[link]["64-ecmp"] += 1
				    counts[rev_link]["64-ecmp"] += 1
				if i < 8:
				    counts[link]["8-ksp"] += 1
				    counts[rev_link]["8-ksp"] += 1
				prev_node = node
	return counts
	

def assemble_histogram(counts):
	ksp_distinct_paths_counts = []
	ecmp_8_distinct_paths_counts = []
	ecmp_64_distinct_paths_counts = []
	

	for _, value in sorted(counts.iteritems(), key=lambda (k,v): (v["8-ksp"],k)):
	    ksp_distinct_paths_counts.append(value["8-ksp"])
	for _, value in sorted(counts.iteritems(), key=lambda (k,v): (v["8-ecmp"],k)):
	    ecmp_8_distinct_paths_counts.append(value["8-ecmp"])
	for _, value in sorted(counts.iteritems(), key=lambda (k,v): (v["64-ecmp"],k)):
	    ecmp_64_distinct_paths_counts.append(value["64-ecmp"])

	print ksp_distinct_paths_counts
	print ecmp_8_distinct_paths_counts
	print ecmp_64_distinct_paths_counts
	x = range(len(ksp_distinct_paths_counts))
	fig = plt.figure()
	ax1 = fig.add_subplot(111)

	ax1.scatter(x, ksp_distinct_paths_counts, c='b', marker='s', label="8-KSP")
	ax1.scatter(x, ecmp_8_distinct_paths_counts, c='r', marker='o', label="8-ECMP")
	ax1.scatter(x, ecmp_64_distinct_paths_counts, c='g', marker='x', label="64-ECMP")
	plt.legend(loc="upper left");
	plt.savefig("plot.png")
	    

def main():
	#topo = JellyFishTop()
	#net = Mininet(topo=topo, host=CPULimitedHost, link = TCLink, controller=JELLYPOX)
	#experiment(net)
	d = 12
	n = 50
	rrg = networkx.random_regular_graph(d, n)
	file_name = "rrg_large_" + str(d) + "_" + str(n)

	networkx.write_adjlist(rrg, file_name)
 	digraph = load_random_graph(file_name, n)
	shortest_path_counts = count_shortest_paths(digraph, n)
	assemble_histogram(shortest_path_counts)
	

if __name__ == "__main__":
	main()


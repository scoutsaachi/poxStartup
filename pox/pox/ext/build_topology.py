import os
import sys
import networkx
import pdb
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import pickle
from itertools import islice
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.util import dumpNodeConnections
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.node import Controller
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
sys.path.append("../../")
from pox.ext.jelly_pox import JELLYPOX
from subprocess import Popen
from time import sleep, time
from YenKSP.algorithms import ksp_yen
from YenKSP.graph import DiGraph

class JellyFishTop(Topo):
    # numSwitches
    # numHosts
    def build(self, n, adjlist_file):
	switches = []
	hosts = []
	for i in range(n):
	    hosts.append(self.addHost('h%s' % (i)))
	    switches.append(self.addSwitch('s%s' % (i)))
	    self.addLink(hosts[i], switches[i])

        with open(adjlist_file) as f:
	    for line in f:
		if line.startswith("#"):
		    continue
		tokens = line.split()
		source_node = tokens[0]
		for dest_node in tokens[1:]:
		    self.addLink(switches[int(source_node)], switches[int(dest_node)])

def simpleTest():
	topo = JellyFishTop(n=10, adjlist_file="rrg_small_3_10")
	net = Mininet(topo=topo, host=CPULimitedHost, link = TCLink, controller=JELLYPOX)
        net.start()
        sleep(3)
	print "Dumping host connections"
	dumpNodeConnections(net.hosts)
	dumpNodeConnections(net.switches)
	print "Testing network connectivity"
        net.pingAll()
        net.stop()

#def load_random_graph_into_digraph(file, n):
#	graph = DiGraph()
#	for i in range(n):
#	    graph.add_node(str(i))
#	with open(file) as f:
#	    for line in f:
#		if line.startswith("#"):
#		    continue
#		tokens = line.split()
#		source_node = tokens[0]
#		if int(source_node) >= n:
#		    raise "Source node greater than max"
#		for dest_node in tokens[1:]:
#		    graph.add_edge(str(source_node), str(dest_node), 1)
#		    graph.add_edge(str(dest_node), str(source_node), 1)
#	return graph
#
def compute_ecmp_paths(networkx_graph, n):
	ecmp_paths = {}
	for a in range(n):
	    for b in range(a+1, n):
		shortest_paths = networkx.all_shortest_paths(networkx_graph, source=str(a), target=str(b))
		ecmp_paths[(str(a), str(b))] = [p for p in shortest_paths]
	return ecmp_paths

def compute_k_shortest_paths(networkx_graph, n, k=8):
	all_ksp = {}
	for a in range(n):
	    for b in range(a+1, n):
		ksp = list(islice(networkx.shortest_simple_paths(networkx_graph, source=str(a), \
								target=str(b)), k))
		all_ksp[(str(a), str(b))] = ksp
	return all_ksp

#def compute_k_shortest_paths(digraph, n, k=8):
#	counts = {}
#	for a in range(n):
#	    for b in range(a+1, n):
#		ksp = ksp_yen(digraph, str(a), str(b), k)
#		minCost = ksp[0]['cost']
#		for i in range(len(ksp)):
#		    if i >= 8 and ksp[i]['cost'] > minCost:
#			break
#		    else:
#			prev_node  = None
#			for node in ksp[i]['path']:
#			    if not prev_node:
#				prev_node = node
#				continue
#			    else:
#				link = (str(prev_node), str(node))
#				rev_link = (str(node), str(prev_node))
#				if link not in counts:
#			            counts[link] = {"8-ksp": 0, "8-ecmp": 0, "64-ecmp": 0}
#				if rev_link not in counts:
#			            counts[rev_link] = {"8-ksp": 0, "8-ecmp": 0, "64-ecmp": 0}
#				if ksp[i]['cost'] == minCost and i < 8:
#				    counts[link]["8-ecmp"] += 1
#				    counts[rev_link]["8-ecmp"] += 1
#				if ksp[i]['cost'] == minCost:
#				    counts[link]["64-ecmp"] += 1
#				    counts[rev_link]["64-ecmp"] += 1
#				if i < 8:
#				    counts[link]["8-ksp"] += 1
#				    counts[rev_link]["8-ksp"] += 1
#				prev_node = node
#	return counts
#	
#
def get_ecmp_path_counts(ecmp_paths):
	counts = {}
	for _, value in ecmp_paths.iteritems():
	    if len(value) > 64:
		value = value[:64]
	    for i in range(len(value)):
		path = value[i]
		prev_node = None
		for node in path:
		    if not prev_node:
			prev_node = node
			continue
		    link = (str(prev_node), str(node))
		    rev_link = (str(node), str(prev_node))
		    if link not in counts:
			counts[link] = {"8-ecmp": 0, "64-ecmp": 0}
		    if rev_link not in counts:
			counts[rev_link] = {"8-ecmp": 0, "64-ecmp": 0}
		    if i < 8:
			counts[link]["8-ecmp"] += 1
		    counts[link]["64-ecmp"] += 1
		    prev_node = node
	return counts

def get_ksp_counts(all_ksp):
	counts = {}
        for _, value in all_ksp.iteritems():
            for path in value:
                prev_node = None
                for node in path:
                    if not prev_node:
                        prev_node = node
                        continue
                    link = (str(prev_node), str(node))
                    rev_link = (str(node), str(prev_node))
                    if link not in counts:
                        counts[link] = 0
                    if rev_link not in counts:
                        counts[rev_link] = 0
                    counts[link] += 1
                    prev_node = node
        return counts

def assemble_histogram(ecmp_path_counts, ksp_counts, file_name):
	ksp_distinct_paths_counts = []
	ecmp_8_distinct_paths_counts = []
	ecmp_64_distinct_paths_counts = []
	

	for _, value in sorted(ksp_counts.iteritems(), key=lambda (k,v): (v,k)):
	    ksp_distinct_paths_counts.append(value)
	for _, value in sorted(ecmp_path_counts.iteritems(), key=lambda (k,v): (v["8-ecmp"],k)):
	    ecmp_8_distinct_paths_counts.append(value["8-ecmp"])
	for _, value in sorted(ecmp_path_counts.iteritems(), key=lambda (k,v): (v["64-ecmp"],k)):
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
	plt.savefig("%s_plot.png" % file_name)
	    
def save_obj(obj, name):
    with open('pickle_obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, 0)

def load_obj(name ):
    with open('pickle_obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


def main():
	
	#topo = JellyFishTop()
	#net = Mininet(topo=topo, host=CPULimitedHost, link = TCLink, controller=JELLYPOX)
	#experiment(net)
	#d = 14
	#n = 245
	#rrg = networkx.random_regular_graph(d, n)
	#file_name = "rrg_large_" + str(d) + "_" + str(n)

	#networkx.write_adjlist(rrg, file_name)
	#print "Loading random graph into digraph"
 	#digraph = load_random_graph_into_digraph(file_name, n)
	#print "Running KSP"
	#shortest_path_counts = count_shortest_paths(digraph, n)
	#print "Making the plot"
	#assemble_histogram(shortest_path_counts)
	
#	setLogLevel("info")
#	simpleTest()
	reuse_old_result = True
	ecmp_paths = {}
	all_ksp = {}
	file_name = "rrg_small_3_10"
	if not reuse_old_result:
		graph = networkx.read_adjlist(file_name)
		print "ECMP paths"
		ecmp_paths = compute_ecmp_paths(graph, 10)
		pdb.set_trace()	
		save_obj(ecmp_paths, "ecmp_paths_%s" % (file_name))
		print "K shortest paths"
		all_ksp = compute_k_shortest_paths(graph, 10)
		save_obj(all_ksp, "ksp_%s" % (file_name))
	else:
		ecmp_paths = load_obj("ecmp_paths_%s" % (file_name))
		all_ksp = load_obj("ksp_%s" % (file_name))
	print "Assembling counts from paths"
	ecmp_path_counts = get_ecmp_path_counts(ecmp_paths)
	ksp_counts = get_ksp_counts(all_ksp)
	print "Making the plot"
	assemble_histogram(ecmp_path_counts=ecmp_path_counts, ksp_counts=ksp_counts, file_name=file_name)
	
if __name__ == "__main__":
	main()


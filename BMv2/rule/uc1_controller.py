import sys
import os
sys.path.append('/home/p4/p4-utils')
from p4utils.utils.sswitch_thrift_API import *
import math

# Use Case 1 Sampling Space Sizes (From FAT-INT Paper Section 5.3)
global q_space_1, hop_space_1, egress_space_1
q_space_1 = 5
hop_space_1 = 3
egress_space_1 = 1

class Controller(object):

###############################################################################################
##########                                 Ingress                                   ##########
###############################################################################################

    def __init__(self):
        # Initialize 10 switches for the 2-ary fat-tree 
        # (2 Core, 4 Aggregation, 4 Edge) added sequentially in Mininet
        # Indices: c1, c2 -> 0, 1 | a1..a4 -> 2, 3, 4, 5 | e1..e4 -> 6, 7, 8, 9
        self.switches = []
        for i in range(10):
            try:
                # Thrift ports start at 9090 by default in p4-utils
                self.switches.append(SimpleSwitchThriftAPI(9090 + i))
            except Exception as e:
                print(f"Failed to connect to switch on port {9090+i}: {e}")

    def set_source_node(self):
        # Edge switches 1 and 2 (e1=idx 6, e2=idx 7) act as ingress nodes for senders (h1-h4)
        ingress_indices = [6, 7] 
        for idx in ingress_indices:
            self.switches[idx].table_add("tb_set_source", "int_set_source", ['0x3'])
    
    def valid_space(self):
        ingress_indices = [6, 7]
        for idx in ingress_indices:
            # Changed from 0.4 probability to 1.0 (100%)
            self.switches[idx].table_add("tb_valid_space", 
                                        "valid_space", 
                                        ['1', '0->65535'], 
                                        ['0'])

    def set_switch_id(self):
        # Assign unique switch IDs (1 to 10) to all switches
        for i, sw in enumerate(self.switches):
            sw.table_add("tb_set_switch_id", "set_switch_id", ['4'], [str(i + 1)])
    
    def set_space(self):
        global q_space_1, hop_space_1, egress_space_1
        for sw in self.switches:
            sw.table_add("tb_set_space", 
                         "set_space", 
                         ['0'], 
                         [str(q_space_1), str(hop_space_1), str(egress_space_1)])

    def routing_table(self):
        # Map indices to easily readable variables
        c1, c2 = self.switches[0], self.switches[1]
        a1, a2, a3, a4 = self.switches[2], self.switches[3], self.switches[4], self.switches[5]
        e1, e2, e3, e4 = self.switches[6], self.switches[7], self.switches[8], self.switches[9]

        def add_bidirectional_route(switch, port_a, port_b):
            """Helper to add forwarding in both directions based on ingress port"""
            switch.table_add("tb_forward", "set_egress_port", [str(port_a)], [str(port_b)])
            switch.table_add("tb_forward", "set_egress_port", [str(port_b)], [str(port_a)])

        # ---------------------------------------------------------------------
        # Disjoint Ingress-Port Routing for 2-ary Fat-Tree
        # ---------------------------------------------------------------------
        
        # Path 1: h1 <-> h5  (Path: e1 <-> a1 <-> c1 <-> a3 <-> e3)
        add_bidirectional_route(e1, 3, 1) # h1(port 3) to a1(port 1)
        add_bidirectional_route(a1, 3, 1) # e1(port 3) to c1(port 1)
        add_bidirectional_route(c1, 1, 3) # a1(port 1) to a3(port 3)
        add_bidirectional_route(a3, 1, 3) # c1(port 1) to e3(port 3)
        add_bidirectional_route(e3, 1, 3) # a3(port 1) to h5(port 3)

        # Path 2: h2 <-> h6  (Path: e1 <-> a2 <-> c2 <-> a4 <-> e3)
        add_bidirectional_route(e1, 4, 2) # h2(port 4) to a2(port 2)
        add_bidirectional_route(a2, 3, 2) # e1(port 3) to c2(port 2)
        add_bidirectional_route(c2, 2, 4) # a2(port 2) to a4(port 4)
        add_bidirectional_route(a4, 2, 3) # c2(port 2) to e3(port 3)
        add_bidirectional_route(e3, 2, 4) # a4(port 2) to h6(port 4)

        # Path 3: h3 <-> h7  (Path: e2 <-> a1 <-> c2 <-> a3 <-> e4)
        add_bidirectional_route(e2, 3, 1) # h3(port 3) to a1(port 1)
        add_bidirectional_route(a1, 4, 2) # e2(port 4) to c2(port 2)
        add_bidirectional_route(c2, 1, 3) # a1(port 1) to a3(port 3)
        add_bidirectional_route(a3, 2, 4) # c2(port 2) to e4(port 4)
        add_bidirectional_route(e4, 1, 3) # a3(port 1) to h7(port 3)

        # Path 4: h4 <-> h8  (Path: e2 <-> a2 <-> c1 <-> a4 <-> e4)
        add_bidirectional_route(e2, 4, 2) # h4(port 4) to a2(port 2)
        add_bidirectional_route(a2, 4, 1) # e2(port 4) to c1(port 1)
        add_bidirectional_route(c1, 2, 4) # a2(port 2) to a4(port 4)
        add_bidirectional_route(a4, 1, 4) # c1(port 1) to e4(port 4)
        add_bidirectional_route(e4, 2, 4) # a4(port 2) to h8(port 4)

################################################################################################
##########                                  Egress                                    ##########
################################################################################################

    def set_param(self):
        global q_space_1, hop_space_1, egress_space_1
        
        # In a 5-hop topology, TTL goes from 63 down to 59. 
        for sw in self.switches:
            ttl = 63
            count = 0 
            
            while ttl >= 59: 
                sw.table_add("tb_set_param", 
                             "set_param",
                             [str(ttl), str(q_space_1), str(hop_space_1), str(egress_space_1)],
                             [str(count % q_space_1), str(count % hop_space_1), str(count % egress_space_1)])
                ttl -= 1
                count += 1
    
    def insert_int(self):
        global q_space_1, hop_space_1, egress_space_1
        
        for sw in self.switches:
            ttl = 63
            count = 0
            
            while ttl >= 59:
                # 1. Expand Space Rules
                sw.table_add("tb_insert_q", "set_q", 
                             [str(1), str(q_space_1), str(count % q_space_1), "0->65535"])
                sw.table_add("tb_insert_hop", "set_hop", 
                             [str(1), str(hop_space_1), str(count % hop_space_1), "0->65535"])
                sw.table_add("tb_insert_egress", "set_egress", 
                             [str(1), str(egress_space_1), str(count % egress_space_1), "0->65535"])
                
                # 2. Multi-slot Reservoir Sampling (MRS) Probabilistic Insertion Rules
                sw.table_add("tb_insert_q", f"index_q{int(count % q_space_1)}",
                             [str(0), str(q_space_1), str(count % q_space_1), 
                              "0->" + str(int((1/math.ceil((count+1)/q_space_1))*65535))])
                sw.table_add("tb_insert_hop", f"index_hop{int(count % hop_space_1)}",
                             [str(0), str(hop_space_1), str(count % hop_space_1), 
                              "0->" + str(int((1/math.ceil((count+1)/hop_space_1))*65535))])
                sw.table_add("tb_insert_egress", f"index_egress{int(count % egress_space_1)}",
                             [str(0), str(egress_space_1), str(count % egress_space_1), 
                              "0->" + str(int((1/math.ceil((count+1)/egress_space_1))*65535))])
                
                ttl -= 1
                count += 1

################################################################################################
##########                                    Main                                    ##########
################################################################################################

if __name__ == "__main__":
    controller = Controller()
   
    print("Setting source nodes...")
    controller.set_source_node()
    
    print("Setting routing tables...")
    controller.routing_table()
    
    print("Setting switch IDs...")
    controller.set_switch_id()
    
    print("Configuring valid spaces...")
    controller.valid_space()
    
    print("Setting FAT-INT spaces...")
    controller.set_space()
    
    print("Setting Multi-slot Reservoir Sampling parameters...")
    controller.set_param()
    
    print("Populating INT insertion rules...")
    controller.insert_int()
    
    print("Controller configuration complete!")
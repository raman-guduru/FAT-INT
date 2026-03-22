import sys
import os
sys.path.append('/home/p4/p4-utils')
from p4utils.utils.sswitch_thrift_API import *
import math

# Use Case 2 Sampling Space Sizes (From FAT-INT Paper Figure 19(d) at 2% Error)
global q_space, hop_space, egress_space
q_space = 7
hop_space = 19
egress_space = 1

class Controller(object):

    def __init__(self):
        # 20 switches for 4-ary fat-tree 
        # c1-c4 (0-3), a1-a8 (4-11), e1-e8 (12-19)
        self.switches = []
        for i in range(20):
            try:
                self.switches.append(SimpleSwitchThriftAPI(9090 + i))
            except Exception as e:
                pass

    def set_source_node(self):
        # h1 connects to e1 (Index 12)
        self.switches[12].table_add("tb_set_source", "int_set_source", ['0x3'])
    
    def valid_space(self):
        # Sampling ratio for UC2 at 2% error is ~38% (Figure 19(b))
        self.switches[12].table_add("tb_valid_space", 
                                     "valid_space", 
                                     ['1', f'0->{math.ceil(65535*0.38)}'], 
                                     ['0'])

    def set_switch_id(self):
        for i, sw in enumerate(self.switches):
            sw.table_add("tb_set_switch_id", "set_switch_id", ['4'], [str(i + 1)])
    
    def set_space(self):
        global q_space, hop_space, egress_space
        for sw in self.switches:
            sw.table_add("tb_set_space", 
                         "set_space", 
                         ['0'], 
                         [str(q_space), str(hop_space), str(egress_space)])

    def routing_table(self):
        def add_route(switch, src_port, dst_port):
            switch.table_add("tb_forward", "set_egress_port", [str(src_port)], [str(dst_port)])

        # Map the exact switches we need for the valid 13-hop path
        c1, c2, c3 = self.switches[0], self.switches[1], self.switches[2]
        a1, a3, a4, a5, a6, a7 = self.switches[4], self.switches[6], self.switches[7], self.switches[8], self.switches[9], self.switches[10]
        e1, e3, e5, e8 = self.switches[12], self.switches[14], self.switches[16], self.switches[19]

        # ---------------------------------------------------------------------
        # CORRECTED 13-Hop Tromboning Path: h1 -> h16
        # Verified strictly against topology_uc2.py link creation order
        # Path: e1 -> a1 -> c1 -> a3 -> e3 -> a4 -> c3 -> a6 -> e5 -> a5 -> c2 -> a7 -> e8
        # ---------------------------------------------------------------------
        add_route(e1, 3, 1) # h1 to a1
        add_route(a1, 3, 1) # e1 to c1
        add_route(c1, 1, 2) # a1 to a3
        add_route(a3, 1, 3) # c1 to e3
        add_route(e3, 1, 2) # a3 to a4
        add_route(a4, 3, 1) # e3 to c3
        add_route(c3, 2, 3) # a4 to a6
        add_route(a6, 1, 3) # c3 to e5
        add_route(e5, 2, 1) # a6 to a5
        add_route(a5, 3, 2) # e5 to c2
        add_route(c2, 3, 4) # a5 to a7
        add_route(a7, 2, 4) # c2 to e8
        add_route(e8, 1, 4) # a7 to h16

    def set_param(self):
        global q_space, hop_space, egress_space
        
        # 13 hops means TTL goes from 63 down to 51
        for sw in self.switches:
            ttl = 63
            count = 0 
            while ttl >= 51: 
                sw.table_add("tb_set_param", "set_param",
                             [str(ttl), str(q_space), str(hop_space), str(egress_space)],
                             [str(count % q_space), str(count % hop_space), str(count % egress_space)])
                ttl -= 1
                count += 1
    
    def insert_int(self):
        global q_space, hop_space, egress_space
        
        for sw in self.switches:
            ttl = 63
            count = 0
            while ttl >= 51:
                sw.table_add("tb_insert_q", "set_q", 
                             [str(1), str(q_space), str(count % q_space), "0->65535"])
                sw.table_add("tb_insert_hop", "set_hop", 
                             [str(1), str(hop_space), str(count % hop_space), "0->65535"])
                sw.table_add("tb_insert_egress", "set_egress", 
                             [str(1), str(egress_space), str(count % egress_space), "0->65535"])
                
                sw.table_add("tb_insert_q", f"index_q{int(count % q_space)}",
                             [str(0), str(q_space), str(count % q_space), 
                              "0->" + str(int((1/math.ceil((count+1)/q_space))*65535))])
                sw.table_add("tb_insert_hop", f"index_hop{int(count % hop_space)}",
                             [str(0), str(hop_space), str(count % hop_space), 
                              "0->" + str(int((1/math.ceil((count+1)/hop_space))*65535))])
                sw.table_add("tb_insert_egress", f"index_egress{int(count % egress_space)}",
                             [str(0), str(egress_space), str(count % egress_space), 
                              "0->" + str(int((1/math.ceil((count+1)/egress_space))*65535))])
                
                ttl -= 1
                count += 1

if __name__ == "__main__":
    controller = Controller()
    print("Populating routes for 13-hop MCN path...")
    controller.set_source_node()
    controller.routing_table()
    controller.set_switch_id()
    controller.valid_space()
    controller.set_space()
    controller.set_param()
    controller.insert_int()
    print("UC2 Controller configured successfully!")
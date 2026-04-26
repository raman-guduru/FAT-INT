#!/usr/bin/env python3
import sys
import os
import math

sys.path.append('/home/p4/p4-utils')
from p4utils.utils.sswitch_thrift_API import *

# Pure / Classical INT: collect all items at all 5 hops
global q_space_1, hop_space_1, egress_space_1
q_space_1 = 5
hop_space_1 = 5
egress_space_1 = 5


class Controller(object):

###############################################################################################
##########                                 Ingress                                   ##########
###############################################################################################

    def __init__(self):
        """
        IMPORTANT: These must match your actual Mininet startup output:
            9090 -> a1
            9091 -> a2
            9092 -> a3
            9093 -> a4
            9094 -> c1
            9095 -> c2
            9096 -> e1
            9097 -> e2
            9098 -> e3
            9099 -> e4
        """
        self.sw = {}
        switch_map = {
            "a1": 9090, "a2": 9091, "a3": 9092, "a4": 9093,
            "c1": 9094, "c2": 9095,
            "e1": 9096, "e2": 9097, "e3": 9098, "e4": 9099,
        }

        for name, port in switch_map.items():
            try:
                self.sw[name] = SimpleSwitchThriftAPI(port)
                print(f"[OK] Connected to {name} on thrift port {port}")
            except Exception as e:
                print(f"[FAIL] Failed to connect to {name} on port {port}: {e}")

    def set_source_node(self):
        """Edge switches e1 and e2 act as ingress sources"""
        ingress_switches = ["e1", "e2"]
        for sw_name in ingress_switches:
            self.sw[sw_name].table_add("tb_set_source", "int_set_source", ['0x3'])

    def valid_space(self):
        """PURE INT: insert INT on every packet"""
        ingress_switches = ["e1", "e2"]
        for sw_name in ingress_switches:
            self.sw[sw_name].table_add(
                "tb_valid_space", "valid_space", ['1', '0->65535'], ['0']
            )

    def set_switch_id(self):
        """Assign switch IDs deterministically"""
        switch_ids = {
            "a1": 1, "a2": 2, "a3": 3, "a4": 4,
            "c1": 5, "c2": 6,
            "e1": 7, "e2": 8, "e3": 9, "e4": 10,
        }
        for sw_name, sid in switch_ids.items():
            self.sw[sw_name].table_add("tb_set_switch_id", "set_switch_id", ['4'], [str(sid)])

    def set_space(self):
        global q_space_1, hop_space_1, egress_space_1
        for sw in self.sw.values():
            sw.table_add(
                "tb_set_space", "set_space", ['0'],
                [str(q_space_1), str(hop_space_1), str(egress_space_1)]
            )

    def routing_table(self):
        """
        ECMP Routing Implementation
        Assigns multiple valid egress ports for destinations to load-balance traffic.
        """
        # Dictionary to track the next available group ID per switch to avoid collisions
        group_ids = {name: 1 for name in self.sw.keys()}

        def add_ecmp_route(sw_name, dst_ip, ports):
            sw = self.sw[sw_name]
            group_id = group_ids[sw_name]
            group_ids[sw_name] += 1  # Increment for the next route on this switch
            
            num_members = len(ports)
            
            # 1. Map IP to ECMP group
            sw.table_add("tb_ecmp_group", "set_ecmp_group", 
                         [dst_ip], 
                         [str(group_id), str(num_members)])

            # 2. Map group + index to actual port
            for index, port in enumerate(ports):
                sw.table_add("tb_ecmp_nhop", "set_egress_port", 
                             [str(group_id), str(index)], 
                             [str(port)])

        # Map host identifiers to IP addresses
        hosts = {
            "h1": "10.0.7.1", "h2": "10.0.7.2",
            "h3": "10.0.8.3", "h4": "10.0.8.4",
            "h5": "10.0.9.5", "h6": "10.0.9.6",
            "h7": "10.0.10.7", "h8": "10.0.10.8"
        }

        # =========================================================
        # EDGE SWITCHES (e1, e2, e3, e4)
        # =========================================================
        
        # e1: Local hosts strictly on port 3 & 4. All other traffic goes UP via port 1 (a1) or 2 (a2).
        add_ecmp_route("e1", hosts["h1"], [3])
        add_ecmp_route("e1", hosts["h2"], [4])
        for h in ["h3", "h4", "h5", "h6", "h7", "h8"]:
            add_ecmp_route("e1", hosts[h], [1, 2])

        # e2: Local hosts strictly on port 3 & 4. All other traffic goes UP via port 1 (a1) or 2 (a2).
        add_ecmp_route("e2", hosts["h3"], [3])
        add_ecmp_route("e2", hosts["h4"], [4])
        for h in ["h1", "h2", "h5", "h6", "h7", "h8"]:
            add_ecmp_route("e2", hosts[h], [1, 2])

        # e3: Local hosts strictly on port 3 & 4. All other traffic goes UP via port 1 (a3) or 2 (a4).
        add_ecmp_route("e3", hosts["h5"], [3])
        add_ecmp_route("e3", hosts["h6"], [4])
        for h in ["h1", "h2", "h3", "h4", "h7", "h8"]:
            add_ecmp_route("e3", hosts[h], [1, 2])

        # e4: Local hosts strictly on port 3 & 4. All other traffic goes UP via port 1 (a3) or 2 (a4).
        add_ecmp_route("e4", hosts["h7"], [3])
        add_ecmp_route("e4", hosts["h8"], [4])
        for h in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            add_ecmp_route("e4", hosts[h], [1, 2])

        # =========================================================
        # AGGREGATION SWITCHES (a1, a2, a3, a4)
        # =========================================================
        
        # a1 & a2 serve the left pod (h1-h4). 
        # Traffic for remote pod (h5-h8) goes UP via port 3 (c1) or 4 (c2).
        for a in ["a1", "a2"]:
            for h in ["h1", "h2"]: add_ecmp_route(a, hosts[h], [1]) # Down to e1
            for h in ["h3", "h4"]: add_ecmp_route(a, hosts[h], [2]) # Down to e2
            for h in ["h5", "h6", "h7", "h8"]: add_ecmp_route(a, hosts[h], [3, 4]) # Up to core

        # a3 & a4 serve the right pod (h5-h8).
        # Traffic for remote pod (h1-h4) goes UP via port 3 (c1) or 4 (c2).
        for a in ["a3", "a4"]:
            for h in ["h1", "h2", "h3", "h4"]: add_ecmp_route(a, hosts[h], [3, 4]) # Up to core
            for h in ["h5", "h6"]: add_ecmp_route(a, hosts[h], [1]) # Down to e3
            for h in ["h7", "h8"]: add_ecmp_route(a, hosts[h], [2]) # Down to e4

        # =========================================================
        # CORE SWITCHES (c1, c2)
        # =========================================================
        
        # c1 & c2 can reach the left pod via a1 (port 1) or a2 (port 2).
        # c1 & c2 can reach the right pod via a3 (port 3) or a4 (port 4).
        for c in ["c1", "c2"]:
            for h in ["h1", "h2", "h3", "h4"]: add_ecmp_route(c, hosts[h], [1, 2])
            for h in ["h5", "h6", "h7", "h8"]: add_ecmp_route(c, hosts[h], [3, 4])

        print("[OK] ECMP routing tables populated across all switches.")

###############################################################################################
##########                                  Egress                                    ##########
###############################################################################################

    def set_param(self):
        """Deterministic per-hop slot assignment for Classical INT."""
        global q_space_1, hop_space_1, egress_space_1
        for sw in self.sw.values():
            ttl = 63
            count = 0
            while ttl >= 59:
                sw.table_add(
                    "tb_set_param", "set_param",
                    [str(ttl), str(q_space_1), str(hop_space_1), str(egress_space_1)],
                    [str(count), str(count), str(count)]
                )
                ttl -= 1
                count += 1

    def insert_int(self):
        """Classical INT insertion rules"""
        global q_space_1, hop_space_1, egress_space_1
        for sw in self.sw.values():
            ttl = 63
            count = 0
            while ttl >= 59:
                sw.table_add("tb_insert_q", "set_q", [str(ttl),str(1), str(q_space_1), str(count), "0->65535"])
                sw.table_add("tb_insert_hop", "set_hop", [str(ttl),str(1), str(hop_space_1), str(count), "0->65535"])
                sw.table_add("tb_insert_egress", "set_egress", [str(ttl),str(1), str(egress_space_1), str(count), "0->65535"])
                ttl -= 1
                count += 1

###############################################################################################
##########                                    Main                                    ##########
###############################################################################################

if __name__ == "__main__":
    controller = Controller()

    print("Setting source nodes...")
    controller.set_source_node()

    print("Setting ECMP routing tables...")
    controller.routing_table()

    print("Setting switch IDs...")
    controller.set_switch_id()

    print("Configuring INT on all packets...")
    controller.valid_space()

    print("Setting classical INT spaces...")
    controller.set_space()

    print("Setting deterministic INT slot parameters...")
    controller.set_param()

    print("Populating deterministic INT insertion rules...")
    controller.insert_int()

    print("ECMP INT controller configuration complete!")
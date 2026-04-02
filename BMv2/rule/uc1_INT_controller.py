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
            "a1": 9090,
            "a2": 9091,
            "a3": 9092,
            "a4": 9093,
            "c1": 9094,
            "c2": 9095,
            "e1": 9096,
            "e2": 9097,
            "e3": 9098,
            "e4": 9099,
        }

        for name, port in switch_map.items():
            try:
                self.sw[name] = SimpleSwitchThriftAPI(port)
                print(f"[OK] Connected to {name} on thrift port {port}")
            except Exception as e:
                print(f"[FAIL] Failed to connect to {name} on port {port}: {e}")

    def set_source_node(self):
        """
        Edge switches e1 and e2 act as ingress sources
        """
        ingress_switches = ["e1", "e2"]
        for sw_name in ingress_switches:
            self.sw[sw_name].table_add("tb_set_source", "int_set_source", ['0x3'])

    def valid_space(self):
        """
        PURE INT: insert INT on every packet
        """
        ingress_switches = ["e1", "e2"]
        for sw_name in ingress_switches:
            self.sw[sw_name].table_add(
                "tb_valid_space",
                "valid_space",
                ['1', '0->65535'],
                ['0']
            )

    def set_switch_id(self):
        """
        Assign switch IDs deterministically
        """
        switch_ids = {
            "a1": 1,
            "a2": 2,
            "a3": 3,
            "a4": 4,
            "c1": 5,
            "c2": 6,
            "e1": 7,
            "e2": 8,
            "e3": 9,
            "e4": 10,
        }

        for sw_name, sid in switch_ids.items():
            self.sw[sw_name].table_add("tb_set_switch_id", "set_switch_id", ['4'], [str(sid)])

    def set_space(self):
        global q_space_1, hop_space_1, egress_space_1
        for sw in self.sw.values():
            sw.table_add(
                "tb_set_space",
                "set_space",
                ['0'],
                [str(q_space_1), str(hop_space_1), str(egress_space_1)]
            )

    def routing_table(self):
        """
        FULLY CORRECT deterministic forwarding for your actual port mapping.

        ---------------------------------------------------------
        Actual ports from your Mininet output
        ---------------------------------------------------------
        a1: 1:e1  2:e2  3:c1  4:c2
        a2: 1:e1  2:e2  3:c1  4:c2
        a3: 1:e3  2:e4  3:c1  4:c2
        a4: 1:e3  2:e4  3:c1  4:c2

        c1: 1:a1  2:a2  3:a3  4:a4
        c2: 1:a1  2:a2  3:a3  4:a4

        e1: 1:a1  2:a2  3:h1  4:h2
        e2: 1:a1  2:a2  3:h3  4:h4
        e3: 1:a3  2:a4  3:h5  4:h6
        e4: 1:a3  2:a4  3:h7  4:h8
        """

        a1 = self.sw["a1"]
        a2 = self.sw["a2"]
        a3 = self.sw["a3"]
        a4 = self.sw["a4"]
        c1 = self.sw["c1"]
        c2 = self.sw["c2"]
        e1 = self.sw["e1"]
        e2 = self.sw["e2"]
        e3 = self.sw["e3"]
        e4 = self.sw["e4"]

        def add_route(sw, dst_ip, port):
            sw.table_add("tb_forward", "set_egress_port", [dst_ip], [str(port)])

        # Hosts
        h1 = "10.0.7.1"
        h2 = "10.0.7.2"
        h3 = "10.0.8.3"
        h4 = "10.0.8.4"
        h5 = "10.0.9.5"
        h6 = "10.0.9.6"
        h7 = "10.0.10.7"
        h8 = "10.0.10.8"

        # =========================================================
        # EDGE SWITCHES
        # =========================================================
        # Use BOTH uplinks consistently for reachability.
        # e1/e2 are pod-left ; e3/e4 are pod-right

        # e1: local h1,h2 ; remote pod via a1
        add_route(e1, h1, 3)
        add_route(e1, h2, 4)
        add_route(e1, h3, 2)   # same pod -> e2 via a2
        add_route(e1, h4, 2)
        add_route(e1, h5, 1)   # remote pod -> a1
        add_route(e1, h6, 1)
        add_route(e1, h7, 1)
        add_route(e1, h8, 1)

        # e2: local h3,h4 ; remote pod via a1
        add_route(e2, h1, 1)   # same pod -> e1 via a1
        add_route(e2, h2, 1)
        add_route(e2, h3, 3)
        add_route(e2, h4, 4)
        add_route(e2, h5, 2)   # remote pod -> a2
        add_route(e2, h6, 2)
        add_route(e2, h7, 2)
        add_route(e2, h8, 2)

        # e3: local h5,h6 ; remote pod via a3
        add_route(e3, h1, 1)
        add_route(e3, h2, 1)
        add_route(e3, h3, 2)
        add_route(e3, h4, 2)
        add_route(e3, h5, 3)
        add_route(e3, h6, 4)
        add_route(e3, h7, 2)   # same pod -> e4 via a4
        add_route(e3, h8, 2)

        # e4: local h7,h8 ; remote pod via a4
        add_route(e4, h1, 2)
        add_route(e4, h2, 2)
        add_route(e4, h3, 1)
        add_route(e4, h4, 1)
        add_route(e4, h5, 1)   # same pod -> e3 via a3
        add_route(e4, h6, 1)
        add_route(e4, h7, 3)
        add_route(e4, h8, 4)

        # =========================================================
        # AGGREGATION SWITCHES
        # =========================================================

        # a1 serves e1/e2 ; remote pod via c1
        add_route(a1, h1, 1)
        add_route(a1, h2, 1)
        add_route(a1, h3, 2)
        add_route(a1, h4, 2)
        add_route(a1, h5, 3)
        add_route(a1, h6, 3)
        add_route(a1, h7, 3)
        add_route(a1, h8, 3)

        # a2 serves e1/e2 ; remote pod via c2
        add_route(a2, h1, 1)
        add_route(a2, h2, 1)
        add_route(a2, h3, 2)
        add_route(a2, h4, 2)
        add_route(a2, h5, 4)
        add_route(a2, h6, 4)
        add_route(a2, h7, 4)
        add_route(a2, h8, 4)

        # a3 serves e3/e4 ; remote pod via c1
        add_route(a3, h1, 3)
        add_route(a3, h2, 3)
        add_route(a3, h3, 3)
        add_route(a3, h4, 3)
        add_route(a3, h5, 1)
        add_route(a3, h6, 1)
        add_route(a3, h7, 2)
        add_route(a3, h8, 2)

        # a4 serves e3/e4 ; remote pod via c2
        add_route(a4, h1, 4)
        add_route(a4, h2, 4)
        add_route(a4, h3, 4)
        add_route(a4, h4, 4)
        add_route(a4, h5, 1)
        add_route(a4, h6, 1)
        add_route(a4, h7, 2)
        add_route(a4, h8, 2)

        # =========================================================
        # CORE SWITCHES
        # =========================================================
        # c1 prefers a1/a3
        add_route(c1, h1, 1)
        add_route(c1, h2, 1)
        add_route(c1, h3, 2)
        add_route(c1, h4, 2)
        add_route(c1, h5, 3)
        add_route(c1, h6, 3)
        add_route(c1, h7, 4)
        add_route(c1, h8, 4)

        # c2 prefers a1/a3 or a2/a4 according to wiring
        add_route(c2, h1, 1)
        add_route(c2, h2, 1)
        add_route(c2, h3, 2)
        add_route(c2, h4, 2)
        add_route(c2, h5, 3)
        add_route(c2, h6, 3)
        add_route(c2, h7, 4)
        add_route(c2, h8, 4)

        print("[OK] Routing rules installed correctly.")

###############################################################################################
##########                                  Egress                                    ##########
###############################################################################################

    def set_param(self):
        """
        Deterministic per-hop slot assignment for Classical INT.
        In a 5-hop path, TTL goes:
            ingress source sends ttl=64
            after 1st hop -> 63
            after 2nd hop -> 62
            after 3rd hop -> 61
            after 4th hop -> 60
            after 5th hop -> 59

        We map:
            ttl 63 -> slot 0
            ttl 62 -> slot 1
            ttl 61 -> slot 2
            ttl 60 -> slot 3
            ttl 59 -> slot 4
        """
        global q_space_1, hop_space_1, egress_space_1

        for sw in self.sw.values():
            ttl = 63
            count = 0

            while ttl >= 59:
                sw.table_add(
                    "tb_set_param",
                    "set_param",
                    [str(ttl), str(q_space_1), str(hop_space_1), str(egress_space_1)],
                    [str(count), str(count), str(count)]
                )
                ttl -= 1
                count += 1

    def insert_int(self):
        """
        Classical INT: always insert queue/hop/egress telemetry
        into the deterministic slot selected by tb_set_param.
        """
        global q_space_1, hop_space_1, egress_space_1

        for sw in self.sw.values():
            ttl = 63
            count = 0

            while ttl >= 59:
                sw.table_add(
                    "tb_insert_q",
                    "set_q",
                    [str(ttl),str(1), str(q_space_1), str(count), "0->65535"]
                )

                sw.table_add(
                    "tb_insert_hop",
                    "set_hop",
                    [str(ttl),str(1), str(hop_space_1), str(count), "0->65535"]
                )

                sw.table_add(
                    "tb_insert_egress",
                    "set_egress",
                    [str(ttl),str(1), str(egress_space_1), str(count), "0->65535"]
                )

                ttl -= 1
                count += 1


###############################################################################################
##########                                    Main                                    ##########
###############################################################################################

if __name__ == "__main__":
    controller = Controller()

    print("Setting source nodes...")
    controller.set_source_node()

    print("Setting routing tables...")
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

    print("Pure INT controller configuration complete!")
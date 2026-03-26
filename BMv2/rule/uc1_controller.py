#!/usr/bin/env python3
import sys
import math

sys.path.append('/home/p4/p4-utils')
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI

# ============================================================
# FAT-INT Use Case 1 (Paper Section 5.3)
# Queue samples  = 5
# Hop samples    = 3
# Egress samples = 1
# ============================================================
q_space_1 = 5
hop_space_1 = 3
egress_space_1 = 1


class Controller(object):

    ###########################################################################
    # INIT
    ###########################################################################
    def __init__(self):
        """
        Thrift ports from your Mininet output:
            a1 -> 9090
            a2 -> 9091
            a3 -> 9092
            a4 -> 9093
            c1 -> 9094
            c2 -> 9095
            e1 -> 9096
            e2 -> 9097
            e3 -> 9098
            e4 -> 9099
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
                print(f"[FAIL] Could not connect to {name} on port {port}: {e}")

    ###########################################################################
    # INGRESS CONFIG
    ###########################################################################
    def set_source_node(self):
        """
        Only sender-side edge switches inject INT.
        h1-h4 are attached to e1/e2.
        """
        ingress_switches = ["e1", "e2"]
        for sw_name in ingress_switches:
            self.sw[sw_name].table_add(
                "tb_set_source",
                "int_set_source",
                ['0x3']
            )

    def valid_space(self):
        """
        FAT-INT ingress probability:
        Paper use-case style: ~40% packet sampling at ingress.

        Match:
            [is_source=1, random=0->ceil(65535*0.4)]
        Action:
            valid_space(0)
        """
        ingress_switches = ["e1", "e2"]
        threshold = math.ceil(65535 * 0.4)

        for sw_name in ingress_switches:
            self.sw[sw_name].table_add(
                "tb_valid_space",
                "valid_space",
                ['1', f'0->{threshold}'],
                ['0']
            )

    def set_switch_id(self):
        """
        Stable switch IDs.
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
            self.sw[sw_name].table_add(
                "tb_set_switch_id",
                "set_switch_id",
                ['4'],
                [str(sid)]
            )

    def set_space(self):
        """
        Install telemetry slot capacities on all switches.
        """
        for sw in self.sw.values():
            sw.table_add(
                "tb_set_space",
                "set_space",
                ['0'],
                [str(q_space_1), str(hop_space_1), str(egress_space_1)]
            )

    ###########################################################################
    # FORWARDING
    ###########################################################################
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

    ###########################################################################
    # EGRESS FAT-INT LOGIC
    ###########################################################################
    def set_param(self):
        """
        Install deterministic hop->slot mapping using TTL.

        For a 5-hop path:
            sender emits TTL=64
            after hop1 -> 63
            after hop2 -> 62
            after hop3 -> 61
            after hop4 -> 60
            after hop5 -> 59

        FAT-INT maps each hop into rotating reservoir slots.
        """
        for sw in self.sw.values():
            ttl = 63
            count = 0

            while ttl >= 59:
                sw.table_add(
                    "tb_set_param",
                    "set_param",
                    [str(ttl), str(q_space_1), str(hop_space_1), str(egress_space_1)],
                    [
                        str(count % q_space_1),
                        str(count % hop_space_1),
                        str(count % egress_space_1)
                    ]
                )
                ttl -= 1
                count += 1

    def insert_int(self):
        """
        FAT-INT insertion rules:
        1. If slot is empty / directly chosen -> set_q / set_hop / set_egress
        2. Otherwise use probabilistic replacement according to MRS logic

        NOTE:
        These action names MUST exist in your P4:
            set_q, set_hop, set_egress
            index_q0..index_q4
            index_hop0..index_hop2
            index_egress0
        """

        for sw in self.sw.values():
            ttl = 63
            count = 0

            while ttl >= 59:
                q_idx = count % q_space_1
                hop_idx = count % hop_space_1
                eg_idx = count % egress_space_1

                # ------------------------------------------------------------
                # 1) Direct insert rules (initial fill / deterministic placement)
                # ------------------------------------------------------------
                sw.table_add(
                    "tb_insert_q",
                    "set_q",
                    ['1', str(q_space_1), str(q_idx), "0->65535"]
                )

                sw.table_add(
                    "tb_insert_hop",
                    "set_hop",
                    ['1', str(hop_space_1), str(hop_idx), "0->65535"]
                )

                sw.table_add(
                    "tb_insert_egress",
                    "set_egress",
                    ['1', str(egress_space_1), str(eg_idx), "0->65535"]
                )

                # ------------------------------------------------------------
                # 2) FAT-INT Multi-slot Reservoir Sampling replacement rules
                # ------------------------------------------------------------
                # Probability = 1 / ceil((count+1)/space)
                #
                # count: 0 1 2 3 4
                # q_space=5       -> all first five have full chance
                # hop_space=3     -> later hops begin replacement
                # egress_space=1  -> classic reservoir behavior
                # ------------------------------------------------------------

                q_prob = int((1 / math.ceil((count + 1) / q_space_1)) * 65535)
                hop_prob = int((1 / math.ceil((count + 1) / hop_space_1)) * 65535)
                eg_prob = int((1 / math.ceil((count + 1) / egress_space_1)) * 65535)

                sw.table_add(
                    "tb_insert_q",
                    f"index_q{q_idx}",
                    ['0', str(q_space_1), str(q_idx), f"0->{q_prob}"]
                )

                sw.table_add(
                    "tb_insert_hop",
                    f"index_hop{hop_idx}",
                    ['0', str(hop_space_1), str(hop_idx), f"0->{hop_prob}"]
                )

                sw.table_add(
                    "tb_insert_egress",
                    f"index_egress{eg_idx}",
                    ['0', str(egress_space_1), str(eg_idx), f"0->{eg_prob}"]
                )

                ttl -= 1
                count += 1

    ###########################################################################
    # OPTIONAL: CLEAR TABLES FIRST
    ###########################################################################
    def clear_all_tables(self):
        """
        Useful when re-running controller without restarting Mininet.
        Safe to comment out if your BMv2 build doesn't support clear.
        """
        table_names = [
            "tb_set_source",
            "tb_valid_space",
            "tb_set_switch_id",
            "tb_set_space",
            "tb_forward",
            "tb_set_param",
            "tb_insert_q",
            "tb_insert_hop",
            "tb_insert_egress",
        ]

        for sw_name, sw in self.sw.items():
            for table in table_names:
                try:
                    sw.table_clear(table)
                except Exception:
                    pass

        print("[OK] Existing table entries cleared (where supported).")


###############################################################################
# MAIN
###############################################################################
if __name__ == "__main__":
    controller = Controller()

    # Optional but recommended if reusing the same Mininet session
    controller.clear_all_tables()

    print("Setting source nodes...")
    controller.set_source_node()

    print("Installing routing tables...")
    controller.routing_table()

    print("Setting switch IDs...")
    controller.set_switch_id()

    print("Configuring ingress sampling validity...")
    controller.valid_space()

    print("Setting FAT-INT spaces...")
    controller.set_space()

    print("Setting FAT-INT hop/slot parameters...")
    controller.set_param()

    print("Installing FAT-INT insertion rules...")
    controller.insert_int()

    print("[DONE] FAT-INT controller configuration complete!")
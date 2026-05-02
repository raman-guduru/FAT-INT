#!/usr/bin/env python3
import sys
import math

sys.path.append('/home/p4/p4-utils')
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI

# FAT-INT Constants
q_space_1 = 5
hop_space_1 = 3
egress_space_1 = 1

class Controller(object):

    def __init__(self):
        self.sw = {}
        # Thrift ports must match your topology
        switch_map = {
            "a1": 9090, "a2": 9091, "a3": 9092, "a4": 9093,
            "c1": 9094, "c2": 9095,
            "e1": 9096, "e2": 9097, "e3": 9098, "e4": 9099,
        }

        for name, port in switch_map.items():
            try:
                self.sw[name] = SimpleSwitchThriftAPI(port)
            except Exception as e:
                print(f"[FAIL] {name} connection failed: {e}")

    def set_source_node(self):
        for sw_name in ["e1", "e2"]:
            self.sw[sw_name].table_add("tb_set_source", "int_set_source", ['0x3'])

    def valid_space(self):
        for sw_name in ["e1", "e2"]:
            self.sw[sw_name].table_add("tb_valid_space", "valid_space", ['1', '0->65535'], ['0'])

    def set_switch_id(self):
        switch_ids = {"a1": 1, "a2": 2, "a3": 3, "a4": 4, "c1": 5, "c2": 6, "e1": 7, "e2": 8, "e3": 9, "e4": 10}
        for sw_name, sid in switch_ids.items():
            self.sw[sw_name].table_add("tb_set_switch_id", "set_switch_id", ['4'], [str(sid)])

    def set_space(self):
        for sw in self.sw.values():
            sw.table_add("tb_set_space", "set_space", ['0'], [str(q_space_1), str(hop_space_1), str(egress_space_1)])

    # =========================================================
    # REPAIRED ECMP ROUTING
    # =========================================================
    def routing_table(self):
        group_ids = {name: 1 for name in self.sw.keys()}

        def add_ecmp_route(sw_name, dst_ip, ports):
            sw = self.sw[sw_name]
            gid = group_ids[sw_name]
            group_ids[sw_name] += 1
            # 1. Add group definition
            sw.table_add("tb_ecmp_group", "set_ecmp_group", [dst_ip], [str(gid), str(len(ports))])
            # 2. Add member ports for the group
            for idx, p in enumerate(ports):
                sw.table_add("tb_ecmp_nhop", "set_egress_port", [str(gid), str(idx)], [str(p)])

        hosts = {
            "h1": "10.0.7.1", "h2": "10.0.7.2", "h3": "10.0.8.3", "h4": "10.0.8.4",
            "h5": "10.0.9.5", "h6": "10.0.9.6", "h7": "10.0.10.7", "h8": "10.0.10.8"
        }

        # Edge e1/e2: Ports 3,4 are local. Ports 1,2 go to Aggregation a1,a2.
        for h_local, port in [("h1", 3), ("h2", 4)]: add_ecmp_route("e1", hosts[h_local], [port])
        for h_rem in ["h3", "h4", "h5", "h6", "h7", "h8"]: add_ecmp_route("e1", hosts[h_rem], [1, 2])

        for h_local, port in [("h3", 3), ("h4", 4)]: add_ecmp_route("e2", hosts[h_local], [port])
        for h_rem in ["h1", "h2", "h5", "h6", "h7", "h8"]: add_ecmp_route("e2", hosts[h_rem], [1, 2])

        # Edge e3/e4: Ports 3,4 are local. Ports 1,2 go to Aggregation a3,a4.
        for h_local, port in [("h5", 3), ("h6", 4)]: add_ecmp_route("e3", hosts[h_local], [port])
        for h_rem in ["h1", "h2", "h3", "h4", "h7", "h8"]: add_ecmp_route("e3", hosts[h_rem], [1, 2])

        for h_local, port in [("h7", 3), ("h8", 4)]: add_ecmp_route("e4", hosts[h_local], [port])
        for h_rem in ["h1", "h2", "h3", "h4", "h5", "h6"]: add_ecmp_route("e4", hosts[h_rem], [1, 2])

        # Aggregation a1/a2 (Left Pod): Down to e1 (port 1), e2 (port 2). Up to Core c1,c2 (port 3,4).
        for a in ["a1", "a2"]:
            for h in ["h1", "h2"]: add_ecmp_route(a, hosts[h], [1])
            for h in ["h3", "h4"]: add_ecmp_route(a, hosts[h], [2])
            for h in ["h5", "h6", "h7", "h8"]: add_ecmp_route(a, hosts[h], [3, 4])

        # Aggregation a3/a4 (Right Pod): Down to e3 (port 1), e4 (port 2). Up to Core c1,c2 (port 3,4).
        for a in ["a3", "a4"]:
            for h in ["h1", "h2", "h3", "h4"]: add_ecmp_route(a, hosts[h], [3, 4])
            for h in ["h5", "h6"]: add_ecmp_route(a, hosts[h], [1])
            for h in ["h7", "h8"]: add_ecmp_route(a, hosts[h], [2])

        # Core c1/c2: Left Pod via a1,a2 (port 1,2). Right Pod via a3,a4 (port 3,4).
        for c in ["c1", "c2"]:
            for h in ["h1", "h2", "h3", "h4"]: add_ecmp_route(c, hosts[h], [1, 2])
            for h in ["h5", "h6", "h7", "h8"]: add_ecmp_route(c, hosts[h], [3, 4])

        print("[OK] ECMP Tables fixed.")

    def set_param(self):
        for sw in self.sw.values():
            ttl, count = 63, 0
            while ttl >= 59:
                sw.table_add("tb_set_param", "set_param", 
                             [str(ttl), str(q_space_1), str(hop_space_1), str(egress_space_1)],
                             [str(count % q_space_1), str(count % hop_space_1), str(count % egress_space_1)])
                ttl -= 1; count += 1

    def insert_int(self):
        for sw in self.sw.values():
            ttl, count = 63, 0
            while ttl >= 59:
                qi, hi, ei = count % q_space_1, count % hop_space_1, count % egress_space_1
                sw.table_add("tb_insert_q", "set_q", [str(ttl), '1', str(q_space_1), str(qi), "0->65535"])
                sw.table_add("tb_insert_hop", "set_hop", [str(ttl), '1', str(hop_space_1), str(hi), "0->65535"])
                sw.table_add("tb_insert_egress", "set_egress", [str(ttl), '1', str(egress_space_1), str(ei), "0->65535"])
                
                # Reservoir logic
                qp = int((1 / math.ceil((count + 1) / q_space_1)) * 65535)
                hp = int((1 / math.ceil((count + 1) / hop_space_1)) * 65535)
                ep = int((1 / math.ceil((count + 1) / egress_space_1)) * 65535)
                sw.table_add("tb_insert_q", f"index_q{qi}", [str(ttl), '0', str(q_space_1), str(qi), f"0->{qp}"])
                sw.table_add("tb_insert_hop", f"index_hop{hi}", [str(ttl), '0', str(hop_space_1), str(hi), f"0->{hp}"])
                sw.table_add("tb_insert_egress", f"index_egress{ei}", [str(ttl), '0', str(egress_space_1), str(ei), f"0->{ep}"])
                ttl -= 1; count += 1

    def clear_all(self):
        tabs = ["tb_set_source", "tb_valid_space", "tb_set_switch_id", "tb_set_space", "tb_ecmp_group", "tb_ecmp_nhop", "tb_set_param", "tb_insert_q", "tb_insert_hop", "tb_insert_egress"]
        for sw in self.sw.values():
            for t in tabs:
                try: sw.table_clear(t)
                except: pass

if __name__ == "__main__":
    c = Controller()
    c.clear_all()
    c.set_source_node()
    c.routing_table()
    c.set_switch_id()
    c.valid_space()
    c.set_space()
    c.set_param()
    c.insert_int()
    print("[DONE] FAT-INT Controller with Fixed ECMP.")
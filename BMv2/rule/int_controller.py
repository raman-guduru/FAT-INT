from p4utils.utils.sswitch_thrift_API import *
import math

global q_space_1, hop_space_1, egress_space_1, q_space_2, hop_space_2, egress_space_2
q_space_1 = 5
hop_space_1 = 3
egress_space_1 = 1
# q_space_2 = 2
# hop_space_2 = 1
# egress_space_2 = 0

class Controller(object):

###############################################################################################
##########                                 Ingress                                   ##########
###############################################################################################

    def __init__(self):
        self.controller_sw1 = SimpleSwitchThriftAPI(9090)
        self.controller_sw2 = SimpleSwitchThriftAPI(9091)
        self.controller_sw3 = SimpleSwitchThriftAPI(9092)
        self.controller_sw4 = SimpleSwitchThriftAPI(9093)
        self.controller_sw5 = SimpleSwitchThriftAPI(9094)

    def set_source_node(self):
        self.controller_sw1.table_add("tb_set_source",
                                      "int_set_source",
                                      ['0x3'],
                                      )
    
    def valid_space(self):
        self.controller_sw1.table_add("tb_valid_space",
                                      "valid_space",
                                      ['1',f'0->{math.ceil(65535*0.4)}'],
                                      ['0'])
        # self.controller_sw1.table_add("tb_valid_space",
        #                               "valid_space",
        #                               ['1',f'{math.ceil(65535*0.4)+1}->{math.ceil(65535*0.8)}'],
        #                               ['1'])

    def set_switch_id(self):
        self.controller_sw1.table_add("tb_set_switch_id",
                                      "set_switch_id",
                                      ['4'],
                                      ['1'])
        self.controller_sw2.table_add("tb_set_switch_id",
                                      "set_switch_id",
                                      ['4'],
                                      ['2'])
        self.controller_sw3.table_add("tb_set_switch_id",
                                      "set_switch_id",
                                      ['4'],
                                      ['3'])
        self.controller_sw4.table_add("tb_set_switch_id",
                                      "set_switch_id",
                                      ['4'],
                                      ['4'])
        self.controller_sw5.table_add("tb_set_switch_id",
                                      "set_switch_id",
                                      ['4'],
                                      ['5'])
    
    def set_space(self):
        global q_space_1, hop_space_1, egress_space_1, q_space_2, hop_space_2, egress_space_2
        self.controller_sw1.table_add("tb_set_space",
                                      "set_space",
                                      ['0'],
                                      [str(q_space_1),str(hop_space_1),str(egress_space_1)])
        self.controller_sw2.table_add("tb_set_space",
                                      "set_space",
                                      ['0'],
                                      [str(q_space_1),str(hop_space_1),str(egress_space_1)])
        self.controller_sw3.table_add("tb_set_space",
                                      "set_space",
                                      ['0'],
                                      [str(q_space_1),str(hop_space_1),str(egress_space_1)])
        self.controller_sw4.table_add("tb_set_space",
                                      "set_space",
                                      ['0'],
                                      [str(q_space_1),str(hop_space_1),str(egress_space_1)])
        self.controller_sw5.table_add("tb_set_space",
                                      "set_space",
                                      ['0'],
                                      [str(q_space_1),str(hop_space_1),str(egress_space_1)])
 
        self.controller_sw1.table_add("tb_set_space",
                                      "set_space",
                                      ['1'],
                                      [str(q_space_2),str(hop_space_2),str(egress_space_2)])
        self.controller_sw2.table_add("tb_set_space",
                                      "set_space",
                                      ['1'],
                                      [str(q_space_2),str(hop_space_2),str(egress_space_2)])
        self.controller_sw3.table_add("tb_set_space",
                                      "set_space",
                                      ['1'],
                                      [str(q_space_2),str(hop_space_2),str(egress_space_2)])
        self.controller_sw4.table_add("tb_set_space",
                                      "set_space",
                                      ['1'],
                                      [str(q_space_2),str(hop_space_2),str(egress_space_2)])
        self.controller_sw5.table_add("tb_set_space",
                                      "set_space",
                                      ['1'],
                                      [str(q_space_2),str(hop_space_2),str(egress_space_2)])
        
    def routing_table(self):
        self.controller_sw1.table_add("tb_forward",
                                      "set_egress_port",
                                      ['1'],
                                      ['2'])
        self.controller_sw2.table_add("tb_forward",
                                      "set_egress_port",
                                      ['1'],
                                      ['2'])
        self.controller_sw3.table_add("tb_forward",
                                      "set_egress_port",
                                      ['1'],
                                      ['2'])
        self.controller_sw4.table_add("tb_forward",
                                      "set_egress_port",
                                      ['1'],
                                      ['2'])
        self.controller_sw5.table_add("tb_forward",
                                      "set_egress_port",
                                      ['2'],
                                      ['1'])
    
################################################################################################
##########                                  Egress                                    ##########
################################################################################################

    def set_param(self):
        global q_space_1, hop_space_1, egress_space_1, q_space_2, hop_space_2, egress_space_2
        ttl= 63
        count = 63-ttl
        
        self.controller_sw1.table_add("tb_set_param",
                                      "set_param",
                                      [str(ttl),str(q_space_1),str(hop_space_1),str(egress_space_1)],
                                      [str(count%q_space_1),str(count%hop_space_1),str(count%egress_space_1)])
        if egress_space_2 == 0:
            self.controller_sw1.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(0)])
        else:
            self.controller_sw1.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(count%egress_space_2)])
        ttl -= 1
        count += 1

        self.controller_sw2.table_add("tb_set_param",
                                      "set_param",
                                      [str(ttl),str(q_space_1),str(hop_space_1),str(egress_space_1)],
                                      [str(count%q_space_1),str(count%hop_space_1),str(count%egress_space_1)])
        if egress_space_2 == 0:
            self.controller_sw2.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(0)])
        else:
            self.controller_sw2.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(count%egress_space_2)])
        ttl -= 1
        count += 1

        self.controller_sw3.table_add("tb_set_param",
                                      "set_param",
                                      [str(ttl),str(q_space_1),str(hop_space_1),str(egress_space_1)],
                                      [str(count%q_space_1),str(count%hop_space_1),str(count%egress_space_1)])
        if egress_space_2 == 0:
            self.controller_sw3.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(0)])
        else:
            self.controller_sw3.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(count%egress_space_2)])
        ttl -= 1
        count += 1

        self.controller_sw4.table_add("tb_set_param",
                                      "set_param",
                                      [str(ttl),str(q_space_1),str(hop_space_1),str(egress_space_1)],
                                      [str(count%q_space_1),str(count%hop_space_1),str(count%egress_space_1)])
        if egress_space_2 == 0:
            self.controller_sw4.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(0)])
        else:
            self.controller_sw4.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(count%egress_space_2)])
        ttl -= 1
        count += 1

        self.controller_sw5.table_add("tb_set_param",
                                      "set_param",
                                      [str(ttl),str(q_space_1),str(hop_space_1),str(egress_space_1)],
                                      [str(count%q_space_1),str(count%hop_space_1),str(count%egress_space_1)])
        if egress_space_2 == 0:
            self.controller_sw5.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(0)])
        else:
            self.controller_sw5.table_add("tb_set_param",
                                          "set_param",
                                          [str(ttl),str(q_space_2),str(hop_space_2),str(egress_space_2)],
                                          [str(count%q_space_2),str(count%hop_space_2),str(count%egress_space_2)])
        ttl -= 1
        count += 1
    
    def insert_int(self):
        global q_space_1, hop_space_1, egress_space_1, q_space_2, hop_space_2, egress_space_2
        ttl= 63
        count = 63-ttl

        self.controller_sw1.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_1), str(count%q_space_1), "0->65535"],
                                       )
        self.controller_sw1.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_1), str(count%hop_space_1), "0->65535"],
                                       )
        self.controller_sw1.table_add("tb_insert_egress",
                                      "set_egress",
                                      [str(1),str(egress_space_1), str(count%egress_space_1), "0->65535"],
                                      )

        self.controller_sw1.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_2), str(count%q_space_2), "0->65535"],
                                       )
        self.controller_sw1.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_2), str(count%hop_space_2), "0->65535"],
                                      )
        try:
            self.controller_sw1.table_add("tb_insert_egress",
                                          "set_egress",[str(1),str(egress_space_2), str(count%egress_space_2), "0->65535"],)
        except:
            print("")
 
        self.controller_sw1.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_1)}",
                                      [str(0),str(q_space_1), str(count%q_space_1), "0->"+str(int((1/math.ceil((count+1)/q_space_1))*65535))],
                                      )
        self.controller_sw1.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_1)}",
                                      [str(0),str(hop_space_1), str(count%hop_space_1), "0->"+str(int((1/math.ceil((count+1)/hop_space_1))*65535))],
                                      )
        self.controller_sw1.table_add("tb_insert_egress",
                                      f"index_egress{int(count%egress_space_1)}",
                                      [str(0),str(egress_space_1), str(count%egress_space_1), "0->"+str(int((1/math.ceil((count+1)/egress_space_1))*65535))],
                                      )

        self.controller_sw1.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_2)}",
                                      [str(0),str(q_space_2), str(count%q_space_2), "0->"+str(int((1/math.ceil((count+1)/q_space_2))*65535))],
                                      )
        self.controller_sw1.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_2)}",
                                      [str(0),str(hop_space_2), str(count%hop_space_2), "0->"+str(int((1/math.ceil((count+1)/hop_space_2))*65535))],
                                      )
        try:
            self.controller_sw1.table_add("tb_insert_egress",
                                          f"index_egress{int(count%egress_space_2)}",
                                          [str(0),str(egress_space_2), str(count%egress_space_2), "0->"+str(int((1/math.ceil((count+1)/egress_space_2))*65535))],
                                          )
            ttl -= 1
            count += 1
        except:
            ttl -= 1
            count += 1

        self.controller_sw2.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_1), str(count%q_space_1), "0->65535"],
                                      )
        self.controller_sw2.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_1), str(count%hop_space_1), "0->65535"],
                                      )
        self.controller_sw2.table_add("tb_insert_egress",
                                      "set_egress",
                                      [str(1),str(egress_space_1), str(count%egress_space_1), "0->65535"],
                                      )

        self.controller_sw2.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_2), str(count%q_space_2), "0->65535"],
                                      )
        self.controller_sw2.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_2), str(count%hop_space_2), "0->65535"],
                                      )
        try:
            self.controller_sw2.table_add("tb_insert_egress",
                                          "set_egress",
                                          [str(1),str(egress_space_2), str(count%egress_space_2), "0->65535"],
                                          )
        except:
            print("")

        self.controller_sw2.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_1)}",
                                      [str(0),str(q_space_1), str(count%q_space_1), "0->"+str(int((1/math.ceil((count+1)/q_space_1))*65535))],
                                      )
        self.controller_sw2.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_1)}",
                                      [str(0),str(hop_space_1), str(count%hop_space_1), "0->"+str(int((1/math.ceil((count+1)/hop_space_1))*65535))],
                                      )
        self.controller_sw2.table_add("tb_insert_egress",
                                      f"index_egress{int(count%egress_space_1)}",
                                      [str(0),str(egress_space_1), str(count%egress_space_1), "0->"+str(int((1/math.ceil((count+1)/egress_space_1))*65535))],
                                      )

        self.controller_sw2.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_2)}",
                                      [str(0),str(q_space_2), str(count%q_space_2), "0->"+str(int((1/math.ceil((count+1)/q_space_2))*65535))],
                                      )
        self.controller_sw2.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_2)}",
                                      [str(0),str(hop_space_2), str(count%hop_space_2), "0->"+str(int((1/math.ceil((count+1)/hop_space_2))*65535))],
                                      )
        try:
            self.controller_sw2.table_add("tb_insert_egress",
                                          f"index_egress{int(count%egress_space_2)}",
                                          [str(0),str(egress_space_2), str(count%egress_space_2), "0->"+str(int((1/math.ceil((count+1)/egress_space_2))*65535))],
                                          )
            ttl -= 1
            count += 1    
        except:
            ttl -= 1
            count += 1        

        self.controller_sw3.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_1), str(count%q_space_1), "0->65535"],
                                      )
        self.controller_sw3.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_1), str(count%hop_space_1), "0->65535"],
                                      )
        self.controller_sw3.table_add("tb_insert_egress",
                                      "set_egress",
                                      [str(1),str(egress_space_1), str(count%egress_space_1), "0->65535"],
                                      )

        self.controller_sw3.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_2), str(count%q_space_2), "0->65535"],
                                      )
        self.controller_sw3.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_2), str(count%hop_space_2), "0->65535"],
                                      )
        try:
            self.controller_sw3.table_add("tb_insert_egress",
                                          "set_egress",
                                          [str(1),str(egress_space_2), str(count%egress_space_2), "0->65535"],
                                          )
        except:
            print("")

        self.controller_sw3.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_1)}",
                                      [str(0),str(q_space_1), str(count%q_space_1), "0->"+str(int((1/math.ceil((count+1)/q_space_1))*65535))],
                                      )
        self.controller_sw3.table_add("tb_insert_hop"
                                      ,f"index_hop{int(count%hop_space_1)}",
                                      [str(0),str(hop_space_1), str(count%hop_space_1), "0->"+str(int((1/math.ceil((count+1)/hop_space_1))*65535))],
                                      )
        self.controller_sw3.table_add("tb_insert_egress",
                                      f"index_egress{int(count%egress_space_1)}",
                                      [str(0),str(egress_space_1), str(count%egress_space_1), "0->"+str(int((1/math.ceil((count+1)/egress_space_1))*65535))],
                                      )

        self.controller_sw3.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_2)}",
                                      [str(0),str(q_space_2), str(count%q_space_2), "0->"+str(int((1/math.ceil((count+1)/q_space_2))*65535))],
                                      )
        self.controller_sw3.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_2)}",
                                      [str(0),str(hop_space_2), str(count%hop_space_2), "0->"+str(int((1/math.ceil((count+1)/hop_space_2))*65535))],
                                      )
        try:
            self.controller_sw3.table_add("tb_insert_egress",
                                          f"index_egress{int(count%egress_space_2)}",
                                          [str(0),str(egress_space_2), str(count%egress_space_2), "0->"+str(int((1/math.ceil((count+1)/egress_space_2))*65535))],
                                          )
            ttl -= 1
            count += 1
        except:
            ttl -= 1
            count += 1       

        self.controller_sw4.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_1), str(count%q_space_1), "0->65535"],
                                      )
        self.controller_sw4.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_1), str(count%hop_space_1), "0->65535"],
                                      )
        self.controller_sw4.table_add("tb_insert_egress",
                                      "set_egress",
                                      [str(1),str(egress_space_1), str(count%egress_space_1), "0->65535"],
                                      )

        self.controller_sw4.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_2), str(count%q_space_2), "0->65535"],
                                      )
        self.controller_sw4.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_2), str(count%hop_space_2), "0->65535"],
                                      )
        try:
            self.controller_sw4.table_add("tb_insert_egress",
                                          "set_egress",
                                          [str(1),str(egress_space_2), str(count%egress_space_2), "0->65535"],
                                          )
        except:
            print("")

        self.controller_sw4.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_1)}",
                                      [str(0),str(q_space_1), str(count%q_space_1), "0->"+str(int((1/math.ceil((count+1)/q_space_1))*65535))],
                                      )
        self.controller_sw4.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_1)}",
                                      [str(0),str(hop_space_1), str(count%hop_space_1), "0->"+str(int((1/math.ceil((count+1)/hop_space_1))*65535))],
                                      )
        self.controller_sw4.table_add("tb_insert_egress",
                                      f"index_egress{int(count%egress_space_1)}",
                                      [str(0),str(egress_space_1), str(count%egress_space_1), "0->"+str(int((1/math.ceil((count+1)/egress_space_1))*65535))],
                                      )

        self.controller_sw4.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_2)}",
                                      [str(0),str(q_space_2), str(count%q_space_2), "0->"+str(int((1/math.ceil((count+1)/q_space_2))*65535))],
                                      )
        self.controller_sw4.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_2)}",
                                      [str(0),str(hop_space_2), str(count%hop_space_2), "0->"+str(int((1/math.ceil((count+1)/hop_space_2))*65535))],
                                      )
        try:
            self.controller_sw4.table_add("tb_insert_egress",
                                          f"index_egress{int(count%egress_space_2)}",
                                          [str(0),str(egress_space_2), str(count%egress_space_2), "0->"+str(int((1/math.ceil((count+1)/egress_space_2))*65535))],
                                          )
            ttl -= 1
            count += 1
        except:
            ttl -= 1
            count += 1   

        self.controller_sw5.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_1), str(count%q_space_1), "0->65535"],
                                      )
        self.controller_sw5.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_1), str(count%hop_space_1), "0->65535"],
                                      )
        self.controller_sw5.table_add("tb_insert_egress",
                                      "set_egress",
                                      [str(1),str(egress_space_1), str(count%egress_space_1), "0->65535"],
                                      )

        self.controller_sw5.table_add("tb_insert_q",
                                      "set_q",
                                      [str(1),str(q_space_2), str(count%q_space_2), "0->65535"],
                                      )
        self.controller_sw5.table_add("tb_insert_hop",
                                      "set_hop",
                                      [str(1),str(hop_space_2), str(count%hop_space_2), "0->65535"],
                                      )
        try:
            self.controller_sw5.table_add("tb_insert_egress",
                                          "set_egress",
                                          [str(1),str(egress_space_2), str(count%egress_space_2), "0->65535"],
                                          )
        except:
            print("")

        self.controller_sw5.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_1)}",
                                      [str(0),str(q_space_1), str(count%q_space_1), "0->"+str(int((1/math.ceil((count+1)/q_space_1))*65535))],
                                      )
        self.controller_sw5.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_1)}",
                                      [str(0),str(hop_space_1), str(count%hop_space_1), "0->"+str(int((1/math.ceil((count+1)/hop_space_1))*65535))],
                                      )
        self.controller_sw5.table_add("tb_insert_egress",
                                      f"index_egress{int(count%egress_space_1)}",
                                      [str(0),str(egress_space_1), str(count%egress_space_1), "0->"+str(int((1/math.ceil((count+1)/egress_space_1))*65535))],
                                      )

        self.controller_sw5.table_add("tb_insert_q",
                                      f"index_q{int(count%q_space_2)}",
                                      [str(0),str(q_space_2), str(count%q_space_2), "0->"+str(int((1/math.ceil((count+1)/q_space_2))*65535))],
                                      )
        self.controller_sw5.table_add("tb_insert_hop",
                                      f"index_hop{int(count%hop_space_2)}",
                                      [str(0),str(hop_space_2), str(count%hop_space_2), "0->"+str(int((1/math.ceil((count+1)/hop_space_2))*65535))],
                                      )
        try:
            self.controller_sw5.table_add("tb_insert_egress",
                                          f"index_egress{int(count%egress_space_2)}",
                                          [str(0),str(egress_space_2), str(count%egress_space_2), "0->"+str(int((1/math.ceil((count+1)/egress_space_2))*65535))],
                                          )
            ttl -= 1
            count += 1
        except:
            ttl -= 1
            count += 1   
        

################################################################################################
##########                                    Main                                    ##########
################################################################################################

if __name__ == "__main__":
    controller = Controller()
   
    controller.set_source_node()
    controller.routing_table()
    controller.set_switch_id()
    controller.valid_space()
    controller.set_space()
    controller.set_param()
    controller.insert_int()

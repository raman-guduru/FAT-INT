action set_param(bit<8> remainder_q, bit<8> remainder_hop, bit<8> remainder_egress) {
	meta.remainder_q = remainder_q;
	meta.remainder_hop = remainder_hop;
	meta.remainder_egress = remainder_egress;
}

action set_q(){
	hdr.fat_int_q[0].q_id = 0;
	hdr.fat_int_q[0].q_occupancy = (bit<24>) standard_metadata.deq_qdepth;
	hdr.fat_int_q[0].switch_id = (bit<8>) meta.switch_id;
}

action set_hop(){
	hdr.fat_int_hop[0].hop_latency = (bit<32>) standard_metadata.egress_global_timestamp - (bit<32>) standard_metadata.ingress_global_timestamp;
	hdr.fat_int_hop[0].switch_id = (bit<8>) meta.switch_id;
}

action set_egress(){
	hdr.fat_int_egress[0].egress_timestamp = (bit<32>)standard_metadata.egress_global_timestamp;
	hdr.fat_int_egress[0].switch_id = (bit<8>) meta.switch_id;
}


#define INDEX_Q(i)\
action index_q##i##(){\
	hdr.fat_int_q[##i##].q_id = 0;\
	hdr.fat_int_q[##i##].q_occupancy = (bit<24>) standard_metadata.deq_qdepth;\
	hdr.fat_int_q[##i##].switch_id = (bit<8>) meta.switch_id;\
}\

#define INDEX_HOP(i)\
action index_hop##i##(){\
	hdr.fat_int_hop[##i##].hop_latency = (bit<32>) standard_metadata.egress_global_timestamp - (bit<32>) standard_metadata.ingress_global_timestamp;\
	hdr.fat_int_hop[##i##].switch_id = (bit<8>) meta.switch_id;\
}\

#define INDEX_EGRESS(i)\
action index_egress##i##(){\
	hdr.fat_int_egress[##i##].egress_timestamp = (bit<32>)standard_metadata.egress_global_timestamp;\
	hdr.fat_int_egress[##i##].switch_id = (bit<8>) meta.switch_id;\
}\

INDEX_Q(0)
INDEX_Q(1)
INDEX_Q(2)
INDEX_Q(3)
INDEX_Q(4)
INDEX_Q(5)
INDEX_Q(6)
INDEX_Q(7)
INDEX_Q(8)

INDEX_HOP(0)
INDEX_HOP(1)
INDEX_HOP(2)
INDEX_HOP(3)
INDEX_HOP(4)
INDEX_HOP(5)
INDEX_HOP(6)
INDEX_HOP(7)
INDEX_HOP(8)

INDEX_EGRESS(0)
INDEX_EGRESS(1)
INDEX_EGRESS(2)
INDEX_EGRESS(3)
INDEX_EGRESS(4)
INDEX_EGRESS(5)
INDEX_EGRESS(6)
INDEX_EGRESS(7)
INDEX_EGRESS(8)
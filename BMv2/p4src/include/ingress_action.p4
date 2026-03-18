action int_set_source () {
	meta.source = 1;
}	

action set_egress_port(bit<9> port) {
	standard_metadata.egress_spec = port;
	hdr.ipv4.ttl=hdr.ipv4.ttl-1;
}

action set_switch_id(bit<8> switch_id){
	meta.switch_id = switch_id;
}

action valid_space(bit<8> case) {
	hdr.fat_int_case.setValid();
	hdr.fat_int_space.setValid();
	hdr.fat_int_case.case = case;
	hdr.ipv4.dscp = INT;
}

action set_space(bit<8> queue_space, bit<8> hop_space, bit<8> egress_space){
	meta.sampling_space_q = queue_space;
	meta.sampling_space_hop = hop_space;
	meta.sampling_space_egress_tst = egress_space;
}

action adding_space_q (){
	hdr.fat_int_space.queue_space = hdr.fat_int_space.queue_space + 1;
}

action adding_space_hop (){
	hdr.fat_int_space.hop_space = hdr.fat_int_space.hop_space + 1;
}

action adding_space_egress (){
	hdr.fat_int_space.egress_space = hdr.fat_int_space.egress_space + 1;
}

action valid_space_q(){
	hdr.fat_int_q.push_front(1);
	hdr.fat_int_q[0].setValid();
	meta.count_q = 1;
}

action valid_space_hop(){
	hdr.fat_int_hop.push_front(1);
	hdr.fat_int_hop[0].setValid();
	meta.count_hop = 1;
}

action valid_space_egress(){
	hdr.fat_int_egress.push_front(1);
	hdr.fat_int_egress[0].setValid();
	meta.count_egress = 1;
}
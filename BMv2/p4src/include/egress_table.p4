table tb_set_param {
	key={
		hdr.ipv4.ttl : exact;
		meta.sampling_space_q : exact;
		meta.sampling_space_hop : exact;
		meta.sampling_space_egress_tst : exact;
	}
	actions={
		set_param;
		NoAction();
	}
	default_action=NoAction();
}

table tb_insert_q{
	key = {
		meta.count_q: exact;
		meta.sampling_space_q: exact;
		meta.remainder_q : exact;	
		meta.global_hash1 : range;
	}
	actions = {
		set_q;
		index_q0;
		index_q1;
		index_q2;
		index_q3;
		index_q4;
		index_q5;
		index_q6;
		index_q7;
		index_q8;
		NoAction();
	}
	default_action=NoAction();
}

table tb_insert_hop{
	key = {
		meta.count_hop: exact;
		meta.sampling_space_hop: exact;
		meta.remainder_hop : exact;
		meta.global_hash1 : range;
	}
	actions={
		set_hop;
		index_hop0;
		index_hop1;
		index_hop2;
		index_hop3;
		index_hop4;
		index_hop5;
		index_hop6;
		index_hop7;
		index_hop8;
		NoAction();
	}
	default_action=NoAction();
}

table tb_insert_egress{
	key={
		meta.count_egress: exact;
		meta.sampling_space_egress_tst: exact;
		meta.remainder_egress : exact;	
		meta.global_hash1 : range;
	}
	actions={
		set_egress;
		index_egress0;
		index_egress1;
		index_egress2;
		index_egress3;
		index_egress4;
		index_egress5;
		index_egress6;
		index_egress7;
		index_egress8;
		NoAction();
	}
	default_action=NoAction();
}
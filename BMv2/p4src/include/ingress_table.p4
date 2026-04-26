table tb_set_source {
	key = {
		hdr.ipv4.dscp : exact;
	}
	actions = {
		int_set_source;
		NoAction();
	}
	default_action = NoAction();
	size = 1;
}

table tb_valid_space {
	key = {
		meta.source: exact;
		meta.global_hash1 : range;
	}
	actions = {
		valid_space();
		NoAction();
 	}
	default_action = NoAction();
	size = 2;
}

table tb_set_switch_id {
	key = {
		hdr.ipv4.version : exact;
	}
	actions = {
		set_switch_id;
		NoAction();
	}
	default_action = NoAction();
	size = 1;
}

table tb_set_space {
	key = {
		hdr.fat_int_case.case : exact;
	}
	actions = {
		set_space();
		NoAction();
	}
	const default_action = NoAction();
}

table tb_valid_space_q {
	actions = {
		valid_space_q;
	}
	const default_action = valid_space_q();
}

table tb_valid_space_hop {
	actions = {
		valid_space_hop;
	}
	const default_action = valid_space_hop();
}

table tb_valid_space_egress {
	actions = {
		valid_space_egress;
	}
	const default_action = valid_space_egress();
}

table tb_forward {
	key = {
		hdr.ipv4.dstAddr: exact;
	}
	actions = {
		set_egress_port;
		NoAction();
	}
	const default_action = NoAction();
}

// Table A: Maps a Destination IP to an ECMP Group
table tb_ecmp_group {
    key = {
        hdr.ipv4.dstAddr : exact;
    }
    actions = {
        set_ecmp_group;
        NoAction;
    }
    size = 1024;
}

// Table B: Maps the (Group ID + Calculated Hash Index) to a physical port
table tb_ecmp_nhop {
    key = {
        meta.ecmp_group_id : exact;
        meta.ecmp_index : exact;
    }
    actions = {
        set_egress_port;
        NoAction;
    }
    size = 1024;
}
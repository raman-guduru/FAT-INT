/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#define INT 20
const bit<16> TYPE_IPV4 = 0x800;

#include "include/header.p4"
#include "include/parser.p4"

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
		apply {  }
}

control MyIngress(inout headers hdr,
		  inout metadata meta,
		  inout standard_metadata_t standard_metadata) {

	#include "include/ingress_action.p4"
	#include "include/ingress_table.p4"

	apply {
		tb_set_source.apply();
		hash(meta.global_hash1, HashAlgorithm.crc32, (bit<1>)0, {hdr.ipv4.srcAddr,
									 hdr.ipv4.dstAddr,
									 hdr.ipv4.protocol,
									 hdr.ipv4.identification,
									 hdr.tcp.srcPort,
									 hdr.tcp.dstPort,
									 hdr.ipv4.ttl},
		  						         (bit<16>)65535);
		tb_valid_space.apply();	
		if (hdr.fat_int_space.isValid()){
			tb_set_switch_id.apply();
			tb_set_space.apply();
			if (meta.sampling_space_q != (hdr.fat_int_space.queue_space)){
				tb_valid_space_q.apply();
				adding_space_q();
			}
			if (meta.sampling_space_hop != (hdr.fat_int_space.hop_space)){
				tb_valid_space_hop.apply();	
				adding_space_hop();
			}
			if (meta.sampling_space_egress_tst != (hdr.fat_int_space.egress_space)){
				tb_valid_space_egress.apply();	
				adding_space_egress();
			}
		}
		tb_forward.apply();
	}
}

control MyEgress(inout headers hdr,
	 	 inout metadata meta,
	 	 inout standard_metadata_t standard_metadata) {
		
	#include "include/egress_action.p4"
	#include "include/egress_table.p4"

	apply {	
		if (hdr.fat_int_space.isValid()){
			tb_set_param.apply(); 

			tb_insert_q.apply();
			tb_insert_hop.apply();
			tb_insert_egress.apply();
		}
	}
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
		apply {

		}
}

V1Switch(
		MyParser(),
		MyVerifyChecksum(),
		MyIngress(),
		MyEgress(),
		MyComputeChecksum(),
		MyDeparser()
) main;

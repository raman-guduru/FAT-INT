typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
		macAddr_t dstAddr;
		macAddr_t srcAddr;
		bit<16>   etherType;
}

header ipv4_t {
		bit<4>    version;
		bit<4>    ihl;
        bit<8>    dscp;
		bit<16>   totalLen;
		bit<16>   identification;
		bit<3>    flags;
		bit<13>   fragOffset;
		bit<8>    ttl;
		bit<8>    protocol;
		bit<16>   hdrChecksum;
		ip4Addr_t srcAddr;
		ip4Addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header fat_int_case_t{
	bit<8> case;
}

header fat_int_space_t{
	bit<8> queue_space;
	bit<8> hop_space;
	bit<8> egress_space;
}

header fat_int_q_occupancy_t {
	bit<8> q_id;
	bit<24> q_occupancy;
	bit<8> switch_id;
}

header fat_int_hop_latency_t {
	bit<32> hop_latency;
	bit<8> switch_id;
}

header fat_int_egress_timestamp_t {
	bit<32> egress_timestamp;
	bit<8> switch_id;
} 

struct headers {
	ethernet_t  					ethernet;
	ipv4_t      					ipv4;
	tcp_t       					tcp;

	fat_int_case_t	 				fat_int_case;
	fat_int_space_t 				fat_int_space;
	fat_int_q_occupancy_t[9] 		fat_int_q;
	fat_int_hop_latency_t[9] 		fat_int_hop;
	fat_int_egress_timestamp_t[9] 	fat_int_egress;
}

struct metadata {
		bit<8> switch_id;	
		bit<8> sampling_space_q;
		bit<8> sampling_space_hop;
		bit<8> sampling_space_egress_tst;

		bit<16> global_hash1;

		bit<8> space_q;
		bit<8> space_hop;
		bit<8> space_egress;

		bit<8> remainder_q;
		bit<8> remainder_hop;
		bit<8> remainder_egress;

		bit<8> remain_q;
		bit<8> remain_hop;
		bit<8> remain_egress;

		bit<1>  source;
		bit<1> count_q;
		bit<1> count_hop;
		bit<1> count_egress;
}


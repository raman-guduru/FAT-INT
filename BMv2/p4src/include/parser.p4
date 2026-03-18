parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        packet.extract(hdr.ipv4);
        packet.extract(hdr.tcp);
        transition select (hdr.ipv4.dscp){
            INT: fat_int;
            default: accept;
        }
    }

    state fat_int {
        packet.extract(hdr.fat_int_case);
        packet.extract(hdr.fat_int_space);
        meta.remain_q = hdr.fat_int_space.queue_space;
        meta.remain_hop = hdr.fat_int_space.hop_space;
        meta.remain_egress = hdr.fat_int_space.egress_space;
        transition select (hdr.fat_int_space.queue_space){
            0 : fat_int_hop;
            default : parse_queue;

        }
    }

    state parse_queue{
        packet.extract(hdr.fat_int_q.next);
        meta.remain_q = meta.remain_q -1;
        transition select(meta.remain_q){
            0 : fat_int_hop;
            default : parse_queue;
        }
    }

    state fat_int_hop{
        transition select (hdr.fat_int_space.hop_space){
            0 : fat_int_egress;
            default : parse_hop;
        }
    }

    state parse_hop{
        packet.extract(hdr.fat_int_hop.next);
        meta.remain_hop = meta.remain_hop-1;
        transition select(meta.remain_hop){
            0 : fat_int_egress;
            default : parse_hop;
        }
    }

    state fat_int_egress{
        transition select (hdr.fat_int_space.egress_space){
            0 : accept;
            default : parse_egress;
        }
    }

    state parse_egress{
        packet.extract(hdr.fat_int_egress.next);
        meta.remain_egress = meta.remain_egress-1;
        transition select(meta.remain_egress){
            0 : accept;
            default : parse_hop;
        }
    }   
}

control MyDeparser(packet_out packet, 
                   in headers hdr) {
		apply {
				packet.emit(hdr.ethernet);
				packet.emit(hdr.ipv4);
                packet.emit(hdr.tcp);
                packet.emit(hdr.fat_int_case);
				packet.emit(hdr.fat_int_space);
				packet.emit(hdr.fat_int_q);
				packet.emit(hdr.fat_int_hop);
				packet.emit(hdr.fat_int_egress);
		}
}

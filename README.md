# Network Security: DNS Cache Poisoning & DNSSEC

![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![BIND9](https://img.shields.io/badge/BIND9-4A90E2?style=for-the-badge&logo=linux&logoColor=white)
![Wazuh](https://img.shields.io/badge/Wazuh-005E8C?style=for-the-badge&logo=security&logoColor=white)
![Kali Linux](https://img.shields.io/badge/Kali_Linux-557C94?style=for-the-badge&logo=kali-linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

Questo repository contiene l'elaborato progettuale per l'esame di **Network Security**.  
Il progetto analizza e mitiga le vulnerabilità intrinseche del protocollo DNS, dimostrando come un'architettura inizialmente basata sulla fiducia implicita possa essere compromessa (tramite DNS Cache/Zone Poisoning) e, successivamente, blindata in un ecosistema *Zero-Trust* resiliente.

## Descrizione del Progetto

Il progetto è suddiviso in tre fasi operative implementate in un ambiente interamente containerizzato:

1. **Offensive (Red Team):** sfruttamento dell'assenza di autenticazione nei *Dynamic DNS Updates* per iniettare record malevoli nel Master Server e avvelenare la cache del Resolver di frontiera (usando Kali Linux e Scapy).
2. **Defensive (Blue Team / Hardening):** implementazione di un approccio *Defense-in-Depth* tramite firme crittografiche **TSIG** (Transaction Signature) per le comunicazioni server-to-server e **DNSSEC** (*Inline-Signing* con ECDSA P-256) per garantire l'integrità dei dati ai client finali.
3. **Monitoring (SOC/SIEM):** integrazione *agentless* di **Wazuh** per l'analisi dei log applicativi di BIND9, regole custom di *Threat Hunting* e mantenimento di un *Audit Trail* delle operazioni amministrative.

> **Nota:** La documentazione completa (teoria, setup, comandi e analisi forense tramite Wireshark) è disponibile nel file `documentazione_ns.pdf` incluso in questa repository.

## Struttura della Repository

```text
Root
┣ progetto-ns/              # Root dell'ambiente Docker
┃ ┣ attacker_scripts/       # Script Python (Scapy) per l'attacco di Poisoning
┃ ┣ bind/                   # Configurazioni e file di zona per il Master DNS
┃ ┣ html_clone/             # Pagine web fittizie per l'attacco di Masquerade
┃ ┣ resolver/               # Configurazioni per il DNS Resolver (Frontiera)
┃ ┣ wazuh/                  # File di configurazione e log condivisi per il SIEM
┃ ┗ docker-compose.yml      # Descrittore per l'orchestrazione dei container
┣ documentazione_ns.pdf     # Elaborato e report tecnico completo
┗ README.md
```

## Quick Start

### Prerequisiti

- Docker e Docker Compose installati  
  (su Windows è consigliato Docker Desktop con backend WSL2).
- Almeno **10 GB di RAM** libera dedicata a Docker per lo stack Elasticsearch/OpenSearch di Wazuh.

### Avvio dell'ambiente

1. Clona la repository:
   ```bash
   git clone https://github.com/NS-Projects-Unina/CachePoisoning_DNSSEC.git
   ```
2. Entra nella cartella del progetto:
   ```bash
   cd progetto-ns
   ```
3. Avvia l'infrastruttura in background:
   ```bash
   docker compose up -d
   ```

Attendi qualche minuto affinché i container Wazuh completino il bootstrap.  
La dashboard è raggiungibile su `https://localhost:443` (ignora l'avviso SSL autofirmato).

> Tutti i comandi per replicare l'attacco, testare le vulnerabilità ed eseguire l'hardening sono documentati nel PDF allegato.

---

## Troubleshooting: Conflitti SSL/TLS (Wazuh)

Come documentato nell'elaborato (Capitolo 1.4.4), durante il primo avvio o in caso di riavvii forzati, lo stack Wazuh può entrare in loop di errori legati ai certificati SSL autofirmati o ai plugin di sicurezza OpenSearch (`bad certificate`, `NotSslRecordException`).

Se la dashboard non è raggiungibile o i log non vengono indicizzati, esegui questi passaggi.

### 1) Hard reset dell'ambiente (opzionale ma consigliato)

```bash
docker compose down -v
# Se necessario, svuota anche le directory dei volumi (es. /wazuh/config)
docker compose up -d
```

### 2) Inizializzazione e disattivazione Security Plugin (Indexer)

```bash
# Inizializza i certificati di base
docker exec -u 0 -it wazuh_indexer /bin/bash -c "chmod +x /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh && export JAVA_HOME=/usr/share/wazuh-indexer/jdk && /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh -cd /usr/share/wazuh-indexer/opensearch-security/ -nhnv -cacert /usr/share/wazuh-indexer/certs/root-ca.pem -cert /usr/share/wazuh-indexer/certs/admin.pem -key /usr/share/wazuh-indexer/certs/admin-key.pem -h 10.0.1.11"

# Disabilita il plugin di sicurezza
docker exec -u 0 -it wazuh_indexer bash -c "echo -e 'network.host: 0.0.0.0\ndiscovery.type: single-node\nplugins.security.disabled: true' > /usr/share/wazuh-indexer/opensearch.yml"

docker compose restart wazuh_indexer
```

### 3) Fix compatibilità + HTTP sul Manager (Filebeat)

```bash
# Workaround compatibilità versioni
docker exec -it wazuh_manager curl -XPUT -u admin:admin -k "https://10.0.1.11:9200/_cluster/settings" -H "Content-Type: application/json" -d "{\"persistent\": {\"compatibility.override_main_response_version\": true}}"

# Passa da HTTPS a HTTP in Filebeat
docker exec -it wazuh_manager bash -c "sed -i 's|https://10.0.1.11:9200|http://10.0.1.11:9200|g' /etc/filebeat/filebeat.yml && service filebeat restart"
```

### 4) Riconfigurazione Dashboard (OpenSearch & API)

```bash
# Disabilita la verifica SSL lato Dashboard verso l'Indexer
docker exec -u 0 -it wazuh_dashboard bash -c "echo -e 'server.host: \"0.0.0.0\"\nopensearch.hosts: [\"http://10.0.1.11:9200\"]\nopensearch.ssl.verificationMode: none\nopensearch_security.enabled: false\nuiSettings.overrides.defaultRoute: /app/wazuh' > /usr/share/wazuh-dashboard/config/opensearch_dashboards.yml"

# Configura la connessione all'API Wazuh Manager ignorando i check SSL
docker exec -u 0 -it wazuh_dashboard bash -c "echo -e 'hosts:\n  - default:\n      url: https://10.0.1.10\n      port: 55000\n      username: wazuh\n      password: wazuh\n      insecure: true' > /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml"

docker compose restart wazuh_dashboard
```

### Errore “Duplicate Key” sulla Dashboard

Se la UI restituisce un errore di chiavi duplicate in `wazuh.yml`, rigenera il file:

```bash
docker exec -u 0 -it wazuh_dashboard bash -c "rm -f /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml && echo -e 'hosts:\n  - default:\n      url: http://10.0.1.10\n      port: 55000\n      username: wazuh\n      password: wazuh' > /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml"
docker compose restart wazuh_dashboard
```

---

## Disclaimer Etico (Ethical Hacking)

Questa repository e gli script in essa contenuti sono stati sviluppati esclusivamente per scopi didattici e di ricerca accademica nell'ambito dell'esame di Network Security. Le tecniche descritte dimostrano come identificare e mitigare vulnerabilità infrastrutturali. L'autore declina ogni responsabilità per l'uso improprio o illegale di tali informazioni al di fuori di ambienti di laboratorio isolati e preventivamente autorizzati.

**Autore:** Pasquale Paolo Silvenni (Matricola: M63001717)

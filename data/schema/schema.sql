-- Election Results Database Schema
-- This schema stores election results by circonscription and candidate

-- Main results table
CREATE TABLE IF NOT EXISTS election_results (
    id INTEGER PRIMARY KEY,
    
    -- Circonscription information
    region VARCHAR,
    region_normalise VARCHAR,
    circonscription_num VARCHAR,
    circonscription_name TEXT,
    
    -- Voting statistics
    nb_bureaux INTEGER,
    inscrits INTEGER,
    votants INTEGER,
    taux_participation DECIMAL(5,2),
    bulletins_nuls INTEGER,
    suffrages_exprimes INTEGER,
    bulletins_blancs_nombre INTEGER,
    bulletins_blancs_pourcentage DECIMAL(5,2),
    
    -- Candidate information
    parti VARCHAR,
    parti_normalise VARCHAR,
    candidat VARCHAR,
    candidat_normalise VARCHAR,
    voix INTEGER,
    pourcentage_voix DECIMAL(5,2),
    elu BOOLEAN,
    
    -- ✅ NOUVEAU: Provenance (PDF citations)
    source_page INTEGER,
    table_id VARCHAR(50),
    row_id INTEGER
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_circonscription ON election_results(circonscription_num);
CREATE INDEX IF NOT EXISTS idx_parti ON election_results(parti_normalise);
CREATE INDEX IF NOT EXISTS idx_region ON election_results(region_normalise);
CREATE INDEX IF NOT EXISTS idx_elu ON election_results(elu);
CREATE INDEX IF NOT EXISTS idx_candidat ON election_results(candidat_normalise);
CREATE INDEX IF NOT EXISTS idx_source_page ON election_results(source_page);  -- ✅ NOUVEAU

-- View: Winners by circonscription
CREATE OR REPLACE VIEW vw_winners AS
SELECT 
    circonscription_num,
    circonscription_name,
    region_normalise AS region,
    parti_normalise AS parti,
    candidat_normalise AS candidat,
    voix,
    pourcentage_voix,
    inscrits,
    votants,
    taux_participation
FROM election_results
WHERE elu = TRUE
ORDER BY circonscription_num;

-- View: Results by party
CREATE OR REPLACE VIEW vw_party_results AS
SELECT 
    parti_normalise AS parti,
    COUNT(*) AS total_candidats,
    SUM(CASE WHEN elu = TRUE THEN 1 ELSE 0 END) AS sieges,
    SUM(voix) AS total_voix,
    ROUND(AVG(pourcentage_voix), 2) AS pourcentage_moyen
FROM election_results
GROUP BY parti_normalise
ORDER BY sieges DESC, total_voix DESC;

-- View: Turnout by circonscription
CREATE OR REPLACE VIEW vw_turnout AS
SELECT 
    circonscription_num,
    circonscription_name,
    region_normalise AS region,
    MAX(inscrits) AS inscrits,
    MAX(votants) AS votants,
    MAX(taux_participation) AS taux_participation,
    MAX(bulletins_blancs_nombre) AS bulletins_blancs,
    MAX(bulletins_blancs_pourcentage) AS pourcentage_blancs
FROM election_results
GROUP BY circonscription_num, circonscription_name, region_normalise
ORDER BY taux_participation DESC;

-- View: Results by region
CREATE OR REPLACE VIEW vw_region_results AS
SELECT 
    region_normalise AS region,
    COUNT(DISTINCT circonscription_num) AS nb_circonscriptions,
    SUM(CASE WHEN elu = TRUE THEN 1 ELSE 0 END) AS nb_elus,
    SUM(DISTINCT inscrits) AS total_inscrits,
    SUM(DISTINCT votants) AS total_votants,
    ROUND(AVG(taux_participation), 2) AS taux_participation_moyen
FROM election_results
GROUP BY region_normalise
ORDER BY nb_circonscriptions DESC;

-- View: Close races (difference < 5%)
CREATE OR REPLACE VIEW vw_close_races AS
WITH ranked_results AS (
    SELECT 
        circonscription_num,
        circonscription_name,
        candidat_normalise,
        parti_normalise,
        pourcentage_voix,
        elu,
        ROW_NUMBER() OVER (PARTITION BY circonscription_num ORDER BY pourcentage_voix DESC) AS rank
    FROM election_results
)
SELECT 
    r1.circonscription_num,
    r1.circonscription_name,
    r1.candidat_normalise AS gagnant,
    r1.parti_normalise AS parti_gagnant,
    r1.pourcentage_voix AS pourcentage_gagnant,
    r2.candidat_normalise AS deuxieme,
    r2.parti_normalise AS parti_deuxieme,
    r2.pourcentage_voix AS pourcentage_deuxieme,
    ROUND(r1.pourcentage_voix - r2.pourcentage_voix, 2) AS ecart
FROM ranked_results r1
JOIN ranked_results r2 ON r1.circonscription_num = r2.circonscription_num
WHERE r1.rank = 1 AND r2.rank = 2
    AND (r1.pourcentage_voix - r2.pourcentage_voix) < 5.0
ORDER BY ecart ASC;
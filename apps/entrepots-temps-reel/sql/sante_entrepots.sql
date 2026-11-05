-- Vue lue par l'application « Entrepôts en temps réel » (connecteur fabric-sqlanalytics).
-- À créer dans le point de terminaison SQL du Lakehouse AmazingZoneLK. La table wms.evenements y est un raccourci
-- OneLake vers la copie Delta de la table KQL wms_evenements (disponibilité OneLake, délai d'écriture de 5 minutes).
-- Le connecteur n'accepte pas le point de terminaison SQL de la base KQL elle-même (élément « MirroredWarehouse »).
-- Le silence d'un entrepôt est mesuré par rapport au dernier événement copié, tous entrepôts confondus, et non à
-- l'heure courante : la copie a toujours quelques minutes de retard, qui ne doivent pas passer pour un silence.
CREATE OR ALTER VIEW api.sante_entrepots
AS
WITH copie AS (
    SELECT MAX(DateEvenement) AS DerniereCopie
    FROM wms.evenements
)
SELECT
    e.CodeEntrepot,
    MAX(e.DateEvenement) AS DernierEvenement,
    MAX(c.DerniereCopie) AS DerniereCopie,
    DATEDIFF(MINUTE, MAX(e.DateEvenement), MAX(c.DerniereCopie)) AS MinutesSansEvenement,
    CAST(CASE WHEN DATEDIFF(MINUTE, MAX(e.DateEvenement), MAX(c.DerniereCopie)) > 15 THEN 1 ELSE 0 END AS bit) AS EntrepotMuet,
    CAST(SUM(CASE WHEN e.DateEvenement > DATEADD(HOUR, -1, c.DerniereCopie) THEN 1 ELSE 0 END) AS int) AS EvenementsDerniereHeure,
    CAST(SUM(CASE WHEN e.DateEvenement > DATEADD(HOUR, -1, c.DerniereCopie) AND e.TypeEvenement = 'SHIPMENT' THEN 1 ELSE 0 END) AS int) AS ExpeditionsDerniereHeure
FROM wms.evenements AS e
CROSS JOIN copie AS c
WHERE e.CodeEntrepot IN ('WH1', 'WH2', 'WH3', 'WH4')
GROUP BY e.CodeEntrepot;

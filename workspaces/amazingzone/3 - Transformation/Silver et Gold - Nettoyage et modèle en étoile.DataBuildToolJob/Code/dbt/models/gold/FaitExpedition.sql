-- Expéditions, à la maille de la commande logistique du WMS.
WITH clients AS (
    SELECT DISTINCT numero_commande, client_id FROM {{ ref('commande_ligne') }}
)
SELECT CAST(w.numero_commande AS VARCHAR(20))       AS NumeroCommande,
       {{ date_id('w.date_prise_en_charge') }}      AS DatePriseEnChargeId,
       {{ date_id('w.date_expedition') }}           AS DateExpeditionId,
       COALESCE(e.EntrepotKey, -1)                  AS EntrepotKey,
       COALESCE(t.TransporteurKey, -1)              AS TransporteurKey,
       COALESCE(c.ClientKey, -1)                    AS ClientKey,
       CAST(w.statut_logistique AS VARCHAR(20))     AS StatutLogistique,
       w.nb_lignes                                  AS NbLignes,
       w.nb_articles                                AS NbArticles,
       CAST(DATEDIFF(MINUTE, w.date_prise_en_charge, w.date_expedition) / 60.0 AS DECIMAL(9, 2)) AS DelaiPreparationHeures,
       CAST(CASE WHEN w.date_expedition IS NULL THEN NULL
                 WHEN DATEDIFF(MINUTE, w.date_prise_en_charge, w.date_expedition) <= 1440 THEN 1 ELSE 0 END AS BIT) AS EstExpedieeSous24h,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))       AS DateChargement
FROM {{ ref('commande_logistique') }} AS w
LEFT JOIN {{ ref('DimEntrepot') }} AS e ON e.CodeEntrepot = w.code_entrepot
LEFT JOIN {{ ref('DimTransporteur') }} AS t ON t.Transporteur = w.transporteur
LEFT JOIN clients AS l ON l.numero_commande = w.numero_commande
LEFT JOIN {{ ref('DimClient') }} AS c ON c.ClientId = l.client_id

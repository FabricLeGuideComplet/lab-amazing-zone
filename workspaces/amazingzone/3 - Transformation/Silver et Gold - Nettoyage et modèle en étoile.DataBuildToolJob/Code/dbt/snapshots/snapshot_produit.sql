{# Historisation du catalogue (SCD de type 2) : dbt compare à chaque exécution le prix catalogue, la catégorie
   et l'univers de chaque produit à la dernière version enregistrée, clôture la version modifiée
   (dbt_valid_to) et en insère une nouvelle (dbt_valid_from). Le prix est historisé pour suivre l'évolution
   du catalogue ; le chiffre d'affaires, lui, vient toujours du prix porté par la ligne de commande.
   Le nœud porte un nom distinct du modèle Silver produit ; sa table reste snapshots.produit. #}
{% snapshot snapshot_produit %}
{{
    config(
        alias='produit',
        unique_key='produit_id',
        strategy='check',
        check_cols=['prix_vente', 'categorie', 'univers'],
    )
}}
SELECT produit_id, sku, produit, univers, categorie, prix_vente, cout_achat
FROM {{ ref('produit') }}
{% endsnapshot %}

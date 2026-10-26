-- Catalogue du site e-commerce : produit, catégorie principale, univers, prix catalogue et coût d'achat.
WITH categorie_principale AS (
    SELECT ProductId, MIN(CategoryId) AS CategoryId
    FROM {{ source('ecommerce', 'Product_Category_Mapping') }}
    GROUP BY ProductId
)
SELECT p.Id                                    AS produit_id,
       CAST(p.Sku AS VARCHAR(50))              AS sku,
       p.Name                                  AS produit,
       COALESCE(parent.Name, cat.Name)         AS univers,
       cat.Name                                AS categorie,
       CAST(p.Price AS DECIMAL(18, 2))         AS prix_vente,
       CAST(p.ProductCost AS DECIMAL(18, 2))   AS cout_achat,
       p.Published                             AS publie
FROM {{ source('ecommerce', 'Product') }} AS p
LEFT JOIN categorie_principale AS m ON m.ProductId = p.Id
LEFT JOIN {{ source('ecommerce', 'Category') }} AS cat    ON cat.Id = m.CategoryId
LEFT JOIN {{ source('ecommerce', 'Category') }} AS parent ON parent.Id = cat.ParentCategoryId AND cat.ParentCategoryId > 0
WHERE p.Deleted = 0

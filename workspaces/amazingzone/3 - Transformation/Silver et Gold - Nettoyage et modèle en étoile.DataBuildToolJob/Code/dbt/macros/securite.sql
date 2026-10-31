{# Sécurité du Warehouse pour les accès SQL directs (le modèle sémantique, en Direct Lake sur OneLake, lit les
   fichiers et applique sa propre sécurité).
   Une politique de sécurité liée au schéma (SCHEMABINDING) interdit de renommer ou de supprimer les tables
   qu'elle protège : dbt ne pourrait plus les reconstruire. La politique et sa fonction sont donc retirées en
   début d'exécution (on-run-start) et recréées en fin d'exécution (on-run-end), ainsi que les droits posés
   sur des tables, perdus à chaque reconstruction. Pendant l'exécution, la sécurité est donc levée : les faits
   ne sont pas filtrés et la colonne Email de gold.DimClient est lisible par lecteurs_gold (le GRANT sur le
   schéma demeure, le DENY posé sur la table disparaît avec elle). Si une instruction de fin d'exécution échoue,
   la sécurité n'est rétablie qu'à la prochaine exécution réussie : l'échec du job doit être surveillé. #}

{% macro securite_retirer() -%}
IF EXISTS (SELECT 1 FROM sys.security_policies WHERE name = 'politique_entrepot')
    DROP SECURITY POLICY securite.politique_entrepot;
IF OBJECT_ID('securite.fn_acces_entrepot') IS NOT NULL
    DROP FUNCTION securite.fn_acces_entrepot;
{%- endmacro %}

{# Un administrateur de l'espace n'échappe pas à la sécurité T-SQL : sans le rôle acces_tous_entrepots, le
   principal de service qui exécute dbt ne verrait aucune ligne. #}
{% macro securite_fonction() -%}
CREATE FUNCTION securite.fn_acces_entrepot(@EntrepotKey BIGINT)
RETURNS TABLE
WITH SCHEMABINDING
AS RETURN
    SELECT 1 AS acces
    WHERE IS_MEMBER('acces_tous_entrepots') = 1
       OR EXISTS (SELECT 1
                  FROM securite.AccesEntrepot AS a
                  WHERE a.EntrepotKey = @EntrepotKey
                    AND a.Utilisateur = USER_NAME())
{%- endmacro %}

{% macro securite_politique() -%}
CREATE SECURITY POLICY securite.politique_entrepot
    ADD FILTER PREDICATE securite.fn_acces_entrepot(EntrepotKey) ON gold.FaitVente,
    ADD FILTER PREDICATE securite.fn_acces_entrepot(EntrepotKey) ON gold.FaitExpedition,
    ADD FILTER PREDICATE securite.fn_acces_entrepot(EntrepotKey) ON gold.FaitStockJour,
    ADD FILTER PREDICATE securite.fn_acces_entrepot(EntrepotKey) ON gold.FaitMeteoJour
    WITH (STATE = ON)
{%- endmacro %}

{# Rôles et droits. lecteurs_gold : lecture du Gold sans l'adresse e-mail des clients (sécurité au niveau des
   colonnes) ; ses membres sont les utilisateurs de la table de correspondance. acces_tous_entrepots : identités
   qui voient tous les entrepôts (variable securite_acces_complet). Les membres retirés de la correspondance
   ne sont pas retirés des rôles : à faire à la main. #}
{% macro securite_roles() -%}
{%- set membres = [] -%}
{%- if execute -%}
    {%- set resultat = run_query("SELECT DISTINCT Utilisateur FROM securite.AccesEntrepot") -%}
    {%- set membres = resultat.columns[0].values() -%}
{%- endif -%}
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'lecteurs_gold' AND type = 'R')
    CREATE ROLE lecteurs_gold;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'acces_tous_entrepots' AND type = 'R')
    CREATE ROLE acces_tous_entrepots;
GRANT SELECT ON SCHEMA::gold TO lecteurs_gold;
DENY SELECT ON gold.DimClient(Email) TO lecteurs_gold;
{% for m in membres -%}
{{ securite_ajouter_membre('lecteurs_gold', m) }}
{% endfor -%}
{% for m in var('securite_acces_complet', []) -%}
{{ securite_ajouter_membre('acces_tous_entrepots', m) }}
{% endfor -%}
{%- endmacro %}

{% macro securite_ajouter_membre(role, membre) -%}
IF NOT EXISTS (SELECT 1
               FROM sys.database_role_members AS rm
               JOIN sys.database_principals AS r ON r.principal_id = rm.role_principal_id
               JOIN sys.database_principals AS m ON m.principal_id = rm.member_principal_id
               WHERE r.name = '{{ role }}' AND m.name = '{{ membre }}')
    ALTER ROLE {{ role }} ADD MEMBER [{{ membre }}];
{%- endmacro %}

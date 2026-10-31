/* {"app": "dbt", "dbt_version": "1.11.8", "profile_name": "dbtexecutorprofile", "target_name": "dev", "connection_name": "master"} */
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

GO
CREATE SECURITY POLICY [securite].[politique_entrepot]
    ADD FILTER PREDICATE [securite].[fn_acces_entrepot]([EntrepotKey]) ON [gold].[FaitVente],
    ADD FILTER PREDICATE [securite].[fn_acces_entrepot]([EntrepotKey]) ON [gold].[FaitExpedition],
    ADD FILTER PREDICATE [securite].[fn_acces_entrepot]([EntrepotKey]) ON [gold].[FaitStockJour],
    ADD FILTER PREDICATE [securite].[fn_acces_entrepot]([EntrepotKey]) ON [gold].[FaitMeteoJour]
    WITH (STATE = ON);


GO
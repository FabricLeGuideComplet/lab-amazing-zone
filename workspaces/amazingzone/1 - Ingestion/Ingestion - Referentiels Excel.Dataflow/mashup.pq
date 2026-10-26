[StagingDefinition = [Kind = "FastCopy"]]
section Section1;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "taux_change_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared taux_change = let
  Source = Excel.Workbook(Web.Contents("https://mariietardygmail.sharepoint.com/sites/Finance/Documents partages/Taux de change/taux_de_change_vs_eur_2019_2026.xlsx"), null, true),
  #"Navigation 1" = Source{[Item = "Taux de change vs EUR", Kind = "Sheet"]}[Data],
  #"Changed column type" = Table.TransformColumnTypes(#"Navigation 1", {{"Column1", type text}, {"Column2", type text}, {"Column3", type text}, {"Column4", type text}, {"Column5", type number}, {"Column6", type number}, {"Column7", type number}, {"Column8", type number}, {"Column9", type number}, {"Column10", type number}, {"Column11", type number}, {"Column12", type number}}),
  #"Promoted headers" = Table.PromoteHeaders(#"Changed column type", [PromoteAllScalars = true]),
  #"Unpivoted other columns" = Table.UnpivotOtherColumns(#"Promoted headers", {"Code ISO-3", "Pays", "Code devise", "Devise"}, "Attribute", "Value"),
  #"Renamed columns" = Table.RenameColumns(#"Unpivoted other columns", {{"Attribute", "Annee"}, {"Value", "TauxChange"}}),
  #"Removed columns" = Table.RemoveColumns(#"Renamed columns", {"Pays", "Devise"}),
  #"Changed column type 1" = Table.TransformColumnTypes(#"Removed columns", {{"Annee", Int64.Type}})
in
  #"Changed column type 1";
shared taux_change_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true]),
  Navigation_1 = Pattern{[workspaceId = "0875373d-96cd-4d0e-b4e7-5fc5cd327cb8"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6523eec-e450-401b-a672-cebe8d1ef2af"]}[Data],
  Navigation_3 = Navigation_2{[Id = "referentiels", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "taux_change", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "geographie_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared geographie = let
  Source = Excel.Workbook(Web.Contents("https://mariietardygmail.sharepoint.com/sites/Finance/Documents partages/Referentiels/referentiel_geographique.xlsx"), null, true),
  #"Navigation 1" = Source{[Item = "Départements", Kind = "Sheet"]}[Data],
  #"Promoted headers" = Table.PromoteHeaders(#"Navigation 1", [PromoteAllScalars = true]),
  #"Changed column type" = Table.TransformColumnTypes(#"Promoted headers", {{"code_departement", type text}, {"departement", type text}, {"chef_lieu_departement", type text}, {"code_region", type text}, {"region", type text}, {"chef_lieu_region", type text}, {"outre_mer", type text}}),
  #"Filtered rows" = Table.SelectRows(#"Changed column type", each [code_departement] <> null and [code_departement] <> "")
in
  #"Filtered rows";
shared geographie_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true]),
  Navigation_1 = Pattern{[workspaceId = "0875373d-96cd-4d0e-b4e7-5fc5cd327cb8"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6523eec-e450-401b-a672-cebe8d1ef2af"]}[Data],
  Navigation_3 = Navigation_2{[Id = "referentiels", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "geographie", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;

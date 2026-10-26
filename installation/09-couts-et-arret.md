# 9. Coûts et mise en veille

Le lab est dimensionné pour coûter peu quand il ne sert pas, à condition de l'arrêter en fin de séance. Les prix
dépendent de la région, de la devise et de vos accords ; estimez-les avec la calculatrice de prix Azure
(<https://azure.microsoft.com/pricing/calculator/>) et suivez-les dans Gestion des coûts Microsoft.

## 9.1 Ce qui est facturé

| Ressource | Facturée en continu | Facturée à l'usage | Comment la mettre en veille |
|---|---|---|---|
| Capacité Fabric F2 (si vous n'êtes pas en évaluation) | Oui, tant qu'elle est active | | Suspendre la capacité (portail Azure > capacité > Suspendre) |
| VM `WMSpostgre` et `WMSgateway` | Disques managés et adresses IP publiques Standard | Calcul, tant que les VM sont démarrées | `az vm deallocate` (un simple arrêt depuis le système d'exploitation continue de facturer le calcul) |
| Plan App Service B1 | Oui | | Supprimer le plan si le site ne sert plus ; l'arrêt de l'application ne réduit pas la facture du plan |
| Event Hubs Standard (1 unité de débit) | Oui | Événements entrants | Pas de mise en pause ; supprimer l'espace de noms si le temps réel ne sert plus |
| Azure SQL Database serverless | Stockage | Calcul, quand la base est active ; pause automatique après 60 minutes d'inactivité | Automatique. Le mirroring et les générateurs la réveillent |
| Key Vault, Application Insights, Log Analytics | Négligeable | Opérations et volume ingéré | |
| SharePoint, Dataverse (essai) | Inclus dans les licences | | |

## 9.2 En fin de séance

```bash
az vm deallocate -g RG_WMS -n WMSgateway --no-wait
az vm deallocate -g RG_WMS -n WMSpostgre --no-wait
# Capacité F2 : suspension (le nom et le groupe sont les vôtres)
az resource invoke-action --action suspend \
   --ids /subscriptions/<abonnement>/resourceGroups/<groupe>/providers/Microsoft.Fabric/capacities/<capacité>
```

Retirez aussi toute planification ajoutée à « Orchestration - Ingestion » : avec les VM désallouées, chaque
exécution échouerait sur la passerelle, et la capacité consommerait pour rien.

Pour reprendre : `az vm start` sur les deux VM, `resume` sur la capacité, puis attendez que la passerelle
apparaisse en ligne dans Fabric avant de lancer une ingestion.

## 9.3 Supprimer le lab

1. Dans Fabric, supprimez les deux espaces de travail (la corbeille les conserve pendant la durée de rétention
   configurée), le domaine `Commerce`, les connexions et la référence Azure Key Vault.
2. Supprimez le lien Fabric dans Power Apps avant l'environnement Dataverse, sinon le Lakehouse géré reste
   orphelin.
3. Supprimez les groupes de ressources : `az group delete -n RG_WMS` puis `az group delete -n RG_AmazingZone`.
   Le coffre de clés passe en suppression réversible pendant 7 jours ; `az keyvault purge` libère son nom plus tôt.
4. Dans Microsoft Entra, supprimez l'inscription d'application `SP-Fabric-AmazingZone` et le groupe
   `dp-equipedata` s'ils ne servent plus. Retirez aussi la passerelle `WMSgateway` de la liste des passerelles
   Fabric.

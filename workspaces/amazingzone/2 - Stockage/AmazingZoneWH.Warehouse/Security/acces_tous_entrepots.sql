CREATE ROLE [acces_tous_entrepots]
    AUTHORIZATION [SP-Fabric-AmazingZone];


GO

ALTER ROLE [acces_tous_entrepots] ADD MEMBER [dp-equipedata];


GO

ALTER ROLE [acces_tous_entrepots] ADD MEMBER [SP-Fabric-AmazingZone];


GO
# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f6523eec-e450-401b-a672-cebe8d1ef2af",
# META       "default_lakehouse_name": "AmazingZoneLK",
# META       "default_lakehouse_workspace_id": "0875373d-96cd-4d0e-b4e7-5fc5cd327cb8",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6523eec-e450-401b-a672-cebe8d1ef2af",
# META           "name": "AmazingZoneLK"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Run the below script or schedule it to run regularly to optimize your Lakehouse table 'sensors'

from delta.tables import *
deltaTable = DeltaTable.forName(spark, "sensors")
deltaTable.optimize().executeCompaction()

# If you only want to optimize a subset of your data, you can specify an optional partition predicate. For example:
#
#     from datetime import datetime, timedelta
#     startDate = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
#     deltaTable.optimize().where("date > '{}'".format(startDate)).executeCompaction()


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

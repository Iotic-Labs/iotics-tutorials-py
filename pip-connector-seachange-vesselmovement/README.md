# Vessel Movement Connector

This module provides a Connector that ingests PIP Data to create Twins of Vessels arriving and departing from the Portsmouth International Port (PIP).

## pip_data.py

The **PIPData** Class is defined to facilitate the loading of PIP Data related to vessel movements and vessel information. Additionally, it offers a variety of methods to assist the user in retrieving specific fields from these datasets. Once live data becomes available, the Class will be updated to provide methods for accessing real-time vessel movement and vessel information.

## publisher_connector.py

Defines a **VesselMovementConnector** Class responsible for simulating the creation of Vessel Twins and scheduling sharing events about arrival and departure to/from PIP. Upon instantiation, the VesselMovementConnector object requires a **PIPData** object, responsible for retrieving info about vessels and their movements around PIP.

1. At start-up the vessel movement dataset is scanned and each row is processed individually. The Estimated Time of Arrival (ETA) for each entry is checked. If the ETA is too far back in the past, that particular entry is skipped. Conversely, if the ETA is determined to be too far ahead in the future, the iteration is paused and it waits until it's time to handle that entry. When processing an entry:

    1.a If the Vessel Twin has not yet been created, it is instantiated and default values are shared for arrival and departure Feeds (`departed=False`, `arrived=False`);

    1.b  If the Vessel Twin already exists, its Feed's Metadata is scheduled for update based on the Estimated Time of Arrival (ETA) of the vessel movement, ensuring it occurs at the appropriate future time or immediately if the ETA is in the past. 
2. Regardless of the existence of the Vessel Twin, the sharing of vessel movement data is scheduled based on the actual time of arrival (ATA) or departure (ATD), ensuring it happens at the appropriate future time or immediately if the actual time is in the past.
3. Finally, the timing for scheduling the Delete Vessel Twin operation is determined. If the ATD is in the future, the Delete Twin operation is scheduled for the appropriate future time. If the ATD is in the past, the Delete Twin operation is triggered immediately.


## main.py

Initialises a PIP Data object (**PIPData**) and a Vessel Movement Connector (**VesselMovementConnector**) and starts processing the PIP dataset.

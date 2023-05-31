metro.aimsun
=============

*aimsun* sub-package is used for simulation-based route assignment models, which 
run using Aimsun. In addition to its initialization file, *aimsun* contains the 
*base* class, which represents the super-class for the *traffic_assignment* and 
*transit_assignment* classes. *traffic_assignment* and *transit_assignment* classes 
are used to initialize, set up, run, and extract outputs and LOS attributes of 
Aimsun-based dynamic traffic assignment and public transit assignment models, 
respectively. *trip_assignment* class is used to integrate a *traffic_assignment*
instance with multiple *transit_assignment* instances to build and run a dynamic 
multimodal route assignment model. *fares* and *tolls* classes are used to define 
the public transit fares and road tolls, respectively. The pt_weights class 
defines the weights of different components of the generalized transit cost function. 
Finally, the outputs class is used for route-based statistics collection.

Submodules
----------

metro.aimsun.aimsun_network module
----------------------------------

.. automodule:: metro.aimsun.aimsun_network
   
.. autoclass:: aimsunNetwork
    :members: 

metro.aimsun.base module
------------------------

.. automodule:: metro.aimsun.base
   
.. autoclass:: aimsunModel
    :members: 

.. autoclass:: aimsunModelType

metro.aimsun.traffic_assignment module
--------------------------------------

.. automodule:: metro.aimsun.traffic_assignment
   
.. autoclass:: DUEModel
    :members: 

metro.aimsun.transit_assignment module
--------------------------------------

.. automodule:: metro.aimsun.transit_assignment
   
.. autoclass:: PTModel
    :members: 

metro.tools
=============

*tools* sub-package contains many helper modules. In addition to its 
initialization file, it contains the *demand* class, which is used mainly to 
store different kind of time and mode-based OD matrices. It defines many 
operations on these matrices, such as arithmetic operators, comparison 
operators, sub-setting, saving, loading, printing, etc. The OD matrices 
can be used to store Aimsun demand, DCM demand, LOS attributes, and so on. 
*tools* sub-package also contains the *convergence* class, which is used for 
testing Aimsun and DCM demand convergence. *los* class defines the various 
kinds of traffic and transit level-of-service attributes and can save and load 
the LOS attributes in addition to merging two sets of LOS attributes, such as 
what is done while filling the zero cells in the simulation-based LOS with the 
non-zero Google-based LOS. *plot* class is used to automatically generate 
different kinds of figures, e.g., line charts, bar charts, and stacked bar 
charts, for OD matrices, LOS attributes, etc. *fitness_calculations* class 
is used to define different kinds of fitness functions that can be used to 
assess the performance of the transportation system. It can calculate the 
average travel time of either the entire network or a portion thereof as a 
(weighted) sum of any combination of the following components: driving travel 
time, transit in-vehicle travel time, transit out-of-vehicle travel time, 
transit wait time, and transit crowdedness. It can also calculate the average 
and/or total road tolls and/or transit fares. The calculated fitness function 
is usually returned in the format of OD matrices. *setup* class is used to 
distinguish the mode in which the current application runs, i.e., the regular 
Python engine or the Aimsun-embedded Python engine is used to run the current 
application. *setup_logging* class is used to set the logging configurations, 
while *system_info* class is used for printing some useful information about 
the current user, machine architecture, Aimsun version, etc. Lastly, the tools 
class contains some helper functions, such as designing different pricing 
structures based on specific parameters.

Submodules
----------

metro.tools.demand module
----------------------------------

.. automodule:: metro.tools.demand
   
.. autoclass:: ODMatrices
    :members: 

metro.tools.los module
----------------------

.. automodule:: metro.tools.los
   
.. autoclass:: levelOfServiceAttributes
    :members: 

metro.tools.det_data module
----------------------

.. automodule:: metro.tools.det_data
    :members: process_det_data
DP a.k.a. "Data processing" with EDF scheduling
************************************************
 
DP a.k.a. "Data processing" is an async scheduling method of data processing modules. Each module works in a separate, preemptible thread with lower priority than LL thread. It allows processing with periods longer than 1ms, on-demand processing, etc. 

Unlike in LL "low latency" method where a module started every 1ms cycle and all of LL modules together MUST finish processing 1ms, DP works async and gets CPU when a module is "ready for processing", what means:

    - on each module's input buffer there's at least IBS bytes of data and in each module's output  buffer there's at least OBS bytes of free space

    OR

    - a module declared readiness by itself by an optional API call "is_ready_to_process"

Critical part is that the module **must** finish processing before its **deadline**. A deadline is a time when the modules must provide a data chunk in order to keep next module(s) in the  pipeline working.
 
To ensure that all modules provide data on time - as long as CPU is not overloaded - regardless  of modules' processing times and processing periods, a Earliest Deadline First (EDF) scheduling  is used.  https://en.wikipedia.org/wiki/Earliest_deadline_first_scheduling

A list of all DP tasks, regardless on core the task is on, is to be iterated every time  the situation of DP readiness or deadline timing may change, that include:

    - finish of processing of LL pipeline (on any core)
    - finish of processing of any DP module (on any core)
 
during the iteration, the following will be checked:
    
    - Readiness of each DP module. As mentioned before,  module "is ready" when declared readiness by itself an API call  or when it has at least IBS of data on each input and at least OBS free space on each out
    - deadline calculation of each DP module. LFTs and Deadlines are not constant, they may change when a module consume/produce a portion of data. Therefore all LFTs and Deadlines must be re-calculated

DEADLINE CALCULATIONS
======================

The most critical part is to calculate deadlines. Lets go from the beginning, there are some definitions:

**def: buffers' Latest Feeding Time (LFT)**

LFT is the latest time when **a buffer** must be fed with a portion of data allowing its data consumer to work and finish in its specific time

LFT is a parameter specific to a buffer and can be calculated based on:

    - current amount of data in the buffer
    - data reciever's consumption rate and period
    - data source production rate and period
    - data reciever's module's LST - latest start time

so, in high level LFT is a sum of:

  - Latest start time (LST) of the data consumer (LST is defined later)

  - estimated time the consumer will drain the current data from the buffer: ``number_of_ms_in_buffer / consumer_period``

        i.e. if there's 5ms of data in the buffer and period of the consumer is 2ms, the calculated time is ``4ms``

  - correction for multiple source cycle

      in case the producer period < consumer period the LFT time needs to be corrected, as the producer must process more than once to provide enough data. The correction will be calculated as: ``producer_LPT * required_number_of_cycles`` where LPT is longest processing time, explained later

      ``correction = producer_LPT * ((consumer_period - number_of_ms_in_buffer) / producer_period)``

      if correction is < 0, it should be set to zero. Note that in case producer_period >= consumer_period correction is always 0

finally: ``LFT = LST(consumer) + estimated_drain_time - correction``

**def: DP module's DEADLINE**

a DEADLINE is the latest moment **a module** must finish processing to feed all target  buffers before their LFTs.
Calculation is simple:

   - module's deadline is the nearest LFT of all target buffers

in case te LFT of the buffer cannot be calculated - that may happen during pipeline startup or if there's no output buffer, i.e. a module like speech recognition - deadline should be set to "moment when module becomes ready + modules's period"

**def: DP module's Longest Processing Time (LPT)**

LPT is the longest time the module may process a portion of data, assuming it is scheduled 100% of CPU time. **LPT cannot be measured in runtime** as processing may change from cycle to cycle, etc. It can, however, be estimated based on:

- declared (by a module vendor) number of CPU cycles required for processing.  This declaration should be done separately for all combination of input/output data formats, platform, CPU type, using of HiFi etc. and either included in manifest od provided in an IPC call
- If declaration is not available, we can take "a period" as an approximation of longest possible processing time. "A period" is a value calculated using IBS and data consumption rate of a module. A module cannot possibly processing longer than its period, because it would never provide data in time (if LPT = period that means a module required 100% of CPU for processing, so it is really the worst possible case)

*Example:* if a data rate is 48samples/msec and OBS = 480samples, the "worst case" period should be calculated 10ms

*NOTE:* in case of sampling freq like 44.1 a round up should taken - if ration is 44.1 samples per mlisecond, 45 samples should be used for calculations

The "worst case approximation", however a correct, is assuming that a module is a heavy one and it requires 100% of CPU time. Using it may lead to unnecessary buffering, see "delayed start" section below.

**def: DP module's latest start time (LST)**

LST is the latest time when **a module** must start processing a portion of data in order to meet its deadline. It can be calculated as:
``deadline - LPT`` When a module is in the middle of processing, its LST may be negative. In that case 0 should be taken to all futhure calculations.

**Based on an above, it is clear that we do need to calculate first a deadline of the very latest module in a chain, than go back and calculate LFTs and deadline of each module separately**

Fortunate is that the last module of a pipeline is almost always an LL module (usually DAI). For LL module deadline always is "NOW", so it is very easy to calculate LFTs for its input buffer(s). note: in case of data rates like 44.1, which cannot be divided to 1ms, a round up to 45 should be used:

   - LL module always start in 1ms periods
   - LL module always consume constant number of bytes in a cycle (with an exception for  frequencies like 44.1, a round up 45KHz should be taken for calculations)

 so ``LFT = NOW + number of data chunks in buffer * 1ms``

"NOW" in all of the calculations is "last start of LL scheduler". It makes all calculations simpler, as in the examples below (calculating CPU cycles would require taking extra care for 32bit overflows or use slow 64bit operations). Also all modules have the same timestamp as "NOW", regardless of moment in the cycle the deadlines are calculated.

If a module is in the middle of processing, it should not release data from input buffer till the processing is finished, so the input buffer should be considered as it was at the moment the processing started, otherwise  deadlines may be miscalculated. 

In case of pipeline like:

.. uml:: images/dp_scheduling/pic1_chains.pu

there are 2 separate deadline calculation chains: DP4 than DP3, and (independent) DP2 than DP1. **Also note that deadlines and other parameters may change, so re-calculation of all parameters should occur reasonable frequently and include all DP modules, regardless of a core it is run on**

End of stream
=============

When a SP module is in the middle of processing when a pipeline is stopping, it should finish processing its current chunk of data. Unformtunately there's no way to interrupt ongoing processing without risk of memory leaks etc. Therefore IPC stopping a pipeline should wait till all DP modules finish processing. 

EXAMPLE1 
=========
*data source period is longer or equal to data consumer period*
Note that in the example CPU load is very close to 100%, yet deadline calculation and EDF scheduling allow to keep the processing on time. 

for simplification lets assume:

   - the pipeline is in stable state (processing for a while, not in startup)
   - no DP is currently processing
   - whole CPU is dedicated to DP, like if LL is on core 0 and DPs on core 1
  
**0ms time:**

.. uml:: images/dp_scheduling/example1.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 15 periods of LL2`` ==> ``DP2 deadline = 15ms``
   - ``DP2 LST = 15ms (DP2 deadline) - 9ms (DP2 LPT) = 6ms``
   - ``buf2 LFT = 6ms (DP2 LST) + 10ms (1 period in buf2) = 16ms`` ==> ``DP1 deadline = 16ms``

   DP2 will be scheduled as it has earliest deadline, will process for 9ms

**9ms time, DP2 finished processing but not yet released data from BUF2:**

.. uml:: images/dp_scheduling/example1_1.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 just finished processing
    
   calculate deadlines:

   - ``buf3 LFT = 6 periods of LL2`` ==> ``DP2 deadline = 6ms``
   - ``DP2 LST = 6ms(DP2 deadline) - 9ms (DP2 LPT) = -3ms`` LST is negative, 0 should be used ``DP2 LST = 0``
   - ``buf2 LFT = 6ms (DP2 LST) + 10ms (1 period in buf2) = 16ms`` ==> ``DP1 deadline = 16ms``

   DP1 will be scheduled

**9ms time, DP2 released data from BUF2:**

.. uml:: images/dp_scheduling/example1_2.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 16 periods of LL2`` ==> ``DP2 deadline = 16ms``
   - ``DP2 LST = 16ms(DP2 deadline) - 9ms (DP2 LPT) = 7ms``
   - ``buf2 LFT = 7ms (DP2 LST) = 7ms`` ==> ``DP1 deadline = 7ms``
    
   DP1 will be scheduled, will run for 5ms

**14ms time, DP1 finished processing and released data from BUF1:**

.. uml:: images/dp_scheduling/example1_3.pu

Pipeline state:

   - DP1 is not ready for processing
   - DP2 is ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 11 periods of LL2`` ==> ``DP2 deadline = 11ms``
   - ``DP2 LST = 11ms(DP2 deadline) - 9ms (DP2 LPT) = 2ms``
   - ``buf2 LFT = 2ms (DP2 LST) + 100ms (10 periods in buf2) = 102ms`` ==> ``DP1 deadline = 102ms``
    
   DP2 will be scheduled 

**100ms time, 86ms passed, DP2 processed 9 times, is in the middle of 10th processing, having 5ms left:**

.. uml:: images/dp_scheduling/example1_4.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 15 periods of LL2`` ==> ``DP2 deadline = 15ms``
   - ``DP2 LST = 15ms(DP2 deadline) - 9ms (DP2 LPT) = 6ms``
   - ``buf2 LFT = 6ms (DP2 LST) + 10ms (1 period in buf2) = 16ms`` ==> ``DP1 deadline = 16ms``
    
   DP2 will be scheduled 

**105ms time, DP2 finished processing and released data from BUF2:**

.. uml:: images/dp_scheduling/example1_5.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 20 periods of LL2`` ==> ``DP2 deadline = 20ms``
   - ``DP2 LST = 20ms(DP2 deadline) - 9ms (DP2 LPT) = 11ms``
   - ``buf2 LFT = 11ms (DP2 LST) + 0ms = 11ms`` ==> ``DP1 deadline = 11ms``
    
   DP1 will be scheduled

EXAMPLE2 
=========
*data source period is shorter than data consumer period*

**0ms time:**

.. uml:: images/dp_scheduling/example2.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 18 periods of LL2`` ==> ``DP2 deadline = 18ms``
   - ``DP2 LST = 18ms (DP2 deadline) - 10ms (DP2 LPT) = 8ms``
   - ``buf2 LFT = 8ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) = 8ms`` correction for multiple source cycle is = 0
   - ``DP1 deadline = 8ms``
    
   DP1 will be scheduled

**2ms time:**

.. uml:: images/dp_scheduling/example2_1.pu
  
Pipeline state:

   - DP1 is not ready for processing
   - DP2 is ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 16 periods of LL2`` ==> ``DP2 deadline = 16ms``
   - ``DP2 LST = 16ms (DP2 deadline) - 10ms (DP2 LPT) = 6ms``
   - ``buf2 LFT = 6ms(DP2 LST) + 20 (1 complete periods of DP2 in buf2) = 26ms`` correction for multiple source cycle is < 0, so 0 is used
   - ``DP1 deadline = 26ms``
    
   DP2 will be scheduled

**5ms time:**

.. uml:: images/dp_scheduling/example2_1a.pu
  
Pipeline state:

   - DP1 is ready for processing
   - DP2 is in the middle of processing, still has to keep processing for 7ms. According to rules, the module should not release data from input buffer till the processing is finished, so buf2 still contains 20ms samples
    
   calculate deadlines:

   - ``buf3 LFT = 13 periods of LL2`` ==> ``DP2 deadline = 13ms``
   - ``DP2 LST = 13ms (DP2 deadline) - 10ms (DP2 LPT) = 3ms``
   - ``buf2 LFT = 3ms(DP2 LST) + 20 (1 complete periods of DP2 in buf2) = 23ms`` correction for multiple source cycle is < 0, so 0 is used
   - ``DP1 deadline = 23ms``
 
   DP2 will be scheduled and will keep processing for 7ms

**12ms time, before releasing data from buf2 and acking data in buf3**

.. uml:: images/dp_scheduling/example2_2a.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 finished processing, but not yet released data from buf2, so buf2 still contains 20ms samples

   calculate deadlines:

   - ``buf3 LFT = 6 periods of LL2`` ==> ``DP2 deadline = 6ms``
   - ``DP2 LST = 6ms (DP2 deadline) - 10ms (DP2 LPT) = -4ms`` LST is negative, so 0 should be used
   - ``buf2 LFT = 0ms(DP2 LST) + 20ms (1 complete periods of DP2 in buf2) = 20ms`` correction for multiple source cycle is < 0, so 0 is used
   - ``DP1 deadline = 20ms``

   DP2 will be release data

**12ms time, after releasing data from buf2 and acking data in buf3**

.. uml:: images/dp_scheduling/example2_2.pu
  
Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 26 periods of LL2`` ==> ``DP2 deadline = 26ms``
   - ``DP2 LST = 26ms (DP2 deadline) - 10ms (DP2 LPT) = 16ms``
   - ``buf2 LFT = 16ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 8ms correction (4 periods of DP2 * 2ms DP1 LPT) = 8ms``
   - ``DP1 deadline = 8ms``
    
   DP1 will be scheduled 

**14ms time:**

.. uml:: images/dp_scheduling/example2_3.pu
  
Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 24 periods of LL2`` ==> ``DP2 deadline = 24ms``
   - ``DP2 LST = 24ms (DP2 deadline) - 10ms (DP2 LPT) = 14ms``
   - ``buf2 LFT = 14ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 6ms correction (3 periods of DP2 * 2ms DP1 LPT) = 8ms``
   - ``DP1 deadline = 8ms``
    
   DP1 will be scheduled 

**16ms time:**

.. uml:: images/dp_scheduling/example2_4.pu
  
Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines:

   - ``buf3 LFT = 22 periods of LL2`` ==> ``DP2 deadline = 22ms``
   - ``DP2 LST = 22ms (DP2 deadline) - 10ms (DP2 LPT) = 12ms``
   - ``buf2 LFT = 12ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 4ms correction (2 periods of DP2 * 2ms DP1 LPT) = 8ms``
   - ``DP1 deadline = 8ms``
    
   DP1 will be scheduled 

**18ms time:**

.. uml:: images/dp_scheduling/example2_5.pu
  
Pipeline state:

   - DP1 is not ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines - however pointless at when no DP is ready:

   - ``buf3 LFT = 20 periods of LL2`` ==> ``DP2 deadline = 20ms``
   - ``DP2 LST = 20ms (DP2 deadline) - 10ms (DP2 LPT) = 10ms``
   - ``buf2 LFT = 10ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 2ms correction (2 periods of DP2 * 2ms DP1 LPT) = 8ms``
   - ``DP1 deadline = 8ms``
    
   no DP will be scheduled

**20ms time:**

.. uml:: images/dp_scheduling/example2_6.pu
  
Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing
    
   calculate deadlines - however pointless at when no DP is ready:

   - ``buf3 LFT = 18 periods of LL2`` ==> ``DP2 deadline = 18ms``
   - ``DP2 LST = 18ms (DP2 deadline) - 10ms (DP2 LPT) = 8ms``
   - ``buf2 LFT = 8ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 2ms correction (2 periods of DP2 * 2ms DP1 LPT) = 6ms``
   - ``DP1 deadline = 6ms``
    
   DP1 will be scheduled 

**22ms time:**

.. uml:: images/dp_scheduling/example2_7.pu
  
Pipeline state:

   - DP1 is not ready for processing
   - DP2 is ready for processing
    
   calculate deadlines 

   - ``buf3 LFT = 16 periods of LL2`` ==> ``DP2 deadline = 16ms``
   - ``DP2 LST = 16ms (DP2 deadline) - 10ms (DP2 LPT) = 6ms``
   - ``buf2 LFT = 6ms(DP2 LST) +20 (1 complete period of DP2 in buf2) = 26ms`` correction for multiple source cycle is = 0
   - ``DP1 deadline = 26ms``
    
   DP2 will be scheduled 


STARTUP
==========

Special case is "pipeline startup". When a pipeline is starting, deadlines cannot be calculated as all the modules are already late and deadlines are in the past. According to deadline calculation rules, the deadline is set to time when the module becomes ready + module's LPT. 

If a module finishes processing before its LPT. it is not guaranteed that it will do it again in any of next cycles. If it happens, the data should be held in the buffer till LPT passes. This prevents underruns in case any of future processing takes longer. This mechanism is called "delayed start". The module should stay in "delayed start" state till the next module becomes ready for the first time.

Delayed start makes EDF scheduling possible and ensures that even when CPU load close to 100%  every module have enough processing time to finish within its deadline.

Example of a pipeline startup and 100% cpu usage 
================================================

**0ms time:**

.. uml:: images/dp_scheduling/example3.pu

Pipeline state:

   - DP1 is not ready for processing, in startup delay state
   - DP2 is not ready for processing, in startup delay state
    
   calculate deadlines 

   - dedline of DP2 can't be calculated
   - dedline of DP1 can't be calculated

   no DP will be scheduled 

**5ms time:**

.. uml:: images/dp_scheduling/example3_1.pu

Pipeline state:

   - DP1 is ready for processing, in startup delay state
   - DP2 is not ready for processing, in startup delay state
    
   calculate deadlines 

   - deadline for DP2 cant be calculated
   - deadline of DP1 is fixed to 2ms (NOW + DP1 LPT) - because DP2 deadline cannot be calculated
    
   DP1 will be scheduled 

**7ms time:**

.. uml:: images/dp_scheduling/example3_2.pu

Pipeline state:

   - DP1 is not ready for processing, in startup delay state
   - DP2 is not ready for processing, in startup delay state
    
   calculate deadlines 

   - deadline for DP2 cant be calculated
   - deadline for DP1 cant be calculated
    
   no DP will be scheduled 

**10ms time:**

.. uml:: images/dp_scheduling/example3_3.pu

Pipeline state:

   - DP1 is ready for processing, in startup delay state
   - DP2 is not ready for processing, in startup delay state
    
   calculate deadlines 

   - deadline for DP2 cant be calculated
   - deadline of DP1 is fixed to 2ms (NOW + DP1 LPT) - because DP2 deadline cannot be calculated
    
   DP1 will be scheduled 

**12ms time:**

.. uml:: images/dp_scheduling/example3_4.pu

Pipeline state:

   - DP1 is not ready for processing, leaving startup delay state
   - DP2 is ready for processing, in startup delay state

   calculate deadlines 

   - deadline for DP2 is fixed to 6ms (NOW + DP2 LPT) 
   - ``DP2 LST = 6ms (DP2 deadline) - 6ms (DP2 LPT) = 0ms``
   - ``buf2 LFT = 0ms(DP2 LST) + 10ms (1 complete period of DP2 in buf2) = 10ms`` correction for multiple source cycle is = 0
   - ``DP1 deadline = 14ms``

    DP2 will be scheduled

**15ms time:**

.. uml:: images/dp_scheduling/example3_5.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is the middle for processing, 3ms left, in startup delay state

   calculate deadlines 

   - deadline for DP2 was fixed to 6ms 3ms ago, so now it is 3ms
   - ``DP2 LST = 3ms (DP2 deadline) - 6ms (DP2 LPT) = -3ms`` 0 will be used
   - ``buf2 LFT = 0(DP2 LST) +10 (1 complete period of DP2 in buf2) = 10ms`` correction for multiple source cycle is = 0
   - ``DP1 deadline = 10ms``

    DP2 will be scheduled

**17ms time:**

.. uml:: images/dp_scheduling/example3_6.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing, leaving startup delay state

   calculate deadlines 

   - ``buf3 LFT = 10 periods of LL2`` ==> ``DP2 deadline = 10ms``
   - ``DP2 LST = 10ms (DP2 deadline) - 6ms (DP2 LPT) = 4ms``
   - ``buf2 LFT = 4ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 2ms correction (2 periods of DP2 * 2ms DP1 LPT) = 2ms``
   - ``DP1 deadline = 2ms``

    DP1 will be scheduled

**19ms time:**

.. uml:: images/dp_scheduling/example3_7.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing

   calculate deadlines 

   - ``buf3 LFT = 8 periods of LL2`` ==> ``DP2 deadline = 8ms``
   - ``DP2 LST = 10ms (DP2 deadline) - 6ms (DP2 LPT) = 2ms``
   - ``buf2 LFT = 2ms(DP2 LST) + 0 (0 complete periods of DP2 in buf2) - 0ms correction (0 periods of DP2 * 2ms DP1 LPT) = 2ms``
   - ``DP1 deadline = 2ms``

    DP1 will be scheduled


Example of a 2 pipelines, one running and one in startup and 100% cpu usage 
============================================================================

pipeline1 is running, DP use 80% of CPU, pipeline2 is starting. Calculating of DP1/DP2 LST and BUF1/BUF3 LFT makes no sense as they're connected to LLs

**0ms time:**

.. uml:: images/dp_scheduling/example4.pu

Pipeline state:

   - DP1 is ready for processing
   - DP2 is not ready for processing

   calculate deadlines 

   - ``buf2 LFT = 10 periods of LL2`` ==> ``DP1 deadline = 10ms``
   - DP2 deadline cannot be calculated

    DP1 will be scheduled

**5ms time:**

.. uml:: images/dp_scheduling/example4_1.pu

Pipeline state:

   - DP1 is in the middle of processing, 3ms left
   - DP2 is ready for processing, in startup delay state

   calculate deadlines 

   - ``buf2 LFT = 5 periods of LL2`` ==> ``DP1 deadline = 5ms``
   - DP2 deadline is fixed to ``DP2 period = 1ms``

    DP1 will be preempted, DP2 will be scheduled

**6ms time:**

.. uml:: images/dp_scheduling/example4_2.pu

Pipeline state:

   - DP1 is in the middle of processing, 3ms left
   - DP2 is not ready for processing, leaving startup delay state

   calculate deadlines 

   - ``buf2 LFT = 4 periods of LL2`` ==> ``DP1 deadline = 4ms``
   - ``buf4 LFT = 5 periods of LL2`` ==> ``DP2 deadline = 5ms``
   

    DP2 will be scheduled



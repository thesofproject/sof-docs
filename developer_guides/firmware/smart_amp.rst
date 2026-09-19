.. _smart_amp:

====================================
Smart Amplifier Protection & Physics
====================================

.. contents::
   :local:
   :depth: 3

Overview
========

Modern laptops, tablets, and mobile devices operate under aggressive physical and industrial design constraints. Thin chassis profiles require miniature micro-speakers with tiny voice coils, compact neodymium magnetic assemblies, and lightweight polymer diaphragms housed within sub-optimal acoustic back-cavities. 

While these transducers are engineered for compact integration, their physical limits severely constrain maximum acoustic loudness and low-frequency bass reproduction:

* **Thermal Limits**: Sustained high-voltage audio signals dissipate electrical energy as resistive heat in the voice coil winding. Excessive temperatures degrade wire insulation, soften structural bobbins, melt coil adhesives, and ultimately cause open-circuit thermal burnout.
* **Mechanical Excursion Limits**: Low-frequency signals near or below the loudspeaker mechanical resonance frequency drive large peak-to-peak diaphragm excursions. If the cone displacement exceeds physical suspension bounds, the voice coil former violently strikes the back plate (*bottoming out*), suspensions tear, and severe acoustic distortion occurs.

Conventional audio architectures protect transducers using static brickwall limiters or aggressive fixed Dynamic Range Compression (DRC). Because static limiters must accommodate worst-case ambient temperatures, component manufacturing variances, and crest factors, they force engineers to set gain thresholds 6 dB to 12 dB below what the speaker could safely reproduce.

**Smart Amplifier Protection** (*Smart Amp*) bridges this acoustic gap. By coupling a feed-forward audio processing pipeline with a real-time current (:math:`I`) and voltage (:math:`V`) feedback sense stream digitized directly at the amplifier terminals, the DSP continuously tracks the physical state of the voice coil (instantaneous resistance, temperature, and cone excursion). This adaptive closed loop enables the firmware to drive micro-speakers right to their true physical boundaries—extracting up to +6 dB to +10 dB of clean acoustic loudness, deep dynamic bass extension, and high vocal intelligibility without risk of transducer damage.

.. graphviz::
   :caption: Figure 160: Electro-Acoustic Transducer Physics, Thermal Heating, and Excursion Boundaries
   :alt: Electro-Acoustic Transducer Physics, Thermal Heating, and Excursion Boundaries

   digraph smart_amp_physics {
       graph [rankdir=TB, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_elec {
           label = "Electrical Domain (Amplifier Terminals & Voice Coil)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           p_drive [label="Drive Voltage V(t)\nClass-D Power Stage", fillcolor="#BEE3F8", color="#2B6CB0"];
           p_coil [label="Voice Coil Impedance\nZ(s) = Re(T) + s*Le + Zem(s)", fillcolor="#FFFFFF", color="#2B6CB0"];
           p_curr [label="Coil Current I(t)\nSense Resistor / ADC", fillcolor="#BEE3F8", color="#2B6CB0"];
           p_heat [label="Joule Dissipation\nP = I(t)^2 * Re(T)", fillcolor="#FED7D7", color="#C53030"];
       }

       subgraph cluster_mech {
           label = "Electro-Mechanical Domain (Motor & Suspension)";
           style = "filled,rounded";
           color = "#2C7A7B";
           fillcolor = "#E6FFFA";

           p_lorentz [label="Lorentz Force\nF(t) = Bl * I(t)", fillcolor="#B2F5EA", color="#2C7A7B"];
           p_backemf [label="Back-EMF Feedback\ne_emf(t) = Bl * v(t)", fillcolor="#B2F5EA", color="#2C7A7B"];
           p_disp [label="Diaphragm Kinematics\nx(t) = integral(v(t) dt)", fillcolor="#FFFFFF", color="#2C7A7B"];
           p_res [label="Mechanical Resonance\nfs = 1 / (2*pi*sqrt(Mms*Cms))", fillcolor="#E2E8F0", color="#4A5568"];
       }

       subgraph cluster_limits {
           label = "Physical Transducer Damage Bounds";
           style = "filled,rounded";
           color = "#C53030";
           fillcolor = "#FFF5F5";

           p_tlimit [label="Thermal Boundary T_max\nAdhesive breakdown (100°C - 130°C)\nBurnout / open circuit", fillcolor="#FED7D7", color="#C53030"];
           p_xlimit [label="Mechanical Boundary X_mech\nVoice coil bottoming\nSuspension tearing / clipping", fillcolor="#FED7D7", color="#C53030"];
       }

       p_drive -> p_coil [label="Applies V(t)"];
       p_coil -> p_curr [label="Produces I(t)"];
       p_curr -> p_heat [label="Resistive loss"];
       p_curr -> p_lorentz [label="Bl coupling"];
       p_heat -> p_tlimit [label="Delta T >= 80°C\nExceeds limits", color="#C53030", style="dashed"];

       p_lorentz -> p_disp [label="Drives mass Mms"];
       p_disp -> p_backemf [label="Velocity v(t)"];
       p_backemf -> p_coil [label="Counter-voltage", color="#2B6CB0"];
       p_disp -> p_res [label="Peaks near fs"];
       p_disp -> p_xlimit [label="|x(t)| > X_max\nBottoming", color="#C53030", style="dashed"];
   }

Electro-Acoustic Foundations & Speaker Physics
==============================================

To safely control micro-speakers, the firmware requires an accurate mathematical model of the electro-dynamic transducer. A conventional moving-coil loudspeaker functions as an electro-mechanical energy converter characterized by Thiele-Small parameters.

The Lumped-Parameter Loudspeaker Model
--------------------------------------

The electrical behavior of the loudspeaker voice coil is governed by Kirchhoff's voltage law:

.. math::

   V(t) = I(t) \cdot R_e(T) + L_e \frac{d I(t)}{dt} + e_{\text{emf}}(t)

Where:

* :math:`V(t)` is the instantaneous voltage across the voice coil terminals (in Volts).
* :math:`I(t)` is the instantaneous current through the voice coil (in Amperes).
* :math:`R_e(T)` is the temperature-dependent DC electrical resistance of the voice coil (in Ohms).
* :math:`L_e` is the voice coil inductance (in Henrys).
* :math:`e_{\text{emf}}(t)` is the back-electromotive force generated by the coil moving through the magnetic field:

.. math::

   e_{\text{emf}}(t) = B \cdot l \cdot \dot{x}(t) = B \cdot l \cdot v(t)

Where:

* :math:`B` is the magnetic flux density in the voice coil air gap (in Tesla).
* :math:`l` is the length of the voice coil wire within the magnetic field (in meters).
* :math:`B \cdot l` is the electro-mechanical force factor (in Newton/Ampere or Tesla-meters).
* :math:`v(t) = \dot{x}(t)` is the instantaneous velocity of the cone diaphragm (in meters/second).

Newton's second law governs the mechanical domain:

.. math::

   F(t) = B \cdot l \cdot I(t) = M_{ms} \ddot{x}(t) + R_{ms} \dot{x}(t) + \frac{1}{C_{ms}} x(t)

Where:

* :math:`M_{ms}` is the total moving mass of the diaphragm and voice coil assembly (in kilograms).
* :math:`R_{ms}` is the mechanical damping resistance of the suspension (in Newton-seconds/meter).
* :math:`C_{ms}` is the mechanical compliance of the suspension (in meters/Newton).
* :math:`x(t)` is the cone displacement (excursion) relative to its resting position (in meters).

The mechanical resonance frequency :math:`f_s` is defined by:

.. math::

   f_s = \frac{1}{2\pi \sqrt{M_{ms} C_{ms}}}

Near :math:`f_s`, the mechanical impedance reaches a minimum, causing cone excursion to peak sharply for a given drive voltage.

Thermal Dissipation Mechanics
-----------------------------

Typical micro-speakers exhibit an electrical-to-acoustic power conversion efficiency of less than 1%. More than 99% of the delivered electrical power is converted into heat:

.. math::

   P_{\text{diss}}(t) = I^2(t) \cdot R_e(T)

The heat generated in the voice coil conducts across the narrow air gap into the magnet pole piece and frame, eventually radiating into the enclosure air. This thermodynamic system is modeled as a two-stage thermal RC network:

1. **Voice Coil Thermal Node**: Small thermal capacitance :math:`C_{th,coil}` with a fast thermal time constant :math:`\tau_{th,coil} = R_{th,coil} \cdot C_{th,coil}` (typically 0.5 to 2.0 seconds).
2. **Magnet/Frame Thermal Node**: Large thermal capacitance :math:`C_{th,magnet}` with a slow thermal time constant :math:`\tau_{th,magnet}` (typically 30 to 120 seconds).

As voice coil temperature rises, the electrical resistance of the copper winding increases linearly according to the temperature coefficient of copper (:math:`\alpha_{Cu} \approx 0.00393 / ^\circ\text{C}`):

.. math::

   R_e(T) = R_0 \cdot \left[ 1 + \alpha_{Cu} (T - T_0) \right]

Where :math:`R_0` is the cold voice coil resistance measured at baseline ambient temperature :math:`T_0` (typically 20°C).

Real-Time Current and Voltage (I/V) Sense
=========================================

Hardware Architecture & Telemetry Capture
-----------------------------------------

In modern smart amplifier hardware (such as Maxim DSM, Cirrus Logic, Texas Instruments, or Realtek smart power amplifiers), the integrated circuit incorporates dedicated on-chip Current-Sense and Voltage-Sense Analog-to-Digital Converters (ADCs). 

* **Voltage Sense (V-Sense)**: Measures the actual differential voltage applied across the speaker voice coil terminals after Class-D output filtering, capturing battery voltage drops and amplifier clipping.
* **Current Sense (I-Sense)**: Measures the current flowing through the voice coil using an ultra-low-value series resistor or an integrated current mirror.

The digitized :math:`I` and :math:`V` samples are multiplexed into a high-speed digital audio bus (e.g. SoundWire or TDM / I2S) and streamed upstream into the DSP as an asynchronous capture stream.

.. graphviz::
   :caption: Figure 161: Real-Time I/V Sense Feedback Loop and Parameter Estimation
   :alt: Real-Time I/V Sense Feedback Loop and Parameter Estimation

   digraph smart_amp_iv {
       graph [rankdir=LR, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_hw {
           label = "Hardware Smart Amplifier IC";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#EDF2F7";

           hw_dac [label="Class-D Power Amp\nBridge-Tied Load (BTL)", fillcolor="#CBD5E0", color="#4A5568"];
           hw_spk [label="Micro-Speaker\nVoice Coil & Cone", fillcolor="#FEB2B2", color="#C53030"];
           hw_vsense [label="V-Sense ADC\nTerminal Voltage V(t)", fillcolor="#BEE3F8", color="#2B6CB0"];
           hw_isense [label="I-Sense ADC\nCoil Current I(t)", fillcolor="#BEE3F8", color="#2B6CB0"];
           hw_tdm [label="Upstream Transmitter\nSoundWire / TDM DAI", fillcolor="#CBD5E0", color="#4A5568"];
       }

       subgraph cluster_dsp {
           label = "Sound Open Firmware (SOF) Smart Amp Engine";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           dsp_rx [label="Capture DAI Copier\nI/V Ingestion Buffer", fillcolor="#FFFFFF", color="#2B6CB0"];
           dsp_est_r [label="Resistance Tracking\nRe(t) = LowFreq(V) / LowFreq(I)", fillcolor="#BEE3F8", color="#2B6CB0"];
           dsp_est_t [label="Thermal Estimator\nDelta T = (Re - R0) / (alpha * R0)", fillcolor="#FED7D7", color="#C53030"];
           dsp_est_x [label="Back-EMF & Excursion\ne_emf = V - I*Re - Le(dI/dt)\nx(t) = integral(e_emf / Bl)", fillcolor="#B2F5EA", color="#2C7A7B"];
           dsp_ctrl [label="Dynamic Protection Core\nExcursion Limiter + Thermal Limiter", fillcolor="#FEFCBF", color="#B7791F"];
       }

       hw_dac -> hw_spk [label="Drives audio"];
       hw_spk -> hw_vsense [label="Terminal tap"];
       hw_spk -> hw_isense [label="Current sense"];
       hw_vsense -> hw_tdm [label="V samples"];
       hw_isense -> hw_tdm [label="I samples"];

       hw_tdm -> dsp_rx [label="SoundWire / I2S", color="#2B6CB0", penwidth=1.8];
       dsp_rx -> dsp_est_r [label="Synchronous I/V"];
       dsp_est_r -> dsp_est_t [label="Voice coil Re(t)"];
       dsp_rx -> dsp_est_x [label="High-speed I/V"];
       dsp_est_r -> dsp_est_x [label="Compensated Re(t)"];

       dsp_est_t -> dsp_ctrl [label="Temperature T_coil", color="#C53030"];
       dsp_est_x -> dsp_ctrl [label="Displacement x(t)", color="#2C7A7B"];
   }

Continuous Resistance and Temperature Tracking
----------------------------------------------

Because the coil resistance varies with temperature, the firmware isolates the low-frequency electrical impedance. By computing the ratio of voltage to current over a low-pass filtered band:

.. math::

   R_e(t) = \frac{\langle V_{\text{low}}(t) \cdot I_{\text{low}}(t) \rangle}{\langle I_{\text{low}}^2(t) \rangle}

Once the instantaneous resistance :math:`R_e(t)` is derived, the absolute voice coil temperature is determined:

.. math::

   T_{\text{coil}}(t) = T_0 + \frac{R_e(t) - R_0}{\alpha_{Cu} \cdot R_0}

This measurement operates continuously without requiring offline calibration breaks, allowing the DSP to detect overheating in real time.

Back-EMF Isolation and Excursion Prediction
-------------------------------------------

Predicting mechanical excursion purely from the input audio signal requires assuming static, idealized parameters. However, mechanical compliance :math:`C_{ms}` shifts by up to 50% across temperature and aging, and enclosure acoustic back-cavities can suffer air leaks.

By measuring both :math:`V(t)` and :math:`I(t)`, the firmware computes the true back-EMF:

.. math::

   e_{\text{emf}}(t) = V(t) - I(t) \cdot R_e(t) - L_e \frac{d I(t)}{dt}

Because :math:`e_{\text{emf}}(t) = B \cdot l \cdot v(t)`, the diaphragm velocity is directly extracted:

.. math::

   v(t) = \frac{e_{\text{emf}}(t)}{B \cdot l}

Integrating velocity yields the instantaneous physical cone displacement :math:`x(t)`:

.. math::

   x(t) = \int_0^t v(\tau) d\tau = \int_0^t \frac{V(\tau) - I(\tau) R_e(\tau) - L_e \frac{d I(\tau)}{d\tau}}{B \cdot l} d\tau

This closed-loop displacement measurement reflects true transducer behavior in real time, automatically compensating for enclosure leaks, barometric pressure changes, and component aging.

The Sound Open Firmware Two-Layer Architecture
==============================================

To accommodate diverse amplifier vendor silicon while maintaining a unified, testable codebase, Sound Open Firmware structures the Smart Amplifier component into two distinct layers:

1. **Generic Component Layer** (`smart_amp.c`, `smart_amp_generic.c`): Open-source middleware interfacing with the SOF pipeline, scheduler, memory allocator, and ALSA topology.
2. **Inner Model Layer** (`smart_amp_mod_data_base`, `struct inner_model_ops`): Solution-specific algorithm implementation.

.. graphviz::
   :caption: Figure 162: Architectural Decoupling: Generic SOF Layer vs Solution-Specific Inner Model
   :alt: Architectural Decoupling: Generic SOF Layer vs Solution-Specific Inner Model

   digraph smart_amp_twolayer {
       graph [rankdir=TB, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_sof {
           label = "Sound Open Firmware Infrastructure";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#F7FAFC";

           sof_pipe [label="Playback Pipeline\nFeed-Forward Source (FF)", fillcolor="#EDF2F7", color="#4A5568"];
           sof_cap [label="Capture Pipeline\nFeedback Source (FB)", fillcolor="#EDF2F7", color="#4A5568"];
           sof_sink [label="Downstream DAI Sink\nProtected Audio Output", fillcolor="#EDF2F7", color="#4A5568"];
           sof_ipc [label="IPC Control Plane\nALSA byte controls / SET_LARGE_CONFIG", fillcolor="#EDF2F7", color="#4A5568"];
       }

       subgraph cluster_generic {
           label = "Generic Smart Amp Layer (smart_amp.c & smart_amp_generic.c)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           g_adapter [label="SOF Processing Module Adapter\nInterface lifecycle & triggers", fillcolor="#BEE3F8", color="#2B6CB0"];
           g_memmgr [label="Runtime Memory Manager\nAllocates & owns all memory blocks", fillcolor="#BEE3F8", color="#2B6CB0"];
           g_remap [label="Channel Remapping Engine\nsource_ch_map & feedback_ch_map", fillcolor="#BEE3F8", color="#2B6CB0"];
           g_conv [label="Format Conversion\nS16_LE / S24_4LE -> S32_LE inner format", fillcolor="#BEE3F8", color="#2B6CB0"];
           g_buffers [label="Intermediate Stream Buffers\nff_mod, fb_mod, out_mod", fillcolor="#FFFFFF", color="#2B6CB0"];
       }

       subgraph cluster_inner {
           label = "Inner Model Layer (smart_amp_mod_data_base & inner_model_ops)";
           style = "filled,rounded";
           color = "#2C7A7B";
           fillcolor = "#E6FFFA";

           i_ops [label="Inner Model Operations Table\ninit(), query_memblk_size(), set_memblk(),\nset_fmt(), ff_proc(), fb_proc(), get/set_config()", fillcolor="#B2F5EA", color="#2C7A7B"];

           subgraph cluster_impls {
               label = "Supported Inner Model Implementations (Kconfig Selectable)";
               style = "dotted";
               color = "#2C7A7B";

               impl_pass [label="PASSTHRU_AMP\nZero latency, bypass audio,\nconsumes/drops FB frames", fillcolor="#E2E8F0", color="#4A5568"];
               impl_dsm [label="MAXIM_DSM\nDynamic Speaker Management\n(Statically linked libdsm.a)", fillcolor="#FEFCBF", color="#B7791F"];
               impl_test [label="Test Smart Amp Module\nSynthetic model for unit tests", fillcolor="#E2E8F0", color="#4A5568"];
           }
       }

       sof_pipe -> g_remap [label="FF Frames"];
       sof_cap -> g_remap [label="FB Frames (I/V)"];
       g_remap -> g_conv -> g_buffers;
       g_buffers -> sof_sink [label="Safe Out"];

       sof_ipc -> g_adapter [label="Config & Model Blobs"];
       g_adapter -> g_memmgr;
       g_adapter -> i_ops [label="Dispatches mod_ops", color="#2B6CB0", penwidth=1.5];

       i_ops -> impl_pass [style="dashed"];
       i_ops -> impl_dsm [style="dashed"];
       i_ops -> impl_test [style="dashed"];

       g_buffers -> i_ops [label="Pointers to data buffers", color="#2C7A7B"];
   }

Generic Layer Responsibilities
------------------------------

The generic layer acts as the standard SOF processing component:

* **Lifecycle and Pipeline Orchestration**: Implements `init()`, `prepare()`, `process()`, `trigger()`, `reset()`, and `free()` matching the unified SOF module adapter interface.
* **Full Memory Ownership**: To ensure deterministic isolation, the generic layer completely manages memory allocation. It queries the inner model for required buffer sizes across distinct lifecycle stages and allocates all buffers using SOF core memory allocators.
* **Channel Remapping**: The physical arrangement of audio channels in the capture pipeline often varies across hardware designs (e.g., Left-V, Left-I, Right-V, Right-I vs. interleaved I/V pairs). The generic layer applies runtime channel maps (`source_ch_map` and `feedback_ch_map`) to rearrange multi-channel streams into standard formats before feeding the inner model.
* **Format Conversion**: Allows the inner model to operate at a fixed, high-precision bit depth (such as 32-bit fixed point) regardless of whether external pipelines stream in `S16_LE`, `S24_4LE`, or `S32_LE`.

Inner Model Interface (`inner_model_ops`)
-----------------------------------------

The inner model interacts with the generic layer strictly through an operations table:

.. list-table:: Sound Open Firmware Inner Model Operations Interface
   :widths: 25 20 55
   :header-rows: 1

   * - Operation Name
     - Invocation Stage
     - Functional Responsibility
   * - ``init()``
     - Component Creation
     - Initializes internal model state variables and coefficients.
   * - ``query_memblk_size()``
     - Creation & Prepare
     - Returns the memory size in bytes required for a specific memory block category.
   * - ``set_memblk()``
     - Creation & Prepare
     - Receives allocated memory buffer pointers from the generic layer.
   * - ``get_supported_fmts()``
     - Component Prepare
     - Reports the array of PCM sample formats supported by the inner algorithm.
   * - ``set_fmt()``
     - Component Prepare
     - Sets the negotiated operating sample format for feed-forward and feedback streams.
   * - ``ff_proc()``
     - Audio Stream Processing
     - Executes protection algorithms (excursion/thermal limiting) on playback frames.
   * - ``fb_proc()``
     - Audio Stream Processing
     - Ingests and processes current/voltage sense feedback frames to update physical models.
   * - ``get_config()`` / ``set_config()``
     - Control Plane / IPC
     - Reads runtime telemetry or updates static speaker model and calibration data.
   * - ``reset()``
     - Stream Stop / Reset
     - Flushes internal delay lines, clears history buffers, and resets filter states.

Supported Inner Model Implementations
-------------------------------------

SOF supports multiple implementations selected at firmware build time via Kconfig:

1. **Passthrough Smart Amp (`PASSTHRU_AMP`)**:
   
   * UUID: `64a794f0-55d3-4bca-9d5b-7b588badd037`.
   * Open-source reference implementation requiring no proprietary libraries.
   * Audio frames passing through feed-forward are copied directly to output without modification or latency.
   * Feedback frames arriving on the capture input are consumed and discarded.
   * Serves as the default baseline for pipeline bring-up, open-hardware testing, and continuous integration.

2. **Maxim Dynamic Speaker Management (`MAXIM_DSM`)**:
   
   * UUID: `0cd84e80-ebd3-11ea-adc1-0242ac120002`.
   * Integrates Maxim's proprietary DSM algorithm via a pre-compiled static library (`libdsm.a`).
   * Provides real-time voice coil temperature estimation, non-linear excursion prediction, thermal limiting, and dynamic bass boost.
   * Includes a stub implementation (`MAXIM_DSM_STUB`) for CI building and unit testing without proprietary source code.

Three-Block Structured Memory Architecture
==========================================

Hard real-time embedded audio DSPs forbid dynamic heap allocations (`malloc`, `free`) during streaming to avoid non-deterministic latency and memory fragmentation. The Smart Amp component organizes all runtime memory into three strictly classified blocks:

.. graphviz::
   :caption: Figure 163: Memory Classification and Double-Buffer Rate Matching
   :alt: Memory Classification and Double-Buffer Rate Matching

   digraph smart_amp_mem {
       graph [rankdir=TB, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_mems {
           label = "Three-Block Memory Hierarchy (enum smart_amp_mod_memblk)";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#F7FAFC";

           subgraph cluster_priv {
               label = "MOD_MEMBLK_PRIVATE (Allocated BEFORE model init)";
               style = "filled,rounded";
               color = "#2B6CB0";
               fillcolor = "#EBF8FF";

               m_handle [label="Algorithm State Handle\ne.g. dsmhandle (Persistent context)", fillcolor="#BEE3F8", color="#2B6CB0"];
               m_filter [label="Persistent Filter History\nBiquad delays & state variables", fillcolor="#BEE3F8", color="#2B6CB0"];
           }

           subgraph cluster_frame {
               label = "MOD_MEMBLK_FRAME (Allocated AFTER model init)";
               style = "filled,rounded";
               color = "#2C7A7B";
               fillcolor = "#E6FFFA";

               m_work [label="Scratch Processing Arrays\nInput, Output, Voltage, Current working arrays", fillcolor="#B2F5EA", color="#2C7A7B"];
               m_db_ff [label="Feed-Forward Double-Buffer\nSMART_AMP_FF_BUF_DB_SZ\nDecouples SOF ticks from fixed block size", fillcolor="#B2F5EA", color="#2C7A7B"];
               m_db_fb [label="Feedback Double-Buffer\nSMART_AMP_FB_BUF_DB_SZ\nBuffers async I/V capture frames", fillcolor="#B2F5EA", color="#2C7A7B"];
           }

           subgraph cluster_param {
               label = "MOD_MEMBLK_PARAM (Allocated AFTER model init)";
               style = "filled,rounded";
               color = "#B7791F";
               fillcolor = "#FEFCBF";

               m_caldata [label="Static Model Calibration Table\nThiele-Small parameters, limits, EQ presets", fillcolor="#FFFFF0", color="#B7791F"];
               m_vol [label="Volatile Telemetry Mirror\nReal-time temperature, excursion, Rdc readback", fillcolor="#FFFFF0", color="#B7791F"];
           }
       }

       subgraph cluster_flow {
           label = "Buffer Decoupling Mechanics (Variable SOF Period <-> Fixed Algorithm Frame)";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#EDF2F7";

           f_in [label="SOF Variable Input (e.g. 1ms / 48 frames)"];
           f_ring [label="Accumulation Double-Buffer\n(ff.avail, ff_out.avail)"];
           f_block [label="Fixed Algorithm Block Execution\n(e.g. DSM_FRM_SZ = 48 frames)"];
           f_out [label="SOF Variable Output Drain"];
       }

       f_in -> f_ring [label="Appends new samples"];
       f_ring -> f_block [label="Triggers when avail >= block_size"];
       f_block -> f_ring [label="Stores processed frames"];
       f_ring -> f_out [label="Drains to sink"];

       m_work -> f_block [style="dashed", color="#2C7A7B"];
       m_db_ff -> f_ring [style="dashed", color="#2C7A7B"];
   }

1. **Private Memory Block (`MOD_MEMBLK_PRIVATE`)**:
   
   * Queried and allocated **before** the inner model is initialized.
   * Holds the algorithm context handle (e.g., `dsmhandle`), static mathematical tables, and circular delay lines.
   * Persists across pipeline run, pause, and resume cycles.

2. **Frame Buffer Memory Block (`MOD_MEMBLK_FRAME`)**:
   
   * Queried and allocated **after** model initialization.
   * Contains working sample arrays for feed-forward input, processed output, feedback voltage, and feedback current.
   * Allocates dedicated accumulation double-buffers (`SMART_AMP_FF_BUF_DB_SZ` and `SMART_AMP_FB_BUF_DB_SZ`). These buffers decouple SOF's variable-period scheduling pipeline ticks from the fixed-frame blocks required by the speaker protection library.

3. **Parameter Memory Block (`MOD_MEMBLK_PARAM`)**:
   
   * Queried and allocated **after** model initialization.
   * Houses static speaker model parameters, Thiele-Small characteristics, thermal dissipation thresholds, and multi-band equalizer coefficients.
   * Maintains volatile telemetry mirrors for dynamic host status readbacks.

Dual-Pipeline Topology & Asynchronous Buffer Scheduling
========================================================

A unique architectural feature of the Smart Amplifier component is its role as a multi-endpoint bridge connecting two asynchronous SOF pipelines:

1. **Feed-Forward (FF) Playback Pipeline**: Originates from host audio streams (via Mixin/Mixout, Volume, and Equalizer) and delivers safe audio to the speaker amplifier DAC.
2. **Feedback (FB) Capture Pipeline**: Originates from the amplifier I/V sense capture DAI and delivers digitized current and voltage frames into the smart amp.

.. graphviz::
   :caption: Figure 164: Dual-Pipeline Topology: Playback and Capture Synchronization
   :alt: Dual-Pipeline Topology: Playback and Capture Synchronization

   digraph smart_amp_topology {
       graph [rankdir=LR, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_playback {
           label = "Playback Pipeline (timer domain 1)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           pb_host [label="Host Playback Stream\nPCM Capture", fillcolor="#FFFFFF", color="#2B6CB0"];
           pb_vol [label="Volume / Gain\nModule", fillcolor="#BEE3F8", color="#2B6CB0"];
           pb_buf [label="source_buf\n(Pin 0 Input)", fillcolor="#BEE3F8", color="#2B6CB0"];
           pb_sink [label="sink_buf\n(Pin 0 Output)", fillcolor="#BEE3F8", color="#2B6CB0"];
           pb_dai [label="DAI Copier (Tx)\nTo Amplifier DAC", fillcolor="#FFFFFF", color="#2B6CB0"];
       }

       subgraph cluster_smart {
           label = "Smart Amp Component";
           style = "filled,rounded";
           color = "#B7791F";
           fillcolor = "#FEFCBF";

           sa_core [label="smart_amp_process()\nDual-stream coordinator", fillcolor="#FFFFF0", color="#B7791F"];
           sa_ff [label="smart_amp_ff_process()\nExcursion/Thermal Limiter", fillcolor="#FFFFF0", color="#B7791F"];
           sa_fb [label="smart_amp_fb_process()\nI/V Telemetry Ingestion", fillcolor="#FFFFF0", color="#B7791F"];
       }

       subgraph cluster_capture {
           label = "Capture Pipeline (timer domain 2)";
           style = "filled,rounded";
           color = "#2C7A7B";
           fillcolor = "#E6FFFA";

           cap_dai [label="DAI Copier (Rx)\nFrom Amplifier I/V ADCs", fillcolor="#FFFFFF", color="#2C7A7B"];
           cap_demux [label="Demux / Routing\nSeparates I/V channels", fillcolor="#B2F5EA", color="#2C7A7B"];
           cap_buf [label="feedback_buf\n(Pin 1 Input)", fillcolor="#B2F5EA", color="#2C7A7B"];
       }

       pb_host -> pb_vol -> pb_buf -> sa_core;
       cap_dai -> cap_demux -> cap_buf -> sa_core;

       sa_core -> sa_fb [label="Consumes FB frames"];
       sa_core -> sa_ff [label="Processes FF frames"];

       sa_ff -> pb_sink -> pb_dai;
   }

The Asynchronous Scheduling Challenge
-------------------------------------

In practical hardware, the playback DAI and capture DAI operate on separate hardware FIFOs and may trigger on different DMA interrupt boundaries or timer ticks. The smart amp component handles this divergence:

1. **Available Frame Computation**:
   
   The component queries available frames in the playback path:
   
   .. math::
   
      \text{avail\_passthrough\_frames} = \min(\text{source\_avail}, \text{sink\_free})

2. **Feedback Stream Synchronization**:
   
   If a valid feedback stream is attached and active, the component calculates available feedback frames:
   
   .. math::
   
      \text{avail\_feedback\_frames} = \min(\text{avail\_passthrough\_frames}, \text{feedback\_avail})

3. **Decoupled Processing Sequence**:
   
   * **Cache Invalidation**: Feedback buffer memory ranges are invalidated (`buffer_stream_invalidate()`) to synchronize DSP L1 data cache with incoming DMA writes.
   * **Feedback Consumption**: The feedback process (`fb_proc()`) ingests up to `avail_feedback_frames`, re-orders I/V channels into planar buffers, and updates the physical models. The feedback buffer read pointer is immediately advanced.
   * **Feed-Forward Protection**: Playback audio is processed through `ff_proc()`, applying instantaneous gain reduction and excursion notches informed by the newly updated speaker state.
   * **Cache Writeback**: Processed sink audio is written back to L1 cache (`buffer_stream_writeback()`), and sink produce pointers are updated.

If the capture pipeline experiences a momentary glitch or underflow, the feed-forward audio continues rolling using recent model estimates, ensuring audio playback never stutters or drops out.

Dynamic Protection & Acoustic Enhancement Engines
=================================================

The Smart Amplifier processing core incorporates three coordinated algorithms operating across distinct frequency and temporal domains:

.. graphviz::
   :caption: Figure 165: Dynamic Protection Architecture: Multi-Band Excursion Limiter and Thermal Controller
   :alt: Dynamic Protection Architecture: Multi-Band Excursion Limiter and Thermal Controller

   digraph smart_amp_engines {
       graph [rankdir=LR, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       in_audio [label="Audio Input\nUnprocessed Playback", fillcolor="#EDF2F7", color="#4A5568"];

       subgraph cluster_dbe {
           label = "Acoustic Enhancement";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           e_dbe [label="Dynamic Bass Extension (DBE)\nAdaptive resonant boost\nRolls off at high drive", fillcolor="#BEE3F8", color="#2B6CB0"];
           e_harm [label="Harmonic Bass Synthesizer\nNon-linear 2nd/3rd harmonics\n(Missing Fundamental)", fillcolor="#BEE3F8", color="#2B6CB0"];
       }

       subgraph cluster_xlimit {
           label = "Fast Excursion Limiting Loop (Mechanical)";
           style = "filled,rounded";
           color = "#2C7A7B";
           fillcolor = "#E6FFFA";

           x_pred [label="Excursion Predictor\nx_hat(t) = H_disp(s) * V_in", fillcolor="#B2F5EA", color="#2C7A7B"];
           x_peak [label="Peak Detector\nTracks margin to X_max", fillcolor="#B2F5EA", color="#2C7A7B"];
           x_filter [label="Dynamic High-Pass / Notch\nShifts cutoff upward near fs\nwhen |x| -> X_max", fillcolor="#FFFFFF", color="#2C7A7B"];
       }

       subgraph cluster_tlimit {
           label = "Slow Thermal Limiting Loop (Electrical)";
           style = "filled,rounded";
           color = "#C53030";
           fillcolor = "#FFF5F5";

           t_meas [label="Measured Temperature\nT_coil from Re tracking", fillcolor="#FED7D7", color="#C53030"];
           t_gain [label="Slow RMS Gain Attenuator\nSmooth broadband ducking\nwhen T_coil -> T_max", fillcolor="#FFFFFF", color="#C53030"];
       }

       out_audio [label="Safe Audio Output\nTo Amplifier DAC", fillcolor="#EDF2F7", color="#4A5568"];

       in_audio -> e_dbe;
       e_dbe -> e_harm -> x_filter;

       x_pred -> x_peak [label="Predicted cone motion"];
       x_peak -> x_filter [label="Frequency-selective cut", color="#2C7A7B", penwidth=1.5];
       x_peak -> e_dbe [label="Throttle bass boost", color="#2C7A7B", style="dashed"];

       x_filter -> t_gain -> out_audio;
       t_meas -> t_gain [label="Thermal reduction", color="#C53030", penwidth=1.5];
   }

1. Excursion Limiter (Sub-Millisecond Mechanical Protection)
------------------------------------------------------------

Loudspeaker displacement is heavily concentrated in the low-frequency band near resonance :math:`f_s`. The Excursion Limiter enforces physical bounds:

* **Displacement Prediction**: Filters the input signal through a linear/non-linear displacement transfer function :math:`H_x(s) = \frac{X(s)}{V(s)}` modeling the speaker suspension and acoustic enclosure.
* **Frequency-Selective Clamping**: When predicted excursion approaches the linear limit :math:`X_{max}`, the limiter does *not* apply crude wideband attenuation. Instead, it dynamically shifts a high-pass filter corner frequency upward, or engages a sharp parametric notch filter centered at :math:`f_s`. 
* **Perceptual Benefit**: Midrange dialogue and high frequencies pass through unaffected at full volume, maintaining punch and speech clarity while eliminating bass bottoming.

2. Thermal Limiter (Multi-Second Electrical Protection)
-------------------------------------------------------

Thermal damage results from long-term integrated power dissipation. The Thermal Limiter protects against coil burnout:

* **Temperature Thresholding**: Compares the real-time measured temperature :math:`T_{\text{coil}}(t)` against two configured thresholds: :math:`T_{\text{warn}}` (e.g. 95°C) and :math:`T_{\text{max}}` (e.g. 115°C).
* **Smooth Broadband Compression**: When :math:`T_{\text{coil}} > T_{\text{warn}}`, the limiter applies a slow-acting gain reduction (attack time constant 1 to 5 seconds, release time constant 10 to 30 seconds).
* **Perceptual Benefit**: The user perceives no sudden pumping, clicks, or dynamic modulation. The overall volume level smoothly scales back to an equilibrium level where heat generation matches ambient thermal dissipation.

3. Dynamic Bass Extension (DBE) & Harmonic Synthesis
----------------------------------------------------

Micro-speakers typically have a natural low-frequency roll-off starting around 300 Hz to 500 Hz. At low to moderate listening levels, the speaker operates with substantial excursion and thermal headroom.

* **Dynamic Bass Boost**: The DBE module applies an equalization shelf boosting frequencies between 100 Hz and 300 Hz. As the overall playback volume increases and the excursion limiter detects that :math:`x(t)` is approaching :math:`X_{max}`, the bass boost automatically rolls off.
* **Psychoacoustic Missing Fundamental**: When bass frequencies below 150 Hz cannot be physically reproduced without tearing the speaker diaphragm, the algorithm synthesizes 2nd and 3rd harmonics (e.g. 200 Hz and 300 Hz for a 100 Hz bass note). The human auditory cortex interprets these harmonics as the original low-frequency fundamental without requiring large cone excursions.

Control Plane, Calibration & Production Workflow
================================================

IPC Configuration Structures
----------------------------

The Smart Amplifier component exposes two standard binary configuration payloads via IPC3 (`SOF_IPC_COMP_SET_DATA`) and IPC4 (`SET_LARGE_CONFIG` / `GET_LARGE_CONFIG`):

.. list-table:: Smart Amplifier IPC Configuration Payloads
   :widths: 20 25 55
   :header-rows: 1

   * - Config Type
     - Identifier
     - Structure & Contents
   * - **Type 0**
     - ``SOF_SMART_AMP_CONFIG``
     - ``struct sof_smart_amp_config``: Topology channel mapping, feedback channel count, `source_ch_map[PLATFORM_MAX_CHANNELS]`, and `feedback_ch_map[PLATFORM_MAX_CHANNELS]`.
   * - **Type 1**
     - ``SOF_SMART_AMP_MODEL``
     - Vendor-specific speaker calibration blob: Thiele-Small parameters (:math:`R_0, Bl, M_{ms}, C_{ms}, R_{ms}`), thermal limits (:math:`T_{max}, \tau_{th}`), excursion thresholds (:math:`X_{max}`), and tuning EQ curves.

Volatile Telemetry Readback
---------------------------

The host operating system or manufacturing test utility can query real-time operating metrics by issuing a `GET_LARGE_CONFIG` request for `SOF_SMART_AMP_MODEL`. 

When the command arrives with `msg_index = 0`, the firmware executes `maxim_dsm_get_volatile_param()`, reading live internal state from the DSP algorithm and packing the data into the response payload:

* Instantaneous voice coil resistance :math:`R_e(t)`.
* Real-time voice coil temperature :math:`T_{\text{coil}}(t)`.
* Maximum instantaneous cone excursion :math:`x_{\text{peak}}`.
* Thermal limiter gain reduction (dB).
* Excursion limiter attenuation (dB).

Factory Assembly Line Calibration
---------------------------------

Loudspeaker voice coil resistance :math:`R_0` varies by up to :math:`\pm 10\%` during factory manufacturing due to copper wire draw tolerances and winding tension. If an algorithm assumed a nominal :math:`R_0 = 6.0\,\Omega` on a speaker whose actual cold resistance is :math:`6.6\,\Omega`, the thermal estimator would calculate a persistent +25°C error, triggering premature thermal limiting.

To prevent this, production lines execute a calibration routine:

1. The device is stabilized in a controlled temperature environment (e.g., :math:`T_0 = 20^\circ\text{C}`).
2. A factory diagnostic utility plays a low-level, inaudible test tone or pilot sequence.
3. The DSP measures the baseline cold resistance :math:`R_0` via I/V feedback.
4. The calculated :math:`R_0` value is flashed into non-volatile device storage (ACPI tables or factory calibration partitions).
5. At boot, the Linux sound card initialization script loads the calibrated :math:`R_0` into the Smart Amp component via ALSA byte controls.

ALSA Topology 2 Declaration & System Graph
==========================================

Topology 2 Widget Declaration
-----------------------------

The Smart Amplifier component is declared in ALSA Topology 2.0 configuration files via `Class.Widget."smart_amp"` (defined in `tools/topology/topology2/include/components/smart_amp.conf`):

.. code-block:: none

   Class.Widget."smart_amp" {
       DefineAttribute."index" {}
       <include/components/widget-common.conf>

       # Declares 2 input pins (FF audio and FB sense) and 1 output pin
       num_input_pins      2
       num_output_pins     1
       type                "effect"
       no_pm               "true"
       cpc                 5000
       is_pages            1

       # ALSA byte control for runtime configuration and model delivery
       Object.Control.bytes."1" {
           !access [
               tlv_read
               tlv_callback
           ]
           Object.Base.extops.1 {
               name    "extctl"
               get 258
               put 0
           }
           max 4096
       }
   }

End-to-End System Hardware and Firmware Audio Graph
---------------------------------------------------

The complete signal routing connects host audio applications, firmware processing modules, hardware DAI links, and the physical loudspeaker transducer:

.. graphviz::
   :caption: Figure 166: Complete End-to-End Hardware and Firmware Audio Graph
   :alt: Complete End-to-End Hardware and Firmware Audio Graph

   digraph smart_amp_e2e {
       graph [rankdir=TB, bgcolor="transparent", fontsize=11, fontname="Bitstream Vera Sans"];
       node [shape=box, style="filled,rounded", fontname="Bitstream Vera Sans", fontsize=10, penwidth=1.5];
       edge [fontname="Bitstream Vera Sans", fontsize=9, penwidth=1.2];

       subgraph cluster_host {
           label = "Linux Host OS (ALSA / SoundWire Driver)";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#EDF2F7";

           h_app [label="Audio Application\n(Music / Video / Call)", fillcolor="#CBD5E0", color="#4A5568"];
           h_alsa [label="ALSA UCM & Topology 2\nLoads Calibration Blob & Channel Map", fillcolor="#CBD5E0", color="#4A5568"];
       }

       subgraph cluster_dsp_fw {
           label = "Audio DSP Firmware (Sound Open Firmware)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           subgraph cluster_playback_pipe {
               label = "Playback Pipeline (ID: 1)";
               style = "filled,rounded";
               color = "#2B6CB0";
               fillcolor = "#FFFFFF";

               fw_mixin [label="Mixin / Mixer", fillcolor="#BEE3F8", color="#2B6CB0"];
               fw_dcb [label="DC Blocker", fillcolor="#BEE3F8", color="#2B6CB0"];
               fw_eq [label="Equalizer (FIR/IIR)", fillcolor="#BEE3F8", color="#2B6CB0"];
               fw_drc [label="Dynamic Range Compressor", fillcolor="#BEE3F8", color="#2B6CB0"];
               fw_sa [label="Smart Amplifier\n(smart_amp.c)\nPin 0: Feedforward\nPin 1: Feedback\nPin 0 Out: Protected Audio", fillcolor="#FEFCBF", color="#B7791F", penwidth=2.0];
               fw_copier_tx [label="DAI Copier (Tx)\nSoundWire / I2S Output", fillcolor="#BEE3F8", color="#2B6CB0"];
           }

           subgraph cluster_capture_pipe {
               label = "Feedback Capture Pipeline (ID: 2)";
               style = "filled,rounded";
               color = "#2C7A7B";
               fillcolor = "#FFFFFF";

               fw_copier_rx [label="DAI Copier (Rx)\nSoundWire / I2S Input", fillcolor="#B2F5EA", color="#2C7A7B"];
               fw_demux [label="Channel Demux\nIsolates I and V Streams", fillcolor="#B2F5EA", color="#2C7A7B"];
           }
       }

       subgraph cluster_hardware {
           label = "Hardware Platform";
           style = "filled,rounded";
           color = "#C53030";
           fillcolor = "#FFF5F5";

           hw_amp [label="Smart Amplifier IC (e.g. MAX98373 / CS35L41)\nClass-D BTL Power Stage + I/V Sense ADCs", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           hw_speaker [label="Micro-Speaker Transducer\nVoice Coil + Neodymium Magnet + Diaphragm", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
       }

       h_app -> fw_mixin [label="PCM Audio Stream"];
       h_alsa -> fw_sa [label="Model Blob & Config", style="dashed", color="#B7791F"];

       fw_mixin -> fw_dcb -> fw_eq -> fw_drc -> fw_sa [label="Feedforward Playback"];
       fw_sa -> fw_copier_tx [label="Protected Audio"];
       fw_copier_tx -> hw_amp [label="Digital Audio (Tx)", color="#2B6CB0", penwidth=1.5];

       hw_amp -> hw_speaker [label="High-Power Analog Drive", color="#C53030", penwidth=2.0];
       hw_speaker -> hw_amp [label="I/V Sense Terminal Feedback", color="#C53030", style="dotted", penwidth=1.5];

       hw_amp -> fw_copier_rx [label="Digitized I/V Sense (Rx)", color="#2C7A7B", penwidth=1.5];
       fw_copier_rx -> fw_demux -> fw_sa [label="Feedback Stream (Pin 1)", color="#2C7A7B", penwidth=1.5];
   }

Developer Tuning & Diagnostic Workflow
======================================

When integrating a new micro-speaker into a Sound Open Firmware platform:

1. **Speaker Characterization**: Measure baseline Thiele-Small parameters (:math:`R_0, Bl, M_{ms}, C_{ms}, R_{ms}`) and determine destructive thermal (:math:`T_{max}`) and mechanical (:math:`X_{max}`) limits using laser vibrometry and thermal imaging.
2. **Topology Channel Mapping**: Configure `source_ch_map` and `feedback_ch_map` in ALSA Topology 2 to ensure the V-sense and I-sense capture channels align with the physical amplifier pinout.
3. **Model Generation & Injection**: Compile Characterization parameters into a binary model blob (`SOF_SMART_AMP_MODEL`) and deliver it to the component via ALSA mixer controls (`amixer cset`).
4. **Telemetry Verification**: Stream high-volume audio while monitoring volatile parameters (:math:`R_e(t), T_{\text{coil}}(t), x(t)`) to verify that the thermal and excursion limiters activate smoothly before reaching physical boundaries.

Upstream Source Code References
===============================

* **Component Core & Generic Layer**:
  
  - `src/audio/smart_amp/smart_amp.c <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/smart_amp.c>`_: Processing module adapter, multi-endpoint binding, memory manager, and process loop.
  - `src/audio/smart_amp/smart_amp_generic.c <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/smart_amp_generic.c>`_: Channel remapping, format conversion routines, and pointer helpers.
  - `src/include/sof/audio/smart_amp/smart_amp.h <https://github.com/thesofproject/sof/tree/main/src/include/sof/audio/smart_amp/smart_amp.h>`_: Internal interfaces, buffer definitions, and memory block enums.
  - `src/include/user/smart_amp.h <https://github.com/thesofproject/sof/tree/main/src/include/user/smart_amp.h>`_: User-space and IPC configuration structures.

* **Inner Model Implementations**:
  
  - `src/audio/smart_amp/smart_amp_passthru.c <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/smart_amp_passthru.c>`_: Open-source passthrough inner model.
  - `src/audio/smart_amp/smart_amp_maxim_dsm.c <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/smart_amp_maxim_dsm.c>`_: Maxim DSM adapter, volatile telemetry readback, and frame reordering.
  - `src/audio/smart_amp/include/dsm_api/inc/dsm_api_public.h <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/include/dsm_api/inc/dsm_api_public.h>`_: Public interface declarations for DSM.

* **ALSA Topology 2 Configurations**:
  
  - `tools/topology/topology2/include/components/smart_amp.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/components/smart_amp.conf>`_: Topology 2 smart amp widget class.
  - `tools/topology/topology2/include/pipelines/cavs/mixout-gain-smart-amp-dai-copier-playback.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/pipelines/cavs/mixout-gain-smart-amp-dai-copier-playback.conf>`_: Playback pipeline integrating Smart Amp with gain and DAI copiers.

Related Architecture Guides
===========================

* :ref:`drc_multiband_drc`: Wideband and multi-band dynamic range compression, lookahead pre-delay buffers, and speaker protection leveling.
* :ref:`dcblock`: First-order recursive high-pass filter eliminating DC offsets before speaker power amplification.
* :ref:`crossover`: Multi-way active digital frequency division splitting audio across woofers and tweeters.
* :ref:`volume_module`: High-precision volume scaling, zero-crossing smooth ramping, and soft mute mechanics.
* :ref:`module_framework`: Standardized lifecycle, memory management, and IPC configuration handlers.

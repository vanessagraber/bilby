#!/bin/python
"""
Tutorial to demonstrate running parameter estimation on a binary neutron star system taking into account tidal deformabilities.

This example estimates the masses using a uniform prior in both component masses and also estimates the tidal deformabilities
using a uniform prior in both tidal deformabilities
"""

from __future__ import division, print_function

import numpy as np

import tupak

# Specify the output directory and the name of the simulation.
outdir = 'outdir'
label = 'bns_example'
tupak.core.utils.setup_logger(outdir=outdir, label=label)

# Set up a random seed for result reproducibility.  This is optional!
np.random.seed(881705)


# We are going to inject a binary neutron star waveform.  We first establish a dictionary of parameters that
# includes all of the different waveform parameters, including masses of the two black holes (mass_1, mass_2),
# spins of both black holes (a_1,a_2) , etc. Take into account the the waveform approximants TaylorF2 and 
# IMRPHenomD_NRTidal can only handle aligned spins, so the parameters tilt_1, tilt_2, phi_12, phi_jl must be
# set to 0.
injection_parameters = dict(mass_1=1.5, mass_2=1.3, a_1=0.0, a_2=0.0, tilt_1=0.0, tilt_2=0.0, phi_12=0.0, phi_jl=0,
                            luminosity_distance=50., iota=0.4, psi=2.659, phase=1.3, geocent_time=1126259642.413,
                            ra=1.375, dec=-1.2108, lambda1=400, lambda2=450)

# Set the duration and sampling frequency of the data segment that we're going to inject the signal into. For the 
# TaylorF2 waveform we cut the waveform at the isco frequency
duration = 4.
sampling_frequency = 2*1570.
start_time = injection_parameters['geocent_time'] // 4 * 4

# Fixed arguments passed into the source model
waveform_arguments = dict(waveform_approximant='TaylorF2',
                          reference_frequency=50.,minimum_frequency=40.0)

# Create the waveform_generator using a LAL BinaryBlackHole source function
waveform_generator = tupak.gw.WaveformGenerator(duration=duration,
                                             sampling_frequency=sampling_frequency,
                                             frequency_domain_source_model=tupak.gw.source.lal_binary_neutron_star,
                                             parameters=injection_parameters,
                                             waveform_arguments=waveform_arguments)
hf_signal = waveform_generator.frequency_domain_strain()

# Set up interferometers.  In this case we'll use three interferometers (LIGO-Hanford (H1), LIGO-Livingston (L1),
# and Virgo (V1)).  These default to their design sensitivity
H1 = tupak.gw.detector.get_empty_interferometer('H1')
H1.minimum_frequency = 40
H1.set_strain_data_from_power_spectral_density(sampling_frequency=sampling_frequency, duration=duration,
                                               start_time = start_time)
H1.inject_signal(parameters=injection_parameters,
        injection_polarizations=hf_signal,
        waveform_generator=waveform_generator)

H1.save_data(outdir, label=label)
H1.plot_data(signal=H1.get_detector_response(hf_signal,injection_parameters), outdir=outdir, label=label)


#second interferometer
L1 = tupak.gw.detector.get_empty_interferometer('L1')
L1.minimum_frequency = 40
L1.set_strain_data_from_power_spectral_density(sampling_frequency=sampling_frequency, duration=duration,
                                               start_time = start_time)
L1.inject_signal(parameters=injection_parameters,
        injection_polarizations=hf_signal,
        waveform_generator=waveform_generator)

L1.save_data(outdir, label=label)
L1.plot_data(signal=L1.get_detector_response(hf_signal,injection_parameters), outdir=outdir, label=label)

#third interferometer
V1 = tupak.gw.detector.get_empty_interferometer('V1')
V1.minimum_frequency = 40
V1.set_strain_data_from_power_spectral_density(sampling_frequency=sampling_frequency, duration=duration,
                                               start_time = start_time)
V1.inject_signal(parameters=injection_parameters,
        injection_polarizations=hf_signal,
        waveform_generator=waveform_generator)

V1.save_data(outdir, label=label)
V1.plot_data(signal=V1.get_detector_response(hf_signal,injection_parameters), outdir=outdir, label=label)
IFOs = np.array([H1,L1,V1])

#priors
priors = tupak.gw.prior.BBHPriorSet()
priors['lambda1'] = tupak.prior.Uniform(0, 3000, '$\\Lambda_1$')
priors['lambda2'] = tupak.prior.Uniform(0, 3000, '$\\Lambda_2$')
priors['mass_1'] = tupak.prior.Uniform(1, 2, '$m_1$')
priors['mass_2'] = tupak.prior.Uniform(1, 2, '$m_2$')
for key in ['a_1', 'a_2', 'tilt_1', 'tilt_2', 'phi_12', 'phi_jl', 'psi',
           'geocent_time','ra','dec','iota','luminosity_distance','phase']:
    priors[key] = injection_parameters[key]
    
# Initialise the likelihood by passing in the interferometer data (IFOs) and the waveoform generator
likelihood = tupak.gw.GravitationalWaveTransient(interferometers=IFOs, waveform_generator=waveform_generator,
                                              time_marginalization=False, phase_marginalization=False,
                                              distance_marginalization=False, prior=priors)

# Run sampler.  In this case we're going to use the `nestle` sampler
result = tupak.run_sampler(likelihood=likelihood, priors=priors, sampler='nestle', npoints=500,
                           injection_parameters=injection_parameters, outdir=outdir, label=label)

result.plot_corner()


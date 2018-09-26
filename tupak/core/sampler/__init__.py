import inspect
import sys
import numpy as np
import datetime
from collections import OrderedDict

from ..utils import command_line_args, logger
from ..prior import PriorSet

from .base_sampler import Sampler
from .cpnest import Cpnest
from .dynesty import Dynesty
from .emcee import Emcee
from .nestle import Nestle
from .ptemcee import Ptemcee
from .pymultinest import Pymultinest

implemented_samplers = {
    'cpnest': Cpnest, 'dynesty': Dynesty, 'emcee': Emcee, 'nestle': Nestle,
    'ptemcee': Ptemcee, 'pymultinest': Pymultinest}

if command_line_args.sampler_help:
    from . import implemented_samplers
    sampler = command_line_args.sampler_help
    if sampler in implemented_samplers:
        sampler_class = implemented_samplers[sampler]
        print('Help for sampler "{}":'.format(sampler))
        print(sampler_class.__doc__)
    else:
        if sampler == "None":
            print('For help with a specific sampler, call sampler-help with '
                  'the name of the sampler')
        else:
            print('Requested sampler {} not implemented'.format(sampler))
        print('Available samplers = {}'.format(implemented_samplers))

    sys.exit()


def run_sampler(likelihood, priors=None, label='label', outdir='outdir',
                sampler='dynesty', use_ratio=None, injection_parameters=None,
                conversion_function=None, plot=False, default_priors_file=None,
                clean=None, meta_data=None, save=True, **kwargs):
    """
    The primary interface to easy parameter estimation

    Parameters
    ----------
    likelihood: `tupak.Likelihood`
        A `Likelihood` instance
    priors: `tupak.PriorSet`
        A PriorSet/dictionary of the priors for each parameter - missing
        parameters will use default priors, if None, all priors will be default
    label: str
        Name for the run, used in output files
    outdir: str
        A string used in defining output files
    sampler: str, Sampler
        The name of the sampler to use - see
        `tupak.sampler.get_implemented_samplers()` for a list of available
        samplers.
        Alternatively a Sampler object can be passed
    use_ratio: bool (False)
        If True, use the likelihood's log_likelihood_ratio, rather than just
        the log_likelihood.
    injection_parameters: dict
        A dictionary of injection parameters used in creating the data (if
        using simulated data). Appended to the result object and saved.
    plot: bool
        If true, generate a corner plot and, if applicable diagnostic plots
    conversion_function: function, optional
        Function to apply to posterior to generate additional parameters.
    default_priors_file: str
        If given, a file containing the default priors; otherwise defaults to
        the tupak defaults for a binary black hole.
    clean: bool
        If given, override the command line interface `clean` option.
    meta_data: dict
        If given, adds the key-value pairs to the 'results' object before
        saving. For example, if `meta_data={dtype: 'signal'}`. Warning: in case
        of conflict with keys saved by tupak, the meta_data keys will be
        overwritten.
    save: bool
        If true, save the priors and results to disk.
    **kwargs:
        All kwargs are passed directly to the samplers `run` function

    Returns
    -------
    result
        An object containing the results
    """

    if clean:
        command_line_args.clean = clean

    from . import implemented_samplers

    if priors is None:
        priors = dict()

    if type(priors) in [dict, OrderedDict]:
        priors = PriorSet(priors)
    elif isinstance(priors, PriorSet):
        pass
    else:
        raise ValueError("Input priors not understood")

    priors.fill_priors(likelihood, default_priors_file=default_priors_file)

    if isinstance(sampler, Sampler):
        pass
    elif isinstance(sampler, str):
        if sampler.lower() in implemented_samplers:
            sampler_class = implemented_samplers[sampler.lower()]
            sampler = sampler_class(
                likelihood, priors=priors, external_sampler=sampler,
                outdir=outdir, label=label, use_ratio=use_ratio, plot=plot,
                **kwargs)
        else:
            print(implemented_samplers)
            raise ValueError(
                "Sampler {} not yet implemented".format(sampler))
    elif inspect.isclass(sampler):
        sampler = sampler(
            likelihood, priors=priors, external_sampler=sampler,
            outdir=outdir, label=label, use_ratio=use_ratio, plot=plot,
            **kwargs)
    else:
        raise ValueError(
            "Provided sampler should be a Sampler object or name of a known "
            "sampler: {}.".format(', '.join(implemented_samplers.keys())))

    if sampler.cached_result:
        logger.warning("Using cached result")
        return sampler.cached_result

    start_time = datetime.datetime.now()

    if command_line_args.test:
        result = sampler._run_test()
    else:
        result = sampler._run_external_sampler()

    if type(meta_data) == dict:
        result.update(meta_data)

    result.priors = priors

    end_time = datetime.datetime.now()
    result.sampling_time = (end_time - start_time).total_seconds()
    logger.info('Sampling time: {}'.format(end_time - start_time))

    if sampler.use_ratio:
        result.log_noise_evidence = likelihood.noise_log_likelihood()
        result.log_bayes_factor = result.log_evidence
        result.log_evidence = \
            result.log_bayes_factor + result.log_noise_evidence
    else:
        if likelihood.noise_log_likelihood() is not np.nan:
            result.log_noise_evidence = likelihood.noise_log_likelihood()
            result.log_bayes_factor = \
                result.log_evidence - result.log_noise_evidence
    if injection_parameters is not None:
        result.injection_parameters = injection_parameters
        if conversion_function is not None:
            result.injection_parameters = conversion_function(
                result.injection_parameters)
    result.fixed_parameter_keys = sampler.fixed_parameter_keys
    result.samples_to_posterior(likelihood=likelihood, priors=priors,
                                conversion_function=conversion_function)
    result.kwargs = sampler.kwargs
    if save:
        result.save_to_file()
        logger.info("Results saved to {}/".format(outdir))
    if plot:
        result.plot_corner()
    logger.info("Summary of results:\n{}".format(result))
    return result


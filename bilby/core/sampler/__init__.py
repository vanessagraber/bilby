import inspect
import sys
import datetime
from collections import OrderedDict

from ..utils import command_line_args, logger
from ..prior import PriorDict

from .base_sampler import Sampler
from .cpnest import Cpnest
from .dynesty import Dynesty
from .emcee import Emcee
from .nestle import Nestle
from .ptemcee import Ptemcee
from .pymc3 import Pymc3
from .pymultinest import Pymultinest

implemented_samplers = {
    'cpnest': Cpnest, 'dynesty': Dynesty, 'emcee': Emcee, 'nestle': Nestle,
    'ptemcee': Ptemcee, 'pymc3': Pymc3, 'pymultinest': Pymultinest}

if command_line_args.sampler_help:
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
    likelihood: `bilby.Likelihood`
        A `Likelihood` instance
    priors: `bilby.PriorDict`
        A PriorDict/dictionary of the priors for each parameter - missing
        parameters will use default priors, if None, all priors will be default
    label: str
        Name for the run, used in output files
    outdir: str
        A string used in defining output files
    sampler: str, Sampler
        The name of the sampler to use - see
        `bilby.sampler.get_implemented_samplers()` for a list of available
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
        the bilby defaults for a binary black hole.
    clean: bool
        If given, override the command line interface `clean` option.
    meta_data: dict
        If given, adds the key-value pairs to the 'results' object before
        saving. For example, if `meta_data={dtype: 'signal'}`. Warning: in case
        of conflict with keys saved by bilby, the meta_data keys will be
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
    if command_line_args.clean:
        kwargs['resume'] = False

    from . import implemented_samplers

    if priors is None:
        priors = dict()

    if type(priors) in [dict, OrderedDict]:
        priors = PriorDict(priors)
    elif isinstance(priors, PriorDict):
        pass
    else:
        raise ValueError("Input priors not understood")

    priors.fill_priors(likelihood, default_priors_file=default_priors_file)

    # Generate the meta-data if not given and append the likelihood meta_data
    if meta_data is None:
        meta_data = dict()
    meta_data['likelihood'] = likelihood.meta_data

    if isinstance(sampler, Sampler):
        pass
    elif isinstance(sampler, str):
        if sampler.lower() in implemented_samplers:
            sampler_class = implemented_samplers[sampler.lower()]
            sampler = sampler_class(
                likelihood, priors=priors, outdir=outdir, label=label,
                injection_parameters=injection_parameters, meta_data=meta_data,
                use_ratio=use_ratio, plot=plot, **kwargs)
        else:
            print(implemented_samplers)
            raise ValueError(
                "Sampler {} not yet implemented".format(sampler))
    elif inspect.isclass(sampler):
        sampler = sampler.__init__(
            likelihood, priors=priors,
            outdir=outdir, label=label, use_ratio=use_ratio, plot=plot,
            injection_parameters=injection_parameters, meta_data=meta_data,
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
        result = sampler.run_sampler()

    end_time = datetime.datetime.now()
    result.sampling_time = (end_time - start_time).total_seconds()
    logger.info('Sampling time: {}'.format(end_time - start_time))

    if sampler.use_ratio:
        result.log_noise_evidence = likelihood.noise_log_likelihood()
        result.log_bayes_factor = result.log_evidence
        result.log_evidence = \
            result.log_bayes_factor + result.log_noise_evidence
    else:
        result.log_noise_evidence = likelihood.noise_log_likelihood()
        result.log_bayes_factor = \
            result.log_evidence - result.log_noise_evidence

    if result.injection_parameters is not None:
        if conversion_function is not None:
            result.injection_parameters = conversion_function(
                result.injection_parameters)

    result.samples_to_posterior(likelihood=likelihood, priors=priors,
                                conversion_function=conversion_function)
    if save:
        result.save_to_file()
        logger.info("Results saved to {}/".format(outdir))
    if plot:
        result.plot_corner()
    logger.info("Summary of results:\n{}".format(result))
    return result

